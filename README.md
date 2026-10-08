# Philips BLE Remote for Home Assistant

A Home Assistant custom integration for the **Philips Hue Smart Dimmer Switch–style Bluetooth remote** (BLE manufacturer ID `1559`). It listens passively to the remote's Bluetooth advertisements — no pairing, no hub, no bridge.

## Features

- **Event entity** that fires on every button press (`on`, `off`, `brightness_up`, `brightness_down`, `button_1`–`button_4`), plus a `<button>_double` event for double presses.
- **Battery sensor** (diagnostic), updated on each press and restored across restarts.
- Repeated advertisements of the same press are de-duplicated using the remote's press counter.
- Setup by **auto-discovery**, by **pressing a button** to detect the remote, or by **entering the Bluetooth address**.
- Local push, no cloud.

## Requirements

- Home Assistant 2025.x or newer (uses `AddConfigEntryEntitiesCallback` and `runtime_data`).
- A working Bluetooth adapter or [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html) in range of the remote. The Home Assistant `bluetooth` integration must be set up.

## Installation

### HACS (custom repository)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/Muji86/philips-smart-dimmer-switch` with category **Integration**.
3. Install **Philips BLE Remote** and restart Home Assistant.

### Manual

1. Copy `custom_components/philips_ble_remote` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

Go to **Settings → Devices & services → Add integration → Philips BLE Remote**, or accept the discovery notification if the remote has already been seen. Then choose:

- **Press a button on the remote to detect it** – press any button within 60 seconds; the integration finds the remote and asks you to confirm.
- **Enter its Bluetooth address** – e.g. `98:77:D5:50:D1:AC`.

Each remote is added as its own device.

## Entities

| Entity | Type | Notes |
|---|---|---|
| Button | `event` | Event types: `on`, `off`, `brightness_up`, `brightness_down`, `button_1`–`button_4`, each with a `_double` variant (e.g. `on_double`), and `unknown`. Attributes include the raw `button` code and `press_type`. |
| Battery | `sensor` | Percent, diagnostic. Updates when a button is pressed. |

## Double press

Pressing the same button twice within 0.5 seconds fires the normal event for each press, and the second press is followed immediately by a `<button>_double` event (e.g. `on`, then `on` + `on_double`). Nothing is delayed, so single presses stay instant; to react only to a double press, trigger on the `_double` event type. The window is `DOUBLE_PRESS_WINDOW` in `const.py`.

## Automation example

Using the event entity as a trigger (replace the entity ID with yours):

```yaml
automation:
  - alias: "Remote – brightness up"
    triggers:
      - trigger: state
        entity_id: event.philips_remote_button
        attributes:
          event_type: brightness_up
    actions:
      - action: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_step_pct: 10
```

Or use a UI trigger: **Entity → State** on the event entity and filter on the `event_type` attribute.

## How it works

The remote broadcasts button presses as BLE manufacturer data (ID `1559`):

| Byte | Meaning |
|---|---|
| 11 | Press counter (increments each press; used to drop repeats) |
| 16 | Button code |
| 17 | Press type |
| 18 | Battery (%) |

Button codes: `0x01` on, `0x02` off, `0x08` brightness down, `0x09` brightness up, `0x10`–`0x13` buttons 1–4.

## Troubleshooting

- **Remote not detected:** make sure it is within range of a Bluetooth adapter or proxy, and that Bluetooth is working in Home Assistant (**Settings → Devices & services → Bluetooth**).
- **Presses missed:** passive scanning can drop packets at the edge of range; add a Bluetooth proxy closer to the remote.
- **Unknown button:** the press is reported as `unknown` with its raw code in the `button` attribute — please open an issue with that value.
- Enable debug logging:
  ```yaml
  logger:
    logs:
      custom_components.philips_ble_remote: debug
  ```

## License

MIT
