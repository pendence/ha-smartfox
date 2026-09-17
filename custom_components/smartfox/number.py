"""Number platform for SMARTFOX manual output values."""
from __future__ import annotations
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MANUFACTURER, MODEL
from .control import NUMBER_KEYS, async_write_register
from .registers import REGISTERS
REG_BY_KEY = {reg["key"]: reg for reg in REGISTERS}
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(SmartfoxNumber(coordinator, entry, reg) for key in NUMBER_KEYS if (reg := REG_BY_KEY.get(key)) is not None)
class SmartfoxNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    def __init__(self, coordinator, entry, reg):
        super().__init__(coordinator)
        self.reg = reg
        self._attr_unique_id = f"{entry.unique_id}_{reg['key']}_number"
        self._attr_name = reg["name"]
        self._attr_entity_registry_enabled_default = reg["enabled_default"]
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.unique_id)}, "manufacturer": MANUFACTURER, "model": MODEL, "name": "SMARTFOX", "configuration_url": f"http://{entry.data['host']}"}
    @property
    def native_value(self):
        return self.coordinator.data.get(self.reg["key"])
    async def async_set_native_value(self, value: float) -> None:
        await async_write_register(self.coordinator, self.reg, round(value))
