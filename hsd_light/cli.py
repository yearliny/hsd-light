"""
CLI entry-point for HSD Love Light.

    hsd light color red
    hsd light rgb 255 0 128 --brightness 80
    hsd light effect gradient
    hsd light brightness 50
    hsd music play
    hsd music volume-up
    hsd alarm set 07:30
    hsd sync
    hsd scan
"""

from __future__ import annotations

import asyncio
import logging
import sys

import click

from hsd_light.device import HSDDevice
from hsd_light.protocol import (
    ColorPreset,
    Command,
    Effect,
    MusicAction,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(coro):
    """Run an async coroutine, handling KeyboardInterrupt gracefully."""
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        click.echo("\nAborted.")
        sys.exit(130)


def _device_from_ctx(ctx: click.Context) -> HSDDevice:
    return HSDDevice(
        address=ctx.obj.get("address"),
        timeout=ctx.obj.get("timeout", 10.0),
    )


async def _send_and_close(ctx: click.Context, data: bytes, label: str) -> None:
    dev = _device_from_ctx(ctx)
    async with dev:
        await dev.send(data)
    click.echo(f"OK — {label}")


# ── Root group ───────────────────────────────────────────────────────────────

@click.group()
@click.option(
    "-a", "--address",
    default=None,
    help="BLE MAC address (skip scanning if provided).",
)
@click.option(
    "-t", "--timeout",
    default=10.0, show_default=True,
    help="Scan / connection timeout in seconds.",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable debug logging.",
)
@click.pass_context
def main(ctx: click.Context, address: str | None, timeout: float, verbose: bool):
    """Control an HSD Love Light BLE device from the command line."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)-8s %(message)s",
    )
    ctx.ensure_object(dict)
    ctx.obj["address"] = address
    ctx.obj["timeout"] = timeout


# ── scan ─────────────────────────────────────────────────────────────────────

@main.command()
@click.pass_context
def scan(ctx: click.Context):
    """Scan for the HSD Love Light device and print its address."""
    async def _scan():
        dev = _device_from_ctx(ctx)
        ble = await dev.scan()
        click.echo(f"Found: {ble.name}  [{ble.address}]")

    _run(_scan())


# ── sync ─────────────────────────────────────────────────────────────────────

@main.command()
@click.pass_context
def sync(ctx: click.Context):
    """Sync the current system time to the device."""
    _run(_send_and_close(ctx, Command.time_sync(), "time synced"))


# ── light ────────────────────────────────────────────────────────────────────

@main.group()
def light():
    """Light controls (colour, brightness, effects)."""


main.add_command(light)

# -- light color <preset>
_COLOR_MAP = {
    "red": ColorPreset.RED,
    "green": ColorPreset.GREEN,
    "blue": ColorPreset.BLUE,
    "white": ColorPreset.WHITE,
}


@light.command("color")
@click.argument("preset", type=click.Choice(list(_COLOR_MAP), case_sensitive=False))
@click.pass_context
def light_color(ctx: click.Context, preset: str):
    """Set a preset colour (red / green / blue / white)."""
    _run(_send_and_close(ctx, Command.color_preset(_COLOR_MAP[preset.lower()]),
                         f"color → {preset}"))


# -- light rgb R G B [--white W] [--brightness B]
@light.command("rgb")
@click.argument("r", type=click.IntRange(0, 255))
@click.argument("g", type=click.IntRange(0, 255))
@click.argument("b", type=click.IntRange(0, 255))
@click.option("-w", "--white", default=0, type=click.IntRange(0, 255),
              show_default=True, help="White channel value.")
@click.option("-b", "--brightness", "bright", default=100,
              type=click.IntRange(0, 100), show_default=True, help="Brightness %.")
@click.pass_context
def light_rgb(ctx: click.Context, r: int, g: int, b: int, white: int, bright: int):
    """Set a custom RGBW colour."""
    _run(_send_and_close(
        ctx,
        Command.custom_color(r, g, b, white, bright),
        f"color → rgb({r},{g},{b}) w={white} brightness={bright}%",
    ))


# -- light brightness <value>
@light.command("brightness")
@click.argument("value", type=click.IntRange(0, 100))
@click.pass_context
def light_brightness(ctx: click.Context, value: int):
    """Set brightness (0-100) without changing colour."""
    _run(_send_and_close(ctx, Command.brightness(value),
                         f"brightness → {value}%"))


# -- light effect <name>
_EFFECT_MAP = {
    "gradient": Effect.GRADIENT,
    "flow": Effect.FLOW,
    "dither": Effect.DITHER,
}


@light.command("effect")
@click.argument("name", type=click.Choice(list(_EFFECT_MAP), case_sensitive=False))
@click.pass_context
def light_effect(ctx: click.Context, name: str):
    """Activate a lighting effect (gradient / flow / dither)."""
    _run(_send_and_close(ctx, Command.effect(_EFFECT_MAP[name.lower()]),
                         f"effect → {name}"))


# ── music ────────────────────────────────────────────────────────────────────

@main.group()
def music():
    """Music playback controls."""


_MUSIC_ACTIONS = {
    "play":          MusicAction.PLAY_PAUSE,
    "pause":         MusicAction.PLAY_PAUSE,
    "next":          MusicAction.NEXT_TRACK,
    "prev":          MusicAction.PREV_TRACK,
    "volume-up":     MusicAction.VOLUME_UP,
    "volume-down":   MusicAction.VOLUME_DOWN,
    "eq":            MusicAction.EQ_CYCLE,
    "source":        MusicAction.SOURCE_TOGGLE,
    "mute":          MusicAction.MUTE,
}


@music.command("send")
@click.argument("action", type=click.Choice(list(_MUSIC_ACTIONS), case_sensitive=False))
@click.pass_context
def music_send(ctx: click.Context, action: str):
    """Send a music command (play/pause/next/prev/volume-up/volume-down/eq/source/mute)."""
    _run(_send_and_close(ctx, Command.music(_MUSIC_ACTIONS[action.lower()]),
                         f"music → {action}"))


# ── alarm ────────────────────────────────────────────────────────────────────

@main.group()
def alarm():
    """Alarm / timer controls."""


@alarm.command("set")
@click.argument("time", metavar="HH:MM")
@click.option("--enable/--disable", default=True, show_default=True,
              help="Enable or disable the alarm.")
@click.pass_context
def alarm_set(ctx: click.Context, time: str, enable: bool):
    """Set the alarm timer (e.g. hsd alarm set 07:30)."""
    try:
        hour, minute = (int(x) for x in time.split(":"))
    except ValueError:
        raise click.BadParameter("Time must be HH:MM format.", param_hint="TIME")
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise click.BadParameter("Hour must be 0-23, minute 0-59.", param_hint="TIME")
    label = "enabled" if enable else "disabled"
    _run(_send_and_close(ctx, Command.timer(hour, minute, enable),
                         f"alarm → {hour:02d}:{minute:02d} ({label})"))


# ── query ────────────────────────────────────────────────────────────────────

@main.command()
@click.pass_context
def query(ctx: click.Context):
    """Query the device's current parameters."""
    async def _query():
        dev = _device_from_ctx(ctx)
        responses: list[bytes] = []

        def _collect(data: bytes):
            responses.append(data)

        async with dev:
            dev.on_notify = _collect
            await dev.send(Command.query_params())
            # Give the device a moment to respond
            await asyncio.sleep(1.0)

        if responses:
            for resp in responses:
                click.echo(f"Response: {resp.hex()}")
        else:
            click.echo("No response received (device may not support query).")

    _run(_query())
