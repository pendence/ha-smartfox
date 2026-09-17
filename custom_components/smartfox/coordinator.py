"""Polling coordinator for SMARTFOX."""
from __future__ import annotations

from datetime import timedelta
import struct

from modbus_connection import ModbusError, ModbusUnit
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .registers import REGISTERS, REGISTER_OFFSET

# Blocks are intentionally split at gaps. With 1 s message spacing this keeps
# SMARTFOX within its documented maximum polling rate.
BLOCKS = (
    (40010, 11), (40400, 7), (41000, 45), (41046, 4), (41150, 2),
    (41400, 33), (41440, 1), (41450, 3), (41500, 16), (41600, 50),
    (41700, 60), (42207, 2), (42250, 1), (42280, 1), (42310, 1),
    (42340, 1), (42561, 2),
)

def _bytes(words: list[int]) -> bytes:
    return b"".join(int(w & 0xFFFF).to_bytes(2, "big") for w in words)

def decode(words: list[int], data_type: str):
    raw = _bytes(words)
    if data_type == "uint8":
        return words[0] & 0xFF
    if data_type == "int8":
        v = words[0] & 0xFF
        return v - 256 if v > 127 else v
    if data_type == "uint16":
        return words[0]
    if data_type == "int16":
        return struct.unpack(">h", raw[:2])[0]
    if data_type == "uint32":
        return int.from_bytes(raw[:4], "big", signed=False)
    if data_type == "int32":
        return int.from_bytes(raw[:4], "big", signed=True)
    if data_type == "uint64":
        return int.from_bytes(raw[:8], "big", signed=False)
    if data_type == "float":
        return struct.unpack(">f", raw[:4])[0]
    if data_type == "uint8[6]":
        octets = []
        for word in words[:3]:
            octets.extend([(word >> 8) & 0xFF, word & 0xFF])
        return ":".join(f"{x:02X}" for x in octets)
    return int.from_bytes(raw, "big", signed=False)

class SmartfoxCoordinator(DataUpdateCoordinator[dict[str, object]]):
    def __init__(self, hass: HomeAssistant, unit: ModbusUnit, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.unit = unit

    async def _async_update_data(self) -> dict[str, object]:
        raw: dict[int, int] = {}
        successful_blocks = 0
        last_error: ModbusError | None = None
        for documented_start, count in BLOCKS:
            try:
                words = await self.unit.read_holding_registers(
                    documented_start + REGISTER_OFFSET, count
                )
            except ModbusError as err:
                # Optional SMARTFOX modules/register ranges may not exist on every
                # installation. Keep the integration online and expose those values
                # as unavailable instead of failing the whole config entry.
                last_error = err
                continue
            successful_blocks += 1
            for i, word in enumerate(words):
                raw[documented_start + i] = word

        if successful_blocks == 0:
            raise UpdateFailed(
                f"SMARTFOX Modbus read failed for all register blocks: {last_error}"
            )

        values: dict[str, object] = {}
        for reg in REGISTERS:
            words = [raw.get(reg["address"] + i) for i in range(reg["count"])]
            if any(v is None for v in words):
                values[reg["key"]] = None
                continue
            value = decode(words, reg["data_type"])
            if reg["scale"] is not None and isinstance(value, (int, float)):
                value *= reg["scale"]
            values[reg["key"]] = value
        return values
