<p align="center">
  <img src="logo.png" alt="PresenceSync" width="160" height="160"/>
</p>

<h1 align="center">PresenceSync</h1>

<p align="center">
  <em>Apple Find My → Home Assistant. AirTags, AirPods, iPhones, iPads, Macs, Watches.</em><br>
  <em>One-click install. No MQTT bridge running on your Mac. No SSH. No ongoing Mac dependency.</em>
</p>

<hr>

## What this does

After a one-time setup (about 15 minutes), PresenceSync queries Apple's Find My gateway **directly from inside Home Assistant**. Your AirTags and Apple devices appear as native `device_tracker` entities, updated every minute, with full GPS attributes and home/away resolution.

The Mac you used to set it up can be turned off, put back in its drawer, or have SIP re-enabled — none of that breaks PresenceSync. Apple session credentials live in HA's encrypted storage and auto-refresh.

## Repository contents

Two Home Assistant add-ons in a single repository:

| Add-on | What it is | Touched by user? |
| --- | --- | --- |
| **PresenceSync** | Main app. FastAPI web UI in your HA sidebar. Drives `findmy.py` against Apple, publishes via MQTT auto-discovery. | Yes (setup wizard) |
| **PresenceSync Anisette** | Wraps [`dadoum/anisette-v3-server`](https://github.com/Dadoum/anisette-v3-server). Provides the Apple-compatible signed headers Apple's gateway demands. | No — internal only |

## Quick start

### Step 1 — Add this repository to your HA Add-on Store

In Home Assistant:

1. **Settings → Add-ons → Add-on Store**
2. Top-right **⋯ → Repositories**
3. Paste this URL and click **Add**:
   ```
   https://github.com/PrayerfulDrop/presencesync-addon
   ```

### Step 2 — Install and start both add-ons

The Store now shows two new add-ons. Install both:

- **PresenceSync Anisette** → Install → Start → toggle **Start on boot**
- **PresenceSync** → Install → Start → toggle **Start on boot**

First start of PresenceSync downloads its Python dependencies (`findmy`, `paho-mqtt`, `fastapi`). Allow 1–2 minutes.

### Step 3 — Extract your Apple keys (one time on a Mac)

The extractor needs to run on a Mac that's signed in to the same Apple ID as your AirTags. **The Mac is only needed for this one-time step** — everything after that runs inside HA.

```bash
git clone https://github.com/PrayerfulDrop/findmy-key-extractor.git ~/src/findmy-key-extractor
cd ~/src/findmy-key-extractor
git checkout x86_64-port    # Intel + Apple Silicon support

# Disable SIP + set AMFI boot-arg first — see docs/mac-setup.md.
# (You can re-enable both after extraction completes.)

sudo ./extract.sh                  # captures FMIP + FMF + LocalStorage keys
sudo ./extract_beaconstore.sh      # captures BeaconStore key
./bundle.sh                        # packages everything into presencesync-bundle.tar.gz
```

Copy `presencesync-bundle.tar.gz` to whatever computer you'll use to open Home Assistant in a browser (e.g. AirDrop it to your phone, or save to a USB stick).

### Step 4 — Open PresenceSync's web UI in Home Assistant

Click **PresenceSync** in the HA left sidebar. A web UI opens, walking you through four sections:

1. **MQTT broker** — defaults to `core-mosquitto`. Set username/password if your broker requires auth.
2. **Home location** — your latitude/longitude/radius. Pin this on the HA map if you don't know your exact coordinates.
3. **Upload extractor bundle** — drag in the `.tar.gz` you produced on the Mac.
4. **Apple ID** — paste your iCloud email and password. Click **Log in**. A 6-digit code pops up on your trusted Apple devices. Enter it. Done.

Within 60 seconds, your AirTags + Apple devices appear in **Settings → Devices & Services → MQTT**.

## What you get in Home Assistant

For each tracked item (AirTag, AirPods component, iPhone, iPad, Mac, Watch):

- `device_tracker.<name>` — GPS-source tracker with `latitude`, `longitude`, `gps_accuracy`, `last_seen`. HA's zone resolver handles `home` / `not_home` / `school` / etc. automatically.
- A device card grouping the entity, with manufacturer **Apple** and the real model (e.g. `iPhone17,2`, `Macmini8,1`, `AirPods Pro (2nd generation)`).

You can use these in **Lovelace cards**, **automations**, **history**, **logbook**, and the **map view** like any other HA device tracker.

## How it actually works

```
┌────────────────────────────────────────────────────────────────────┐
│ Home Assistant (no Mac needed after setup)                         │
│                                                                    │
│  ┌──────────────────────┐    ┌──────────────────────────────────┐  │
│  │ PresenceSync add-on  │───▶│ PresenceSync Anisette add-on     │  │
│  │  (FastAPI + findmy)  │    │  (Apple-compatible auth headers) │  │
│  └──────────┬───────────┘    └──────────────────────────────────┘  │
│             │                                                      │
│             │ MQTT publish (auto-discovery)                        │
│             ▼                                                      │
│  ┌──────────────────────┐                                          │
│  │ Mosquitto add-on     │──▶ device_tracker.airtag_swim_bag        │
│  │                      │    device_tracker.iphone17_2             │
│  └──────────────────────┘    sensor.airpods_pro_battery, …         │
└────────────────────────────────────────────────────────────────────┘
                                ▲
                                │ HTTPS poll (every 60s by default)
                                ▼
                       ┌────────────────────┐
                       │ Apple's gateway    │   ◀── all real location data
                       │ gateway.icloud.com │
                       └────────────────────┘
```

- The Mac is **out of the picture** once you've uploaded the bundle.
- Apple ID auth state is persisted to HA's `/data` volume — surviving restarts and updates.
- 2FA only triggers if Apple invalidates the session (rare, typically once a year).

## Reconfigure / reset

PresenceSync's web UI has a **Reset** button that clears the Apple session + bundle while keeping your MQTT and home-location settings. Useful if you change your Apple ID password (re-extract bundle + re-login) or want to wipe state.

## Requirements

- Home Assistant **OS** or **Supervised**, 2024.1 or newer (so the add-on store works and ingress UI is supported).
- Mosquitto add-on (or any MQTT broker reachable from HA) — used to publish entities.
- One Mac, **one time only**, for key extraction (Apple Silicon **or** Intel).
- Your Apple ID + password + access to a trusted Apple device for the 2FA prompt.

## Licensing

- This repository's wrapper code: **MIT**.
- `anisette-v3-server`: **GPL-3.0** (see [Dadoum/anisette-v3-server](https://github.com/Dadoum/anisette-v3-server)).
- `findmy.py`: **MIT** (see [malmeloo/FindMy.py](https://github.com/malmeloo/FindMy.py)).

## Acknowledgements

This project stands on three pieces of community work:

- [`findmy-key-extractor`](https://github.com/manonstreet/findmy-key-extractor) by manonstreet — the original ARM64 extractor, now extended to Intel + BeaconStore in [our fork](https://github.com/PrayerfulDrop/findmy-key-extractor).
- [`FindMySyncPlus`](https://github.com/manonstreet/FindMySyncPlus) by manonstreet — proved out ChaCha20-Poly1305 against `Items.data` and demonstrated the MQTT path.
- [`FindMy.py`](https://github.com/malmeloo/FindMy.py) by malmeloo — the high-level Apple Find My protocol client this project drives.
