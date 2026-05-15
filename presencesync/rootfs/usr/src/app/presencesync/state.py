"""Persistent state — survives container restarts via /data volume."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("PRESENCESYNC_DATA_DIR", "/data"))
CONFIG_PATH = DATA_DIR / "presencesync.json"
APPLE_STATE_PATH = DATA_DIR / "apple_state.json"
BUNDLE_DIR = DATA_DIR / "bundle"  # extracted bundle contents


@dataclass
class HomeLocation:
    latitude: float = 0.0
    longitude: float = 0.0
    radius_m: int = 100


@dataclass
class MqttConfig:
    host: str = "core-mosquitto"
    port: int = 1883
    username: str = ""
    password: str = ""
    discovery_prefix: str = "homeassistant"
    state_prefix: str = "presencesync"


@dataclass
class AppleConfig:
    username: str = ""
    password: str = ""           # stored in clear text on the add-on's /data volume; HA-controlled
    anisette_url: str = ""


@dataclass
class TrackingConfig:
    poll_interval_s: int = 60
    include_audio_accessories: bool = False  # AirPods etc
    include_devices: bool = True             # iPhone / iPad / Mac / Watch
    include_airtags: bool = True
    ignored_identifiers: list[str] = field(default_factory=list)


@dataclass
class Settings:
    apple: AppleConfig = field(default_factory=AppleConfig)
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    home: HomeLocation = field(default_factory=HomeLocation)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    bundle_uploaded: bool = False  # set True once user uploads a presencesync-bundle.tar.gz

    @classmethod
    def load(cls) -> "Settings":
        if not CONFIG_PATH.exists():
            return cls()
        raw = json.loads(CONFIG_PATH.read_text())
        return cls(
            apple=AppleConfig(**raw.get("apple", {})),
            mqtt=MqttConfig(**raw.get("mqtt", {})),
            home=HomeLocation(**raw.get("home", {})),
            tracking=TrackingConfig(**raw.get("tracking", {})),
            bundle_uploaded=raw.get("bundle_uploaded", False),
        )

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2))
        tmp.replace(CONFIG_PATH)


# Single in-memory copy plus a write lock
_settings = Settings.load()
_lock = asyncio.Lock()


def get() -> Settings:
    return _settings


async def update(mutator) -> Settings:
    async with _lock:
        mutator(_settings)
        _settings.save()
    return _settings


# --- Apple auth state (separate file because it's binary-ish) -----------

def save_apple_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    APPLE_STATE_PATH.write_text(json.dumps(state, default=str))


def load_apple_state() -> dict | None:
    if not APPLE_STATE_PATH.exists():
        return None
    try:
        return json.loads(APPLE_STATE_PATH.read_text())
    except json.JSONDecodeError:
        return None


def clear_apple_state() -> None:
    APPLE_STATE_PATH.unlink(missing_ok=True)
