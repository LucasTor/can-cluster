# FuelTech FTCAN 2.0 device emulation — EGT-4 (+ Switchpad) findings

How to emulate FuelTech CAN peripherals on the car's **FTCAN 2.0** bus so the FT600
ECU treats an external device (a Raspberry Pi or ESP32) as a genuine accessory. Two
devices were reverse-engineered and **confirmed working on the actual car**:

- **EGT-4** — feeds 4 exhaust-gas-temperature channels into the ECU. ✅ working.
- **Switchpad-8** — injects button presses that trigger ECU functions (e.g. 3-Step). ✅ working.

Source of truth is the image-only `Protocol_FTCAN20.pdf` (render with
`pdftoppm -png` and read the PNGs). **The spec is incomplete/buggy in places** — notes
below record where reality differs from the document.

---

## FTCAN 2.0 frame basics

Every frame is CAN 2.0B, **29-bit extended ID, 1 Mbit/s**. The ID decomposes as:

```
ID[28:14] = ProductID (15 bits)   ID[13:11] = DataFieldID (3 bits)   ID[10:0] = MessageID (11 bits)
```

Verified by decoding the FT600's own broadcast `0x14080600` → ProductID `0x5020`
(= FT600 ECU), DataFieldID 0, MessageID `0x600`. ProductIDs: FT500 `0x5000`, FT600 `0x5020`.

There are two broadcast styles:
- **Real-time tagged** (MessageID `0x_FF`): `MeasureID(2B)+Value(2B)` pairs. What
  `can_helper.read_can` consumes from the ECU.
- **Simplified** (fixed per-device layout, MessageID `0x000`/device-specific): what the
  EGT-4 and Switchpad use. **These are what you emulate** — fixed layout, broadcast
  periodically, **no announce/handshake required.**

---

## EGT-4 — exhaust gas temperature (4 channels)

Authoritative spec: **"Simplified packets — EGT-4"**, `Protocol_FTCAN20.pdf` p25-26.
(Ignore the p32 "Example 5" — its annotation bytes are wrong; only the LED check values
on p25 are correct.)

| Field | Value |
|---|---|
| CAN ID (ext) | `0x02400000` (**model A — confirmed binding on the FT600**) |
| Other models | B `0x02480000`, C `0x02500000`, D `0x02580000` |
| Packet class | simplified (low byte `00`, **not** the real-time `0x_FF`) |
| DLC | 8 |
| Layout | 4 × `int16`, **big-endian signed**: ch1=bytes0-1, ch2=2-3, ch3=4-5, ch4=6-7 |
| Scale | **0.125 °C/bit** (raw = °C × 8) |
| Range | −50 … 1000 °C |
| Error/disconnect | channel reads `0x2000` (1050 °C) |

Spec check values (p25): `0x0008`=1 °C, `0x0FA0`(4000)=500 °C, `0xFFB0`(−80)=−10 °C.

**Example** — `100/200/300/400 °C` → `03 20 06 40 09 60 0C 80` on ID `0x02400000`.

### How we got here (mistakes worth not repeating)
1. First tried the **real-time tagged** broadcast `0x024000FF` (MessageID `0x0FF`) — the
   ECU ignored it and parked all channels at its no-data sentinel **3276.7** (`0x7FFF`).
   The EGT-4 is a **simplified** packet (`0x02400000`), not real-time.
2. Guessed the scale as ×16 then ×10; the spec's own check values prove **×8 (0.125 °C/bit)**.
3. Model matters — we swept `0x02400000/80/00/80`; **model A** is what this ECU binds.

The ECU does **not** echo EGT back, so EGT can only be confirmed in FTManager (or by eye).

---

## Switchpad-8 — inject button presses

Spec: **"Simplified packets — SwitchPanel"**, p26. The panel broadcasts a **Button
State** frame; the ECU triggers whatever each button is mapped to in FTManager.

| Field | Value |
|---|---|
| Button State ID (panel→ECU) | SW-8 `0x12200320` (confirmed), SW-8 mini `0x12218320`, SW-5 `0x12210320`, SW-5 mini `0x12208320` |
| Button Color ID (ECU→panel) | `0x12200321` (LED colors / state feedback) |
| DLC | 8 |
| Layout | `FF FF <byte2> <byte3> 00 00 00 00` |
| byte2 | bit0=Btn1 … bit3=Btn4 (bits 4-7 = 0) |
| byte3 | bit0=Btn5 … bit3=Btn8 (bits 4-7 = 0) |
| Rate | every 250 ms, or on change (50 ms min) |

**Example** — button 2 pressed → `FF FF 02 00 00 00 00 00`.

### Confirmed working — and how
- The ECU **registers our presses**: its Button Color reply (`0x12200321`) tracks our
  button state **1:1**. For button 2: pressed → `ff ff b0 e0 e2 b0 e0 60`, released →
  `ff ff b2 e0 e2 b0 e2 60` (byte2 bit1 + byte6 bit1 flip). **byte2/byte6 carry bit N for
  button N** — usable later for an "active functions" dash readout.
- **No rolling counter / handshake is needed.** We feared one (swept counter positions
  in bytes 7→0) but behavior was identical regardless — the plain documented frame works.
- The earlier "only the first press fires" was **not a bug**: the test button was mapped
  to **3-Step**, an *arm/level* function — a held press stays armed, so re-pressing the
  same state shows no new event. Per-button addressing also confirmed (any button you map
  the function to syncs to the right channel).

⚠️ **Switchpad presses trigger REAL ECU functions.** Map the test button to something
safe in FTManager before exercising it on a running car.

---

## Bus-collision safety

CAN bitwise arbitration makes frames with **different IDs** unable to corrupt each other
(lower ID wins, loser auto-retransmits). The only real risk is **two transmitters using
the same ID with different data**:
- Our EGT `0x02400000` / Switchpad `0x12200320` never clash with the ECU (`0x5020`).
- **Do not run an emulator alongside the real device** of the same type/ID.
- A second EGT-4 → use a different model ID (`0x02480000`…). A second Switchpad → different
  model ID. Our traffic is tiny (~1 % bus load), so no congestion concern.

---

## Hardware (for a standalone module)

- **ESP32** — built-in TWAI (CAN 2.0B) controller, 29-bit IDs @ 1 Mbit/s. Needs an
  external transceiver (no PHY on-chip).
- **CAN transceiver — TJA1051T/3 (selected for the final build).** `VIO → 3.3 V`
  (matches ESP32 logic, no level shifter), `VDD → 5 V` (rugged bus drive); automotive-
  grade. Equivalents: MCP2562FD, TCAN1042V/1051V. Bench-only: SN65HVD230 (3.3 V-native,
  easy) or 5 V-only MCP2551/TJA1050 (need an RXD level-shift).
- **EGT front-end** — 4 × MAX31855 (K-type thermocouple, SPI), one CS each.
- **120 Ω termination** only if the module sits at a physical end of the bus.

---

## Tooling in this repo

- **`validate_ftcan.py`** — standalone validator. Stop the dash service first, then:
  ```bash
  sudo systemctl stop can-cluster.service
  poetry run python validate_ftcan.py all       # or: egt | switch [N]
  sudo systemctl start can-cluster.service
  ```
  EGT = broadcast known temps (confirm in FTManager). Switch = press a button and
  **auto-verify** via the ECU's color reply (PASS/FAIL, no FTManager staring needed).
- **`esp32_egt4/`** — Arduino sketch + README for a standalone ESP32 EGT-4 module.
- **The dash itself contains no transmit code** — `can_helper.py` only *reads* the bus.
  All emulation/injection lives in the tools above so the cluster never actuates the ECU
  on its own.
