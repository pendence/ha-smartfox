"""Select platform for SMARTFOX writable modes."""
from __future__ import annotations
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MANUFACTURER, MODEL
from .control import SELECT_KEYS, async_write_register
from .registers import REGISTERS
REG_BY_KEY = {reg["key"]: reg for reg in REGISTERS}
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(SmartfoxSelect(coordinator, entry, REG_BY_KEY[key], options) for key, options in SELECT_KEYS.items() if key in REG_BY_KEY)
class SmartfoxSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry, reg, options):
        super().__init__(coordinator)
        self.reg = reg
        self.option_values = options
        self.value_options = {value: option for option, value in options.items()}
        self._attr_options = list(options)
        self._attr_unique_id = f"{entry.unique_id}_{reg['key']}_select"
        self._attr_name = reg["name"]
        self._attr_entity_registry_enabled_default = reg["enabled_default"]
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.unique_id)}, "manufacturer": MANUFACTURER, "model": MODEL, "name": "SMARTFOX", "configuration_url": f"http://{entry.data['host']}"}
    @property
    def current_option(self):
        return self.value_options.get(self.coordinator.data.get(self.reg["key"]))
    async def async_select_option(self, option: str) -> None:
        await async_write_register(self.coordinator, self.reg, self.option_values[option])
