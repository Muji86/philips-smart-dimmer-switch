"""Constants for the Philips BLE Remote integration."""

DOMAIN = "philips_ble_remote"
EVENT = f"{DOMAIN}_button"
MANUFACTURER_ID = 1559

# Button code (manufacturer data byte 16) -> event type name.
BUTTONS: dict[int, str] = {
    0x01: "on",
    0x02: "off",
    0x08: "brightness_down",
    0x09: "brightness_up",
    0x10: "button_1",
    0x11: "button_2",
    0x12: "button_3",
    0x13: "button_4",
}
UNKNOWN = "unknown"
