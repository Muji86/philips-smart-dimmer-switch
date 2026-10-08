"""Config flow: press a button to detect the remote, enter its address, or Bluetooth discovery."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback

from .const import DOMAIN, MANUFACTURER_ID
from .parser import Press, parse

TITLE = "Philips Remote"
DETECT_TIMEOUT = 60
MAC_RE = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


class PhilipsBleRemoteConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._address: str | None = None
        self._press: Press | None = None
        self._detect_task: asyncio.Task[tuple[str, Press]] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["detect", "manual"])

    async def async_step_detect(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._detect_task is None:
            self._detect_task = self.hass.async_create_task(self._async_wait_for_press())
        if not self._detect_task.done():
            return self.async_show_progress(
                step_id="detect",
                progress_action="press_button",
                progress_task=self._detect_task,
            )
        task, self._detect_task = self._detect_task, None
        try:
            self._address, self._press = task.result()
        except TimeoutError:
            return self.async_show_progress_done(next_step_id="detect_timeout")
        return self.async_show_progress_done(next_step_id="detect_confirm")

    async def _async_wait_for_press(self) -> tuple[str, Press]:
        """Wait for a fresh press from any Philips remote not yet configured."""
        configured = self._async_current_ids(include_ignore=False)
        # Counters from advertisements already seen, so stale ones aren't
        # mistaken for a new press.
        baseline = {
            info.address: press.counter
            for info in bluetooth.async_discovered_service_info(self.hass, connectable=False)
            if (press := parse(info))
        }
        found: asyncio.Future[tuple[str, Press]] = self.hass.loop.create_future()

        @callback
        def _on_advertisement(
            info: BluetoothServiceInfoBleak, change: bluetooth.BluetoothChange
        ) -> None:
            if found.done() or info.address in configured or (press := parse(info)) is None:
                return
            if baseline.get(info.address) == press.counter:
                return
            found.set_result((info.address, press))

        unregister = bluetooth.async_register_callback(
            self.hass,
            _on_advertisement,
            bluetooth.BluetoothCallbackMatcher(manufacturer_id=MANUFACTURER_ID, connectable=False),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
        try:
            async with asyncio.timeout(DETECT_TIMEOUT):
                return await found
        finally:
            unregister()

    async def async_step_detect_timeout(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="detect_timeout", menu_options=["detect", "manual"])

    async def async_step_detect_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._address is not None and self._press is not None
        if user_input is not None:
            return await self._async_create(self._address)
        self._set_confirm_only()
        return self.async_show_form(
            step_id="detect_confirm",
            description_placeholders={
                "address": self._address,
                "button": self._press.name,
                "battery": str(self._press.battery),
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper().replace("-", ":")
            if MAC_RE.match(address):
                return await self._async_create(address)
            errors[CONF_ADDRESS] = "invalid_address"
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if parse(discovery_info) is None:
            return self.async_abort(reason="not_supported")
        self._address = discovery_info.address
        self.context["title_placeholders"] = {"address": self._address}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._address is not None
        if user_input is not None:
            return await self._async_create(self._address)
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"address": self._address},
        )

    async def _async_create(self, address: str) -> ConfigFlowResult:
        await self.async_set_unique_id(address, raise_on_progress=False)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=TITLE, data={CONF_ADDRESS: address})
