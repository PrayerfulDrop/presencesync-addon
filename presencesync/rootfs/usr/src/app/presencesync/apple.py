"""Wrapper around findmy.py — login, 2FA, and location fetching with persisted auth."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from findmy import AsyncAppleAccount, LoginState
from findmy.reports.anisette import RemoteAnisetteProvider
from findmy import KeyPair, KeyPairType

from . import state
from .decryptor import OwnedBeacon, load_bundle

log = logging.getLogger(__name__)


@dataclass
class LocationFix:
    identifier: str
    name: str
    model: str | None
    latitude: float
    longitude: float
    horizontal_accuracy: float
    timestamp_unix: int


class AppleClient:
    """Owns the AsyncAppleAccount + the loaded OwnedBeacons. Tracks login state."""

    def __init__(self):
        self.account: AsyncAppleAccount | None = None
        self.anisette: RemoteAnisetteProvider | None = None
        self.beacons: list[OwnedBeacon] = []
        self.beaconstore_key: bytes | None = None
        self._pending_2fa: object | None = None  # AsyncTrustedDeviceSecondFactor or AsyncSmsSecondFactor
        self.last_login_state: LoginState = LoginState.LOGGED_OUT

    async def ensure_account(self) -> None:
        """Create the AsyncAppleAccount if not already, attaching the anisette provider."""
        if self.account is not None:
            return
        anisette_url = state.get().apple.anisette_url or os.environ.get("PRESENCESYNC_ANISETTE_URL", "")
        if not anisette_url:
            raise RuntimeError("anisette_url is not configured")
        self.anisette = RemoteAnisetteProvider(anisette_url)
        # Try to resume from persisted state
        saved = state.load_apple_state()
        if saved:
            try:
                self.account = AsyncAppleAccount(anisette=self.anisette, state_info=saved)
                self.last_login_state = self.account.login_state
                log.info("Resumed Apple account from saved state: %s", self.last_login_state)
                return
            except Exception:
                log.exception("Failed to resume saved Apple state; will require login again")
                state.clear_apple_state()
        self.account = AsyncAppleAccount(anisette=self.anisette)

    async def login(self, username: str, password: str) -> LoginState:
        await self.ensure_account()
        assert self.account is not None
        result = await self.account.login(username, password)
        self.last_login_state = result
        self._persist()
        return result

    async def request_2fa(self, method_index: int = 0) -> None:
        assert self.account is not None
        methods = await self.account.get_2fa_methods()
        if not methods:
            raise RuntimeError("no 2FA methods available")
        method = methods[min(method_index, len(methods) - 1)]
        await method.request()
        self._pending_2fa = method

    async def submit_2fa(self, code: str) -> LoginState:
        assert self.account is not None
        if self._pending_2fa is None:
            methods = await self.account.get_2fa_methods()
            if not methods:
                raise RuntimeError("no 2FA methods to submit against")
            self._pending_2fa = methods[0]
        result = await self._pending_2fa.submit(code)
        self.last_login_state = result
        self._pending_2fa = None
        self._persist()
        return result

    def load_bundle(self, bundle_dir: Path) -> None:
        self.beaconstore_key, self.beacons = load_bundle(bundle_dir)
        log.info("Loaded bundle: %d beacons", len(self.beacons))

    async def fetch_locations(self) -> list[LocationFix]:
        if self.account is None or self.last_login_state != LoginState.LOGGED_IN:
            return []
        if not self.beacons:
            return []

        # Build KeyPair objects per beacon. Each beacon's private_key is the master key.
        targets = []
        beacons_by_pubkey: dict[str, OwnedBeacon] = {}
        for b in self.beacons:
            try:
                kp = KeyPair(private_key=b.private_key, key_type=KeyPairType.PRIMARY, name=b.name or b.identifier)
                targets.append(kp)
                beacons_by_pubkey[kp.hashed_adv_key_b64] = b  # convenience
            except Exception:
                log.exception("Failed to build KeyPair for beacon %s", b.identifier)

        try:
            reports = await self.account.fetch_location(targets)
        except Exception:
            log.exception("fetch_location failed")
            return []
        self._persist()  # may include refreshed tokens

        out: list[LocationFix] = []
        if isinstance(reports, dict):
            for kp, report in reports.items():
                if report is None:
                    continue
                beacon = beacons_by_pubkey.get(getattr(kp, "hashed_adv_key_b64", None), None)
                ident = beacon.identifier if beacon else getattr(kp, "name", "unknown")
                name = (beacon.name if beacon and beacon.name else getattr(kp, "name", None)) or ident
                model = beacon.model if beacon else None
                out.append(LocationFix(
                    identifier=ident,
                    name=name,
                    model=model,
                    latitude=float(report.latitude),
                    longitude=float(report.longitude),
                    horizontal_accuracy=float(report.horizontal_accuracy),
                    timestamp_unix=int(report.timestamp.timestamp()),
                ))
        return out

    def _persist(self) -> None:
        if self.account is None:
            return
        try:
            getstate = getattr(self.account, "__getstate__", None)
            if callable(getstate):
                state.save_apple_state(getstate())
        except Exception:
            log.debug("Could not persist Apple state", exc_info=True)
