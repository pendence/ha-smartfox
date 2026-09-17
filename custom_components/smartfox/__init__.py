"""SMARTFOX integration."""
from __future__ import annotations

from modbus_connection import ModbusTcpParams
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.components.modbus import async_get_unit

from .const import CONF_UNIT_ID, DOMAIN
from .coordinator import SmartfoxCoordinator

PLATFORMS = [Platform.SENSOR, Platform.SELECT, Platform.NUMBER]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    params = ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
    unit = async_get_unit(hass, entry, params, entry.data[CONF_UNIT_ID])
    # SMARTFOX documentation recommends no more than one read request per second.
    unit.set_message_spacing(1.0)
    coordinator = SmartfoxCoordinator(hass, unit, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
