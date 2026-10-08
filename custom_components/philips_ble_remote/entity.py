"""Base entity for the Philips BLE Remote integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import Entity

from . import PhilipsRemote
from .const import DOMAIN


class PhilipsRemoteEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, remote: PhilipsRemote, key: str) -> None:
        self.remote = remote
        self._attr_unique_id = f"{remote.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, remote.address)},
            connections={(CONNECTION_BLUETOOTH, remote.address)},
            name="Philips Remote",
            manufacturer="Philips",
            model="BLE Remote",
        )
