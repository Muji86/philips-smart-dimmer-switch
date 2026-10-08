"""Philips BLE remote: button presses broadcast as BLE advertisements."""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, callback

from .const import EVENT
from .parser import Press, parse

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.EVENT, Platform.SENSOR]

type PhilipsRemoteConfigEntry = ConfigEntry[PhilipsRemote]


class PhilipsRemote:
    """Tracks one remote and hands each new press to its entities."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self.hass = hass
        self.address = address
        self.battery: int | None = None
        self._last_counter: int | None = None
        self._listeners: list[Callable[[Press], None]] = []

        # Seed from the last advertisement HA already has, so a cached press
        # isn't replayed as a new one at startup.
        if (last := bluetooth.async_last_service_info(hass, address, connectable=False)) and (
            press := parse(last)
        ):
            self._last_counter = press.counter
            self.battery = press.battery

    @callback
    def async_add_listener(self, listener: Callable[[Press], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def async_handle_advertisement(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        if (press := parse(service_info)) is None or press.counter == self._last_counter:
            return
        self._last_counter = press.counter
        self.battery = press.battery
        _LOGGER.debug("Press from %s: %s (%s)", self.address, press, press.name)
        # Plain bus event, kept for automations that listen to it directly.
        self.hass.bus.async_fire(
            EVENT,
            {
                "address": self.address,
                "button": press.button,
                "button_name": press.name,
                "press_type": press.press_type,
                "battery": press.battery,
                "counter": press.counter,
            },
        )
        for listener in list(self._listeners):
            listener(press)


async def async_setup_entry(hass: HomeAssistant, entry: PhilipsRemoteConfigEntry) -> bool:
    remote = PhilipsRemote(hass, entry.data[CONF_ADDRESS])
    entry.runtime_data = remote
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            remote.async_handle_advertisement,
            bluetooth.BluetoothCallbackMatcher(address=remote.address, connectable=False),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PhilipsRemoteConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
