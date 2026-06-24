#!/usr/bin/env python3
"""Final validation for the FTCAN emulations (EGT-4 + Switchpad-8).

Run standalone on the Pi with the cluster service STOPPED, so it doesn't fight the
dash's own TX of the same frames:

    sudo systemctl stop can-cluster.service
    cd <repo> && poetry run python validate_ftcan.py all
    # ... then restart when done:  sudo systemctl start can-cluster.service

Subcommands:
    egt            Broadcast EGT-4 (model A) at a known pattern; you confirm the 4 EGT
                   channels in FTManager (no ECU echo to auto-check).
    switch [N]     Press Switchpad-8 button N (default 2) and AUTO-VERIFY the ECU
                   registered it: its Button Color reply (0x12200321) must differ
                   between our released and pressed frames.
    all            egt, then switch.

WARNING: switch presses trigger whatever button N is mapped to in FTManager
(e.g. arming 3-Step). Map it to something safe before validating on a running car.
"""

import sys
import time

import can

CHANNEL = "can0"

# EGT-4 simplified packet (Protocol_FTCAN20.pdf p25-26): 8 bytes, 4 channels at
# bytes 0-1/2-3/4-5/6-7, signed int16 big-endian, 0.125 C/bit. Frame ID = model;
# model A 0x02400000 is the one the FT600 binds.
EGT4_ID = 0x02400000
EGT_TEMP_SCALE = 8              # value = degC * 8 (0.125 C/bit)

# Switchpad-8 (p26): Button State FF FF <btn1-4> <btn5-8> 00 00 00 00. The ECU's
# Button Color reply (0x12200321) tracks button state, so we can auto-verify with it.
SWITCH_SW8_ID = 0x12200320      # Button State (panel -> ECU)
SW_COLOR_ID = 0x12200321        # ECU -> panel "Button Color" reply (tracks button state)
TX_PERIOD = 0.05                # 20 Hz


def _egt_payload(temps):
    """8-byte EGT-4 simplified packet: 4 x int16 big-endian signed, 0.125 C/bit."""
    data = bytearray(8)
    for i, t in enumerate(tuple(temps)[:4]):
        raw = int(round(t * EGT_TEMP_SCALE)) & 0xFFFF
        data[i * 2] = (raw >> 8) & 0xFF
        data[i * 2 + 1] = raw & 0xFF
    return bytes(data)


def _switch_payload(buttons):
    """8-byte SW-8 Button State frame from up to 8 bools (button 1..8)."""
    b = tuple(buttons) + (False,) * (8 - len(buttons))
    return bytes([0xFF, 0xFF,
                  sum(1 << i for i in range(4) if b[i]),       # buttons 1-4
                  sum(1 << i for i in range(4) if b[i + 4]),   # buttons 5-8
                  0x00, 0x00, 0x00, 0x00])


def validate_egt(bus, secs=8):
    temps = (100, 200, 300, 400)
    data = _egt_payload(temps)
    print(f"\n=== EGT-4 ===")
    print(f"[egt] broadcasting model A id=0x{EGT4_ID:08X}  data={data.hex(' ')}")
    print(f"[egt] CHECK FTManager: EGT channels 1-4 should read {temps} C")
    print(f"[egt] sending for {secs}s ...")
    msg = can.Message(arbitration_id=EGT4_ID, is_extended_id=True, data=data)
    t_end = time.monotonic() + secs
    while time.monotonic() < t_end:
        bus.send(msg)
        time.sleep(TX_PERIOD)
    print("[egt] done — confirm the readings in FTManager (manual check).")


def _exercise(bus, button, pressed, secs):
    """Hold button `pressed`/released for `secs`; return the most-common ECU color
    reply seen in that window (hex string), or None if the ECU sent nothing."""
    btns = [False] * 8
    if pressed:
        btns[button - 1] = True
    msg = can.Message(arbitration_id=SWITCH_SW8_ID, is_extended_id=True,
                      data=_switch_payload(btns))
    seen = {}
    last_send = 0.0
    t_end = time.monotonic() + secs
    while time.monotonic() < t_end:
        now = time.monotonic()
        if now - last_send >= TX_PERIOD:
            bus.send(msg)
            last_send = now
        r = bus.recv(timeout=0.02)
        if r is not None and r.is_extended_id and r.arbitration_id == SW_COLOR_ID:
            h = bytes(r.data).hex(' ')
            seen[h] = seen.get(h, 0) + 1
    return max(seen, key=seen.get) if seen else None


def validate_switch(bus, button=2, reps=3):
    print(f"\n=== Switchpad-8 button {button} ===")
    print(f"[sw] pressing id=0x{SWITCH_SW8_ID:08X}, auto-checking ECU reply "
          f"0x{SW_COLOR_ID:08X} changes between released/pressed")
    results = []
    for rep in range(reps):
        rel = _exercise(bus, button, pressed=False, secs=2.0)
        prs = _exercise(bus, button, pressed=True, secs=2.0)
        ok = rel is not None and prs is not None and rel != prs
        results.append(ok)
        print(f"[sw] rep {rep + 1}: released={rel}")
        print(f"[sw]         pressed ={prs}  -> {'PASS' if ok else 'FAIL'}")
    n_ok = sum(results)
    passed = n_ok >= (reps // 2 + 1)   # majority
    if passed:
        print(f"[sw] RESULT: PASS — ECU tracks button {button} ({n_ok}/{reps} reps)")
    elif n_ok == 0:
        print(f"[sw] RESULT: FAIL — ECU reply never changed (no color frames, or no "
              f"tracking). Is the service stopped and the panel configured?")
    else:
        print(f"[sw] RESULT: WEAK — only {n_ok}/{reps} reps showed a change")
    return passed


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    button = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    bus = can.Bus(interface="socketcan", channel=CHANNEL)
    try:
        if cmd in ("egt", "all"):
            validate_egt(bus)
        if cmd in ("switch", "sw", "all"):
            validate_switch(bus, button)
        if cmd not in ("egt", "switch", "sw", "all"):
            print(__doc__)
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
