# HSD Love Light CLI & SDK

Control your HSD Love Light BLE speaker-lamp from the command line — lighting, music, alarms, and more.

This project provides two layers:

- **SDK** (`hsd_light.protocol` + `hsd_light.device`) — integrate directly into any Python project
- **CLI** (`hsd` command) — one-liner terminal control for the device

## Requirements

- Python >= 3.10
- Bluetooth adapter with BLE support
- Windows / macOS / Linux

## Installation

From PyPI (recommended):

```bash
pip install hsd-light
```

Or from source (for development):

```bash
cd cli
pip install -e .
```

The `hsd` command will be available after installation.

## CLI Usage

### Global Options

```
hsd [OPTIONS] COMMAND
```

| Option | Description |
|--------|-------------|
| `-a, --address TEXT` | BLE MAC address (skip scanning) |
| `-t, --timeout FLOAT` | Scan / connection timeout in seconds (default: 10) |
| `-v, --verbose` | Enable debug logging |

### Scan for Device

```bash
hsd scan
# Found: HSD Love Light  [AA:BB:CC:DD:EE:FF]
```

### Light Control

```bash
# Preset colours
hsd light color red          # red / green / blue / white

# Custom RGB
hsd light rgb 255 0 128
hsd light rgb 255 100 0 --white 50 --brightness 80

# Brightness (0-100)
hsd light brightness 60

# Effects
hsd light effect gradient    # gradient / flow / dither
```

### Music Control

```bash
hsd music send play          # play / pause (toggle)
hsd music send next          # next track
hsd music send prev          # previous track
hsd music send volume-up     # volume up
hsd music send volume-down   # volume down
hsd music send eq            # cycle EQ modes
hsd music send source        # toggle BT / TF source
hsd music send mute          # mute
```

### Alarm

```bash
hsd alarm set 07:30              # set and enable alarm
hsd alarm set 22:00 --disable    # set but keep disabled
```

### Time Sync & Device Query

```bash
hsd sync     # sync system time to the device
hsd query    # query current device state
```

### Specifying a Device Address

If you already know the MAC address, skip scanning for a faster connection:

```bash
hsd -a AA:BB:CC:DD:EE:FF light color blue
```

## SDK Usage

### Quick Start

```python
import asyncio
from hsd_light import HSDDevice, Command
from hsd_light.protocol import MusicAction, ColorPreset, Effect

async def main():
    async with HSDDevice() as dev:
        # Set red, 80% brightness
        await dev.send(Command.color_preset(ColorPreset.RED))
        await dev.send(Command.brightness(80))

        # Custom colour
        await dev.send(Command.custom_color(r=255, g=0, b=128, w=0, brightness=100))

        # Gradient effect
        await dev.send(Command.effect(Effect.GRADIENT))

        # Music: play, next track
        await dev.send(Command.music(MusicAction.PLAY_PAUSE))
        await dev.send(Command.music(MusicAction.NEXT_TRACK))

        # Set alarm at 07:30
        await dev.send(Command.timer(7, 30, enabled=True))

asyncio.run(main())
```

### Specifying a Device Address

```python
async with HSDDevice(address="AA:BB:CC:DD:EE:FF") as dev:
    await dev.send(Command.brightness(50))
```

### Listening for Device Notifications

```python
async with HSDDevice() as dev:
    dev.on_notify = lambda data: print("Received:", data.hex())
    await dev.send(Command.query_params())
    await asyncio.sleep(2)  # wait for response
```

### Manual Connection Management

```python
dev = HSDDevice()
await dev.connect()          # scan + connect + auto time-sync
await dev.send(Command.brightness(100))
await dev.disconnect()
```

## BLE Protocol Overview

All commands are binary packets with the following format:

```
[0x69, 0x96, <length>, <cmd_type>, <payload...>]
 ──────────  ────────  ──────────  ───────────
   header     payload    command     command
              length      type       data
```

| Command | Type | Payload | Description |
|---------|------|---------|-------------|
| COLOR_MODE | 1 | `[preset]` | Preset colour / effect (1–7) |
| TIME_SYNC | 2 | `[year_hi, year_lo, month, day, hour, min, sec]` | Sync clock |
| CUSTOM_RGB | 3 | `[R, G, B, W, brightness]` | Custom RGBW colour |
| TIMER | 4 | `[hour, min, mode]` | Alarm setting |
| MUSIC | 8 | `[action]` | Music control (2–10) |
| QUERY | 15 | — | Query device state |
| BRIGHTNESS | 17 | `[value]` | Brightness (0–100) |

## Project Structure

```
cli/
├── pyproject.toml
├── README.md              # Chinese documentation
├── README_EN.md           # English documentation
└── hsd_light/
    ├── __init__.py        # Exports Command, HSDDevice
    ├── __main__.py        # python -m hsd_light
    ├── protocol.py        # Protocol layer — pure command builders, no dependencies
    ├── device.py          # Device layer — BLE connection management via bleak
    └── cli.py             # CLI layer — click-based command-line tool
```

## License

MIT
