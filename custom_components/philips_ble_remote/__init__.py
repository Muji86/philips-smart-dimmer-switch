"""Philips BLE remote: button presses broadcast as BLE advertisements."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, callback

from .const import CONF_DOUBLE_PRESS, DOUBLE_PRESS_WINDOW, EVENT
from .parser import Press, parse

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.EVENT, Platform.SENSOR]

type PhilipsRemoteConfigEntry = ConfigEntry[PhilipsRemote]


class PhilipsRemote:
    """Tracks one remote and hands each new press to its entities."""

    def __init__(self, hass: HomeAssistant, address: str, double_press: bool) -> None:
        self.hass = hass
        self.address = address
        self.double_press = double_press
        self.battery: int | None = None
        self._last_counter: int | None = None
        self._pending: Press | None = None
        self._timer: asyncio.TimerHandle | None = None
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
        if not self.double_press:
            self._dispatch(press)
            return
        if self._pending is not None and self._pending.button == press.button:
            self._cancel_timer()
            self._pending = None
            self._dispatch(replace(press, double=True))
            return
        # A different button ends any pending press right away.
        self._flush()
        self._pending = press
        self._timer = self.hass.loop.call_later(DOUBLE_PRESS_WINDOW, self._flush)

    @callback
    def _flush(self) -> None:
        """Emit the held press as a single press."""
        self._cancel_timer()
        if (press := self._pending) is not None:
            self._pending = None
            self._dispatch(press)

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    @callback
    def async_shutdown(self) -> None:
        self._cancel_timer()
        self._pending = None

    def _dispatch(self, press: Press) -> None:
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
    remote = PhilipsRemote(
        hass, entry.data[CONF_ADDRESS], entry.options.get(CONF_DOUBLE_PRESS, False)
    )
    entry.runtime_data = remote
    entry.async_on_unload(remote.async_shutdown)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
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


async def _async_options_updated(hass: HomeAssistant, entry: PhilipsRemoteConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PhilipsRemoteConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
