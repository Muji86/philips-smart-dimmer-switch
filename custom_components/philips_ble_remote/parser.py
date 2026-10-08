"""Decode the remote's manufacturer data.

  byte 11 - press counter (increments each press, used to drop repeats)
  byte 16 - button code
  byte 17 - press type
  byte 18 - battery (%)
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from .const import BUTTONS, MANUFACTURER_ID, UNKNOWN


@dataclass(frozen=True)
class Press:
    counter: int
    button: int
    press_type: int
    battery: int

    @property
    def name(self) -> str:
        return BUTTONS.get(self.button, UNKNOWN)


def parse(service_info: BluetoothServiceInfoBleak) -> Press | None:
    data = service_info.manufacturer_data.get(MANUFACTURER_ID)
    if data is None or len(data) < 19:
        return None
    return Press(counter=data[11], button=data[16], press_type=data[17], battery=data[18])
