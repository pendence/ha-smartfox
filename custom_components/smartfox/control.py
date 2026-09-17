"""Writable SMARTFOX control definitions."""
from __future__ import annotations
from .registers import REGISTER_OFFSET
CHARGE_MODE_KEYS = {
    f"car_charge_{n}_charge_mode": {
        "Automatik (A)": 0,
        "Manuell (M)": 1,
        "Automatik+ (A+)": 2,
        "Aus": 3,
        "Manuell+ (M+)": 4,
    }
    for n in range(1, 6)
}
MODE_KEYS = {
    "aout_mode": {"Off": 0, "Manual On": 1, "Automatic": 2},
    "relay_1_mode": {"Off": 0, "Automatic": 1, "Manual On": 2},
    "relay_2_mode": {"Off": 0, "Automatic": 1, "Manual On": 2},
    "relay_3_mode": {"Off": 0, "Automatic": 1, "Manual On": 2},
    "relay_4_mode": {"Off": 0, "Automatic": 1, "Manual On": 2},
    "verbrauchsregler_mode": {"Off": 0, "Manual On": 1, "Automatic": 2},
}
SELECT_KEYS = {**CHARGE_MODE_KEYS, **MODE_KEYS}
NUMBER_KEYS = {f"car_charge_{n}_man_charging_value" for n in range(1, 6)} | {"aout_output_man", "verbrauchsregler_output_man"}
CONTROL_KEYS = set(SELECT_KEYS) | NUMBER_KEYS
async def async_write_register(coordinator, reg, value: int) -> None:
    """Write one SMARTFOX holding register using Modbus/TCP FC16, quantity 1.

    This intentionally mirrors the user's previously working Home Assistant
    Modbus action: one-element array -> Write Multiple Registers (FC16).
    """
    import asyncio
    import struct
    import time
    from homeassistant.exceptions import HomeAssistantError

    address = reg["address"] + REGISTER_OFFSET
    value = int(value)
    if not 0 <= address <= 0xFFFF or not 0 <= value <= 0xFFFF:
        raise HomeAssistantError(
            f"SMARTFOX FC16 value/address out of range: {address=}, {value=}"
        )

    entry = coordinator.config_entry
    host = entry.data["host"]
    port = int(entry.data.get("port", 502))
    unit_id = int(entry.data.get("unit", 1))

    if not hasattr(coordinator, "_smartfox_write_lock"):
        coordinator._smartfox_write_lock = asyncio.Lock()
        coordinator._smartfox_last_write = 0.0

    async with coordinator._smartfox_write_lock:
        wait = 1.0 - (time.monotonic() - coordinator._smartfox_last_write)
        if wait > 0:
            await asyncio.sleep(wait)

        transaction_id = int(time.monotonic() * 1000) & 0xFFFF
        pdu = struct.pack(">BHHBH", 0x10, address, 1, 2, value)
        request = struct.pack(">HHHB", transaction_id, 0, 1 + len(pdu), unit_id) + pdu

        writer = None
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5)
            writer.write(request)
            await writer.drain()
            header = await asyncio.wait_for(reader.readexactly(7), timeout=5)
            rx_tid, protocol_id, length, rx_unit = struct.unpack(">HHHB", header)
            body = await asyncio.wait_for(reader.readexactly(length - 1), timeout=5)
            if rx_tid != transaction_id or protocol_id != 0 or rx_unit != unit_id:
                raise HomeAssistantError("Invalid SMARTFOX Modbus/TCP response header")
            function = body[0]
            if function == 0x90:
                exception_code = body[1] if len(body) > 1 else -1
                raise HomeAssistantError(f"SMARTFOX FC16 exception 0x{exception_code:02X} for register {address}")
            if function != 0x10 or len(body) != 5:
                raise HomeAssistantError(f"Unexpected SMARTFOX Modbus response function 0x{function:02X}")
            rx_address, rx_quantity = struct.unpack(">HH", body[1:5])
            if rx_address != address or rx_quantity != 1:
                raise HomeAssistantError(f"SMARTFOX FC16 response mismatch: {rx_address=}, {rx_quantity=}, expected {address=}, quantity=1")
            coordinator._smartfox_last_write = time.monotonic()
        except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
            raise HomeAssistantError(f"SMARTFOX FC16 write failed for register {address}: {err}") from err
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
    await coordinator.async_request_refresh()
