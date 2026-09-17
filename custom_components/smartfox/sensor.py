"""Sensor platform for SMARTFOX."""
from __future__ import annotations

import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower, UnitOfTemperature, UnitOfFrequency
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .registers import REGISTERS
from .control import CONTROL_KEYS

def metadata(reg):
    unit = reg["unit"]
    name = reg["name"].lower()
    device_class = None
    state_class = None
    native_unit = unit
    if unit == "W":
        device_class, state_class, native_unit = SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT
    elif unit == "kW":
        device_class, state_class, native_unit = SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.KILO_WATT
    elif unit == "Wh":
        device_class, state_class, native_unit = SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR
    elif unit == "kWh":
        device_class, state_class, native_unit = SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.KILO_WATT_HOUR
    elif unit == "V":
        device_class, state_class, native_unit = SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT
    elif unit == "mA":
        device_class, state_class, native_unit = SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.AMPERE
    elif unit == "°C":
        device_class, state_class, native_unit = SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, UnitOfTemperature.CELSIUS
    elif unit == "Hz":
        device_class, state_class, native_unit = SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, UnitOfFrequency.HERTZ
    elif unit == "%":
        state_class = SensorStateClass.MEASUREMENT
    if "day energy" in name or "energy pres" in name:
        state_class = SensorStateClass.TOTAL
    return device_class, state_class, native_unit

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [SmartfoxSensor(coordinator, entry, reg) for reg in REGISTERS if reg["key"] not in CONTROL_KEYS]
    entities.append(SmartfoxHeaterPowerSensor(hass, entry))
    async_add_entities(entities)

class SmartfoxSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry, reg):
        super().__init__(coordinator)
        self.reg = reg
        self._attr_unique_id = f"{entry.unique_id}_{reg['key']}"
        self._attr_name = reg["name"]
        self._attr_entity_registry_enabled_default = reg["enabled_default"]
        dc, sc, unit = metadata(reg)
        self._attr_device_class = dc
        self._attr_state_class = sc
        self._attr_native_unit_of_measurement = unit
        if reg["address"] < 41000 or reg["name"].lower().startswith(("wifi", "sd-card", "sw-version", "wlan-modul", "modbus protocol", "mac-")):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.unique_id)}, "manufacturer": MANUFACTURER, "model": MODEL, "name": "SMARTFOX", "configuration_url": f"http://{entry.data['host']}"}
    @property
    def native_value(self):
        value = self.coordinator.data.get(self.reg["key"])
        if value is None:
            return None
        if self.reg["unit"] == "mA":
            return value / 1000
        if self.reg["unit"] == "Wh":
            return value / 1000
        return value

class SmartfoxHeaterPowerSensor(SensorEntity):
    """SMARTFOX heater power read from the local values.xml endpoint."""
    _attr_has_entity_name = True
    _attr_name = "Heizstab Leistung"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_should_poll = True
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_heater_power_http"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.unique_id)}, "manufacturer": MANUFACTURER, "model": MODEL, "name": "SMARTFOX", "configuration_url": f"http://{entry.data['host']}"}
        self._attr_available = False
    async def async_update(self) -> None:
        session = async_get_clientsession(self._hass)
        url = f"http://{self._entry.data['host']}/values.xml"
        try:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                text = await response.text()
        except Exception:
            self._attr_available = False
            return
        match = re.search(r'"@id"\s*:\s*"htPowerMeasValue"\s*,\s*"#text"\s*:\s*"([\-0-9\.,]+)\s*kW"', text)
        if match is None:
            match = re.search(r'htPowerMeasValue.{0,160}?([\-0-9\.,]+)\s*kW', text, re.IGNORECASE | re.DOTALL)
        if match is None:
            self._attr_available = False
            return
        try:
            kw = float(match.group(1).replace(",", "."))
        except ValueError:
            self._attr_available = False
            return
        self._attr_native_value = round(kw * 1000)
        self._attr_available = True
