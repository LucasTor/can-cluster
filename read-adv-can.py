#!/usr/bin/env python3
import can
from collections import defaultdict
from time import monotonic

# -------- Config --------
CHANNEL = "can0"
BITRATE = None  # leave None if your can0 is already up (e.g., with ip link set can0 up type can bitrate 500000)

# FuelTech FTCAN 2.0 constants (from manual)
# DataIDs we care about (MeasureID bit0==0 for value, bit0==1 would be "status")
DATAID_RPM = 0x0084
DATAID_WSPD_FL = 0x000C
DATAID_WSPD_FR = 0x000D
DATAID_WSPD_RL = 0x000E
DATAID_WSPD_RR = 0x000F

# Simplified broadcast IDs (FT600/550/450 column)
SIMPL_RPM_ID = 0x14080602  # bytes: [ExhO2_H,ExhO2_L, RPM_H, RPM_L, OilT_H, OilT_L, Pit_H, Pit_L]
SIMPL_WSPD_ID = 0x14080603 # [FR_H,FR_L, FL_H,FL_L, RR_H,RR_L, RL_H,RL_L]

# Your segmented stream IDs seen in the dump (match 0x14081?FF)
SEGMENTED_BASE_IDS = {0x140810FF, 0x140811FF, 0x140812FF, 0x140813FF}

# -------- State --------
last = {
    "rpm": None,
    "fl": None, "fr": None, "rl": None, "rr": None
}

# segmented assembly buffer per arbitration_id
seg_buf = defaultdict(bytearray)
seg_last_seq = {}

def maybe_print():
    # Print only when we actually have something new
    print(f"RPM={last['rpm'] or '-'}  WSPD[km/h] FL={last['fl'] or '-'} FR={last['fr'] or '-'} RL={last['rl'] or '-'} RR={last['rr'] or '-'}")

def parse_measure_stream(b: bytes):
    """Scan a byte stream of [ID_hi,ID_lo,VAL_hi,VAL_lo]* and update last[]"""
    # Walk in 4-byte chunks, but be robust to odd lengths
    n = len(b) // 4
    for i in range(n):
        off = i * 4
        mid = (b[off] << 8) | b[off+1]
        val = (b[off+2] << 8) | b[off+3]
        if mid & 0x1:  # status, not a value
            continue
        data_id = mid >> 1

        if data_id == DATAID_RPM:
            # RPM scale = 1 rpm per count (example shows 0x07D0 = 2000 rpm)
            last['rpm'] = val
        elif data_id == DATAID_WSPD_FL:
            last['fl'] = val   # km/h, scale 1
        elif data_id == DATAID_WSPD_FR:
            last['fr'] = val
        elif data_id == DATAID_WSPD_RL:
            last['rl'] = val
        elif data_id == DATAID_WSPD_RR:
            last['rr'] = val

def handle_segmented(msg: can.Message):
    """Assemble FTCAN segmented blocks and parse as data arrives.
       Layout: first data byte is the sequence index (0x00..0x10); bytes 1..7 are data."""
    if not msg.data:
        return
    seq = msg.data[0]
    payload = bytes(msg.data[1:])  # up to 7 bytes per frame

    buf = seg_buf[msg.arbitration_id]
    # Simple strategy: reset at seq==0 or if sequence jumps backwards
    if seq == 0 or (msg.arbitration_id in seg_last_seq and seq <= seg_last_seq[msg.arbitration_id]):
        buf.clear()
    seg_last_seq[msg.arbitration_id] = seq

    buf.extend(payload)

    # As soon as we have at least 4 bytes, try to parse newly added complete tuples
    # Parse only the multiple of 4 portion to avoid cutting a pair in half
    usable_len = (len(buf) // 4) * 4
    if usable_len:
        parse_measure_stream(buf[:usable_len])
        # Keep any remainder (0..3 bytes) in the buffer for next frame
        remainder = buf[usable_len:]
        buf.clear()
        buf.extend(remainder)
        maybe_print()

def handle_simplified(msg: can.Message):
    d = msg.data
    if msg.arbitration_id == SIMPL_RPM_ID and len(d) >= 4:
        last['rpm'] = (d[2] << 8) | d[3]
        maybe_print()
    elif msg.arbitration_id == SIMPL_WSPD_ID and len(d) == 8:
        last['fr'] = (d[0] << 8) | d[1]  # FR
        last['fl'] = (d[2] << 8) | d[3]  # FL
        last['rr'] = (d[4] << 8) | d[5]  # RR
        last['rl'] = (d[6] << 8) | d[7]  # RL
        maybe_print()

def main():
    bus = can.interface.Bus(bustype="socketcan", channel=CHANNEL, bitrate=BITRATE)
    # Hardware filtering helps latency/CPU
    filters = [
        # segmented pages you’re seeing
        *[{"can_id": i, "can_mask": 0x1FFFFFFF, "extended": True} for i in SEGMENTED_BASE_IDS],
        # simplified (fast) frames, if present
        {"can_id": SIMPL_RPM_ID, "can_mask": 0x1FFFFFFF, "extended": True},
        {"can_id": SIMPL_WSPD_ID, "can_mask": 0x1FFFFFFF, "extended": True},
    ]
    bus.set_filters(filters)

    print("Listening on can0 for FTCAN 2.0… (Ctrl+C to stop)")
    try:
        while True:
            msg = bus.recv(timeout=1.0)
            if msg is None:
                continue
            # Extended IDs are expected here
            if msg.arbitration_id in SEGMENTED_BASE_IDS:
                handle_segmented(msg)
            elif msg.arbitration_id in (SIMPL_RPM_ID, SIMPL_WSPD_ID):
                handle_simplified(msg)
            # else ignore
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
