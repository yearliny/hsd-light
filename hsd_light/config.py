"""
Persistent config for caching the device BLE address.

Storage location: ``~/.config/hsd-light/config.json``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "hsd-light"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _read() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_address(address: str) -> None:
    """Cache a device BLE address."""
    data = _read()
    data["address"] = address
    _write(data)
    logger.info("Device address saved: %s", address)


def load_address() -> str | None:
    """Return the cached address, or ``None``."""
    return _read().get("address")


def clear_address() -> None:
    """Remove the cached address."""
    data = _read()
    data.pop("address", None)
    _write(data)
    logger.info("Cached device address cleared.")
