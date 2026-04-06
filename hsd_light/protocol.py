"""
HSD Love Light BLE protocol — pure command builder, no I/O.

Every public method returns a ``bytes`` object ready to be written to the
device's BLE write characteristic.

Packet format
─────────────
  [0x69, 0x96, <length>, <cmd_type>, <payload …>]

  • 0x69 0x96  — fixed header
  • length     — number of bytes that follow the header (including cmd_type)
  • cmd_type   — command identifier
  • payload    — command-specific data
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum


# ── Header ────────────────────────────────────────────────────────────────────

HEADER = bytes([0x69, 0x96])


# ── Command types ─────────────────────────────────────────────────────────────

class CmdType(IntEnum):
    COLOR_MODE = 1
    TIME_SYNC = 2
    CUSTOM_RGB = 3
    TIMER = 4
    MUSIC = 8
    QUERY = 15
    BRIGHTNESS = 17


# ── Color / effect presets ────────────────────────────────────────────────────

class ColorPreset(IntEnum):
    RED = 1
    GREEN = 2
    BLUE = 3
    WHITE = 4


class Effect(IntEnum):
    GRADIENT = 5   # 渐变
    FLOW = 6       # 流动
    DITHER = 7     # 马达


# ── Music sub-commands ────────────────────────────────────────────────────────

class MusicAction(IntEnum):
    VOLUME_UP = 2
    VOLUME_DOWN = 3
    NEXT_TRACK = 4
    PREV_TRACK = 5
    PLAY_PAUSE = 7
    EQ_CYCLE = 8
    SOURCE_TOGGLE = 9   # BT ↔ TF
    MUTE = 10


# ── Command builder ──────────────────────────────────────────────────────────

def _pack(*payload: int) -> bytes:
    """Build a complete packet from *payload* bytes (cmd_type + data)."""
    length = len(payload)
    return HEADER + bytes([length]) + bytes(payload)


class Command:
    """Static factory that builds binary command packets."""

    # ── Query ─────────────────────────────────────────────────────────────

    @staticmethod
    def query_params() -> bytes:
        """Request current device parameters."""
        return _pack(CmdType.QUERY)

    # ── Time sync ─────────────────────────────────────────────────────────

    @staticmethod
    def time_sync(dt: datetime | None = None) -> bytes:
        """Sync the device clock.  Defaults to *now*."""
        dt = dt or datetime.now()
        year_hi = (dt.year & 0xFF00) >> 8
        year_lo = dt.year & 0xFF
        return _pack(
            CmdType.TIME_SYNC,
            year_hi, year_lo,
            dt.month, dt.day,
            dt.hour, dt.minute, dt.second,
        )

    # ── Light: preset color / effect ──────────────────────────────────────

    @staticmethod
    def color_preset(preset: ColorPreset | int) -> bytes:
        """Select a built-in colour (1-4) or effect (5-7)."""
        return _pack(CmdType.COLOR_MODE, int(preset))

    @staticmethod
    def effect(effect: Effect | int) -> bytes:
        """Shorthand for ``color_preset`` with an effect code."""
        return Command.color_preset(effect)

    # ── Light: custom RGBW + brightness ───────────────────────────────────

    @staticmethod
    def custom_color(
        r: int, g: int, b: int, w: int = 0, brightness: int = 100,
    ) -> bytes:
        """Set an arbitrary RGBW colour and brightness (0-100)."""
        return _pack(CmdType.CUSTOM_RGB, r, g, b, w, brightness)

    # ── Light: brightness only ────────────────────────────────────────────

    @staticmethod
    def brightness(value: int) -> bytes:
        """Set brightness (0-100) without changing colour."""
        return _pack(CmdType.BRIGHTNESS, max(0, min(100, value)))

    # ── Music ─────────────────────────────────────────────────────────────

    @staticmethod
    def music(action: MusicAction | int) -> bytes:
        """Send a music-control command."""
        return _pack(CmdType.MUSIC, int(action))

    # ── Timer / alarm ─────────────────────────────────────────────────────

    @staticmethod
    def timer(hour: int, minute: int, enabled: bool = True) -> bytes:
        """Set the alarm timer.  *enabled* controls the auto-brightness bit."""
        mode = 1 if enabled else 0
        return _pack(CmdType.TIMER, hour, minute, mode)
