"""Event entity: one event per button press."""

from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PhilipsRemote, PhilipsRemoteConfigEntry
from .const import BUTTONS, UNKNOWN
from .entity import PhilipsRemoteEntity
from .parser import Press


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PhilipsRemoteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([PhilipsRemoteButtonEvent(entry.runtime_data)])


class PhilipsRemoteButtonEvent(PhilipsRemoteEntity, EventEntity):
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_translation_key = "button"
    _attr_event_types = [*BUTTONS.values(), UNKNOWN]

    def __init__(self, remote: PhilipsRemote) -> None:
        super().__init__(remote, "button")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.remote.async_add_listener(self._handle_press))

    @callback
    def _handle_press(self, press: Press) -> None:
        self._trigger_event(press.name, {"button": press.button, "press_type": press.press_type})
        self.async_write_ha_state()
