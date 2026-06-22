# CAN Cluster

*A custom digital gauge cluster for a turbo 1992 VW Gol G1 — Raspberry Pi · FuelTech CAN · Kivy.*

It reads engine data from a **FuelTech ECU over CAN** (FTCAN 2.0) and dashboard switches over
**GPIO**, and renders a minimal dark dashboard on a cheap 1920×720 display driven by a
**Raspberry Pi**. The whole thing runs headless off the car's ignition power and is designed to
survive being cut off mid-frame (see [Deploying](#deploying-to-the-pi)).

The styling is a minimal, period-with-a-cyber-edge look anchored on the car's "Azul Boreal" blue
(modelled on a Claude Design mockup, *Painel Gol Minimal*): hairline analog gauges, a no-box
centre readout, and tell-tale "pills" that stay dark until they have something to say.

![cluster](docs/cluster.png)

Running in the car ([full video](docs/cluster-demo.mp4)):

![cluster running](docs/cluster-demo.gif)

## What it shows

- **Two analog gauges** — speed (left) and RPM (right): hairline major/minor ticks, a thin
  Azul Boreal needle and progress arc, redline arc, and a centre digit (RPM shows `3.2k`-style
  above 1000). A startup self-test sweep runs on boot.
- **Shift light** — above 6000 rpm the RPM gauge flashes aggressively: red disc wash, fat amber
  arc + needle, steady red `SHIFT!`.
- **Centre readout** (no box) — AIR / ENGINE / OIL / FUEL micro-grid, then big **BOOST** and
  **LAMBDA** with colour cues (lambda RICH/STOICH/LEAN, boost red over 1.32 bar).
- **Tell-tales** — a top row of pills: turn signals (◄ ►), HIGH beam, OIL, TEMP, FAN, FUEL,
  BRAKE, 2-STEP, etc. Plus a standalone **WIFI** pill (top-left, hidden unless connected).
- **No-CAN demo mode** — after ~3 s with no CAN frames (on a bench), an animated drive loop
  plays so the cluster is alive without the car. Real data takes over the moment it appears.

## Hardware

- **Raspberry Pi 5** running **Armbian** (Debian bookworm), displaying full-screen via Kivy on
  SDL2 / KMS-DRM (no desktop environment).
- A 10.3" **1920×720** display.
- A **CANable V2.0 Pro** USB↔CAN adapter (socketcan, `can0`) connecting the Pi to the
  **FuelTech ECU**, which broadcasts FTCAN 2.0.
- An **8-channel optocoupler board** isolating the car's dashboard switches (turn signals, high
  beam, parking brake, …) before they reach the Pi's **GPIO**, so 12 V automotive signals never
  touch the 3.3 V pins.
- A **buck converter** stepping the car's 12 V down to 5 V for the Pi.
- Everything mounted in a 3D-printed enclosure behind the display.

The complete build, seen from the back — Pi 5 (centre), CANable adapter (top-left), optocoupler
board (bottom-left) and buck converter (centre):

![back of the cluster](docs/cluster-back.jpg)

## How it works

```
CAN thread  (can_helper.read_can) ┐
                                  ├─► SensorState ─► Dashboard.update() @30Hz ─► widgets
GPIO thread (gpio_helper.read_io) ┘
```

`SensorState` (in `model.py`) is a thread-safe `@dataclass` shared between the reader threads and
the Kivy render loop. The CAN thread calls `state.update({...})` for each decoded frame; the GPIO
thread updates `state.io`. The dashboard reads the state 30×/s and pushes values into the widgets.
Because rendering only ever *reads* a snapshot of the state, a slow or silent sensor never stalls
the UI.

### Project layout

```
cluster.py          Kivy app: Dashboard + CarClusterApp; window/gauge config; render loop + demo
start_cluster.py    Production entry point — spawns CAN + GPIO reader threads, runs the app
model.py            SensorState / IoState — the thread-safe shared data model
can_helper.py       read_can(): decode the FTCAN simplified broadcast into SensorState
gpio_helper.py      read_io(): read GPIO pins into SensorState.io (+ change-logging)
demo.py             simulate(t): the drive simulation used by no-CAN demo mode
theme.py            All colours and layout constants
widgets/
  gauge.py          The analog Gauge (ticks, needle, arc, shift light)
  center_info.py    The centre readout (CenterInfo) — micro-grid + BOOST/LAMBDA
  top_alerts.py     TopAlerts: the tell-tale pill row + WiFi pill (TellTale)
  readout.py        Small value-with-threshold-colour helper
fonts/              Bundled fonts (Share Tech Mono, Compagnon, …)
deploy.sh           Deploy to the Pi and manage its read-only overlay
logs.sh             Tail the running cluster's logs from the Pi
```

## Running

Dependencies are managed with **Poetry** (Python ≥3.10, Kivy, python-can, …).

```bash
poetry install

# Desktop preview (no CAN/GPIO): windowed, and it self-animates the demo loop
poetry run python cluster.py

# Full run with CAN + GPIO reader threads (on the Pi)
poetry run python start_cluster.py
```

`DEV` (env var, default `true`) gives a half-size preview window. On the Pi, production runs with
`DEV=false` for the full 1920×720 window. The no-CAN demo is independent of `DEV` — it triggers
whenever no CAN frame has arrived for a few seconds.

On the Pi the app is a **systemd service**, `can-cluster.service`, which runs
`/usr/local/bin/start-can-cluster.sh` (sets the Kivy/KMS env, `cd`s to the project, runs
`start_cluster.py`).

## Deploying to the Pi

The car cuts power to the Pi the instant the ignition goes off, so the root filesystem is kept
**read-only** in normal use (Armbian *overlayroot* — writes go to RAM and are discarded on power
loss). That way an ignition-off power cut can never corrupt the SD card. The `deploy.sh` script
handles the writable↔read-only cycle and the reboots it requires:

```bash
./deploy.sh          # make writable → sync the repo → re-enable read-only (ends power-safe)
./deploy.sh --no-ro  # deploy but leave it writable (iterating); ./deploy.sh --ro when done
./deploy.sh --rw     # just switch to read-write
./deploy.sh --ro     # just switch to read-only
./deploy.sh --status # report the current mode
```

Connection settings default to `192.168.0.153` / `lucas` / `lucas` and are overridable via
`PI_HOST` / `PI_USER` / `PI_PASS`. Requires `sshpass` locally (`brew install sshpass`), or set up
an SSH key (`ssh-copy-id`) and it works passwordless. Read-only is toggled by an
`overlayroot=tmpfs` token in `/boot/firmware/cmdline.txt` (on the always-writable FAT partition,
so it's recoverable by mounting the SD card on any computer).

> **Always finish with the Pi read-only.** After any `--no-ro` / `--rw` iteration, run
> `./deploy.sh --ro` so the next ignition-off can't corrupt the card.

## Logs

The app is headless, so the systemd journal is the way to check on it:

```bash
./logs.sh          # follow all cluster logs live
./logs.sh gpio     # follow only the [gpio] pin lines (handy for finding wiring)
./logs.sh 100      # last 100 lines and exit
```

## Wiring a GPIO switch to a tell-tale

Three names have to line up:

1. **`gpio_helper.py`** — a `Pin` enum entry, e.g. `PARKING_BRAKE = 16` (name = BCM pin).
2. **`model.py`** — an `IoState` field with the **same name lowercased**, e.g. `parking_brake: bool`.
   (`IoState.update()` drops any reading whose pin name has no matching field.)
3. **`widgets/top_alerts.py`** — in `set_state`, point a pill key at it (`"brake": io.parking_brake`),
   and make sure a matching entry exists in `PILLS`.

Then `./deploy.sh`. To discover which physical switch is on which pin, run `./logs.sh gpio` and
flip switches one at a time — the pin that logs `-> ON` is the one.

## FuelTech CAN notes

`can_helper.py` currently decodes the FTCAN 2.0 **simplified broadcast** — four fixed frames
(`0x14080600`–`0x14080603`, extended IDs) carrying RPM, MAP/boost, air/engine/oil temps, oil/fuel/
water pressures, gear, lambda, pit-limit and the four wheel speeds. Signals like the radiator-fan
output, 2-step/launch status and individual ECU output states live in FuelTech's **real-time
tagged broadcast** (not yet read by this project) — see the FTCAN 2.0 protocol spec for the map.

## Status

Personal project, no warranty. Made to run on a Raspberry Pi with a FuelTech ECU — the pin map and
a few tell-tales (fan, 2-step) are still being wired up on the real car.
</content>
</invoke>
