"""Config flow for SMARTFOX."""
from __future__ import annotations

import voluptuous as vol
from modbus_connection import ModbusTcpParams, ModbusError

from homeassistant import config_entries
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN

STEP_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
    vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
})

class SmartfoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            unit_id = user_input[CONF_UNIT_ID]
            await self.async_set_unique_id(f"{host.lower()}:{port}:{unit_id}")
            self._abort_if_unique_id_configured()
            try:
                params = ModbusTcpParams(host=host, port=port)
                async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
                    unit.set_message_spacing(1.0)
                    # Probe the Modbus protocol version register (documented 40017 -> address 40016).
                    await unit.read_holding_registers(40016, 1)
            except (ModbusError, HomeAssistantError, OSError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"SMARTFOX {host}",
                    data={CONF_HOST: host, CONF_PORT: port, CONF_UNIT_ID: unit_id},
                )
        return self.async_show_form(step_id="user", data_schema=STEP_SCHEMA, errors=errors)
