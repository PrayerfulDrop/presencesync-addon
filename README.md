# AirTagSync Home Assistant Add-on Repository

A single Home Assistant add-on supporting the [AirTagSync](https://github.com/PrayerfulDrop/airtagsync-ha) integration:

- **Anisette** — generates Apple-compatible auth headers so the integration can talk to Apple's Find My gateway. This is required because Apple's API expects per-request signed headers that normally only Apple devices know how to make.

## Install

1. Open Home Assistant.
2. **Settings → Add-ons → Add-on Store → ⋯ (top right) → Repositories.**
3. Add this URL and click **Add**:
   ```
   https://github.com/PrayerfulDrop/airtagsync-addon
   ```
4. Close the dialog. The "AirTagSync Anisette" add-on now appears in the Store.
5. Click **Install**, then **Start**. Toggle **Start on boot**.
6. The add-on now serves anisette headers at `http://homeassistant.local:6969` (or whatever the HA host's address is from the integration's perspective — usually `http://addon_local_anisette:6969` inside the HA network).

That's it. The AirTagSync integration's config flow will ask for this URL.

## What this add-on actually runs

This is a thin Home Assistant wrapper around [`dadoum/anisette-v3-server`](https://github.com/Dadoum/anisette-v3-server) — a single open-source Go binary that emulates Apple's hardware-attestation API. The add-on is < 30 MB.

## Updating

When `dadoum/anisette-v3-server` ships a new image we'll bump the version here. Home Assistant will offer the update in the Add-on Store.

## Troubleshooting

**Add-on won't start** — Check Settings → Add-ons → AirTagSync Anisette → Log. Most failures are network-related (Docker pull failed). Restart the Supervisor and retry.

**Integration can't reach anisette** — From the integration container's perspective the add-on is reachable at `http://homeassistant.local:6969` or `http://<HA-IP>:6969`. If those don't work, your HA setup might have Docker networking weirdness — try `http://supervisor:6969` or set `host_network: true` in the add-on config.

## License

MIT — wrapper code only. Underlying anisette-v3-server is GPL-3.0 (see [Dadoum/anisette-v3-server](https://github.com/Dadoum/anisette-v3-server)).
