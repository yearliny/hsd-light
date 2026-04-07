"""
High-level BLE device wrapper built on *bleak*.

Usage
─────
    async with HSDDevice() as dev:
        await dev.send(Command.brightness(80))
        await dev.send(Command.music(MusicAction.PLAY_PAUSE))

Or without a context manager:

    dev = HSDDevice()
    await dev.connect()
    await dev.send(Command.time_sync())
    await dev.disconnect()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Callable

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice

from hsd_light.config import load_address, save_address
from hsd_light.protocol import HEADER, Command

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

DEVICE_NAME = "HSD Love Light"
SERVICE_UUID = "0000eea0-0000-1000-8000-00805f9b34fb"
WRITE_DEBOUNCE = 0.2  # seconds — mirrors the 200 ms guard in the original app


# ── Device class ─────────────────────────────────────────────────────────────

class HSDDevice:
    """Manage a BLE connection to an HSD Love Light device."""

    def __init__(
        self,
        address: str | None = None,
        *,
        name: str = DEVICE_NAME,
        timeout: float = 10.0,
    ) -> None:
        self._address = address
        self._name = name
        self._timeout = timeout

        self._client: BleakClient | None = None
        self._ble_device: BLEDevice | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._notify_char: BleakGATTCharacteristic | None = None
        self._last_write: float = 0.0

        self.on_notify: Callable[[bytes], None] | None = None

    # ── Scanning ──────────────────────────────────────────────────────────

    async def scan(self, timeout: float | None = None) -> BLEDevice:
        """Scan for the target device and return the first match."""
        timeout = timeout or self._timeout
        logger.info("Scanning for '%s' (timeout=%ss)…", self._name, timeout)

        device = await BleakScanner.find_device_by_name(
            self._name, timeout=timeout,
        )
        if device is None:
            raise RuntimeError(
                f"Device '{self._name}' not found within {timeout}s. "
                "Make sure the device is powered on and nearby."
            )
        logger.info("Found device: %s [%s]", device.name, device.address)
        self._ble_device = device
        save_address(device.address)
        return device

    # ── Connection ────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Scan (if needed), connect, discover services, and sync time."""
        if self._address:
            logger.info("Connecting to address %s…", self._address)
            self._client = BleakClient(self._address, timeout=self._timeout)
        else:
            if self._ble_device is None:
                await self.scan()
            self._client = BleakClient(
                self._ble_device, timeout=self._timeout,
            )

        await self._client.connect()
        logger.info("Connected.")

        try:
            await self._discover_characteristics()
            await self._subscribe_notifications()

            # Sync time on connect — same as the original mini program
            await self.send(Command.time_sync())
            logger.info("Time synced to device.")
        except Exception:
            await self._client.disconnect()
            raise

    async def disconnect(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            logger.info("Disconnected.")

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    # ── Service / characteristic discovery ────────────────────────────────

    async def _discover_characteristics(self) -> None:
        assert self._client is not None
        for service in self._client.services:
            if SERVICE_UUID not in service.uuid.lower():
                continue
            for char in service.characteristics:
                if "write" in char.properties:
                    self._write_char = char
                    logger.debug("Write char: %s", char.uuid)
                if "notify" in char.properties or "read" in char.properties:
                    self._notify_char = char
                    logger.debug("Notify char: %s", char.uuid)

        if self._write_char is None:
            raise RuntimeError(
                "Could not find a writable characteristic on the device."
            )

    async def _subscribe_notifications(self) -> None:
        if self._notify_char is None:
            logger.warning("No notify characteristic found; skipping subscription.")
            return

        def _handler(_char: BleakGATTCharacteristic, data: bytearray) -> None:
            if data[:2] == bytearray(HEADER):
                logger.debug("← %s", data.hex())
                if self.on_notify:
                    self.on_notify(bytes(data))

        await self._client.start_notify(self._notify_char, _handler)

    # ── Write ─────────────────────────────────────────────────────────────

    async def send(self, data: bytes) -> None:
        """Write a command packet, respecting the 200 ms debounce."""
        if not self.is_connected:
            raise RuntimeError("Not connected to device.")

        loop = asyncio.get_running_loop()
        now = loop.time()
        wait = self._last_write + WRITE_DEBOUNCE - now
        if wait > 0:
            await asyncio.sleep(wait)

        logger.debug("→ %s", data.hex())
        await self._client.write_gatt_char(self._write_char, data)
        self._last_write = loop.time()

    # ── Context manager ───────────────────────────────────────────────────

    async def __aenter__(self) -> "HSDDevice":
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.disconnect()
