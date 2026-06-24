# esp32_egt4 — FuelTech EGT-4 CAN emulator

An ESP32 that broadcasts a 4-channel EGT module on the **FTCAN 2.0** bus, so the
FuelTech ECU (and/or the Pi cluster) gets four exhaust-gas-temp channels over CAN.

This is a documented FuelTech device type — see the **"Simplified packets — EGT-4"**
section of `../Protocol_FTCAN20.pdf` (p25-26). (The "Example 5" on p32 has bogus
annotations — the p25 simplified-packet spec is authoritative.) The sketch currently
sends fixed test values (100/200/300/400 °C); swap in thermocouple reads to make it real.

## The frame

| Field | Value |
|---|---|
| CAN ID (extended, 29-bit) | `0x02400000` (EGT-4 **model A** — confirmed binding) |
| Other models | B `0x02480000`, C `0x02500000`, D `0x02580000` |
| Packet class | simplified broadcast (MessageID `0x000`, **not** the real-time `0x_FF`) |
| Bitrate | **1 Mbit/s** |
| DLC | 8 |
| Payload | 4 × `int16`, **big-endian, signed** → channels 1..4 at bytes 0-1/2-3/4-5/6-7 |
| Scale | `°C × 8` (**0.125 °C/bit**) |
| Range / error | −50…1000 °C; disconnected/error channel = `0x2000` (1050 °C) |

Example: 100/200/300/400 °C → `03 20 06 40 09 60 0C 80`.

Spec check values (p25): `0x0008` = 1 °C, `0x0FA0` (4000) = 500 °C, `0xFFB0` (−80) = −10 °C.

## Hardware

- **ESP32** — built-in TWAI (CAN 2.0B) controller, supports 29-bit IDs @ 1 Mbit/s.
- **CAN transceiver — TJA1051T/3 (selected for the final build).** The `/3` variant
  has a **VIO** pin: tie `VIO → 3.3 V` (logic side matches the ESP32 directly, no level
  shifter) and `VDD → 5 V` (rugged bus drive). Wiring:
  `TXD←ESP32 TX, RXD→ESP32 RX, VIO=3.3V, VDD=5V, GND=common, S/STBY→GND, CANH/CANL→bus`.
  (Bench-only alternatives: SN65HVD230 module — 3.3 V-native, easy; MCP2551/TJA1050 —
  5 V-only, need an RXD level-shift.)
- **4× thermocouple front-end** — MAX31855 (K-type, SPI), one CS each, for the real build.
- **120 Ω termination** only if the ESP32 sits at a physical end of the bus.

Set `CAN_TX_PIN` / `CAN_RX_PIN` in the sketch to your transceiver's pins.

## Bus-collision safety

CAN bitwise arbitration makes frames with **different IDs** physically unable to
corrupt each other (lower ID wins, loser auto-retransmits). The only collision risk
is two transmitters using the **same** ID with different data:

- The ECU broadcasts on its own IDs, so `0x02400000` never clashes with it.
- **Do not run this alongside a real FuelTech EGT-4 module** (same ID would collide).
- Need a second EGT-4? Use a different model ID (B `0x02480000`, etc.) and configure
  the ECU for that model too.

## Build / flash

Arduino IDE with the ESP32 board package (the `driver/twai.h` API ships with it):
open `esp32_egt4.ino`, select your ESP32 board, flash. Serial monitor @ 115200
prints `TWAI up @ 1Mbit/s` on success.
