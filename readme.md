# CAN Cluster

A custom digital gauge cluster for a **1992 VW Gol G1** (turbo). It reads engine data from a
**FuelTech ECU over CAN** (FTCAN 2.0) plus dashboard switches over **GPIO**, and renders a
minimal dark dashboard on a cheap 1920×720 display driven by a **Raspberry Pi**.

The styling is a minimal, period-with-a-cyber-edge look anchored on the car's "Azul Boreal"
blue (modelled on a Claude Design mockup, *Painel Gol Minimal*): hairline analog gauges, a
no-box centre readout, and tell-tale "pills" that stay dark until they have something to say.

![cluster](docs/cluster.png)

## Hardware

- Raspberry Pi 5 running **Armbian** (Debian bookworm), displaying full-screen via Kivy on
  SDL2 / KMS-DRM (no desktop environment).
- A 10.3" **1920×720** display.
- **FuelTech ECU** on the CAN bus (`can0`, socketcan), broadcasting FTCAN 2.0.
- Dashboard switches (turn signals, high beam, parking brake, …) wired to the Pi's **GPIO**.

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

## Project layout

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

## Data flow

```
CAN thread  (can_helper.read_can) ┐
                                  ├─► SensorState ─► Dashboard.update() @30Hz ─► widgets
GPIO thread (gpio_helper.read_io) ┘
```

`SensorState` (in `model.py`) is a thread-safe `@dataclass` shared between the reader threads and
the Kivy render loop. The CAN thread calls `state.update({...})` for each decoded frame; the GPIO
thread updates `state.io`. The dashboard reads the state 30×/s and pushes values into the widgets.

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

The Pi's root filesystem is kept **read-only** in normal use (Armbian *overlayroot* — writes go to
RAM and are discarded), so an ignition-off power cut can never corrupt the SD card. The
`deploy.sh` script handles the writable↔read-only cycle and the reboots:

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

## Logs

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

## License / status

Personal project, no warranty. Made to run on a Raspberry Pi with a FuelTech ECU.
