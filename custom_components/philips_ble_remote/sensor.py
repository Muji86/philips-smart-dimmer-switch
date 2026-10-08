"""Battery sensor, updated from each press."""

from __future__ import annotations

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PhilipsRemote, PhilipsRemoteConfigEntry
from .entity import PhilipsRemoteEntity
from .parser import Press


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PhilipsRemoteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([PhilipsRemoteBattery(entry.runtime_data)])


class PhilipsRemoteBattery(PhilipsRemoteEntity, RestoreSensor):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, remote: PhilipsRemote) -> None:
        super().__init__(remote, "battery")
        self._attr_native_value = remote.battery

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._attr_native_value is None and (last := await self.async_get_last_sensor_data()):
            self._attr_native_value = last.native_value
        self.async_on_remove(self.remote.async_add_listener(self._handle_press))

    @callback
    def _handle_press(self, press: Press) -> None:
        self._attr_native_value = press.battery
        self.async_write_ha_state()
