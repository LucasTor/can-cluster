#!/usr/bin/env python3
"""FTCAN 2.0 tagged real-time broadcast reader.

FuelTech devices broadcast measurements on the "real-time reading broadcast"
messages (MessageID 0x_FF — i.e. the CAN frame's low byte is 0xFF). Each
measurement is a MeasureID(2 bytes) + Value(2 bytes) pair, big-endian, where
MeasureID = (DataID << 1) | status_bit. Frames come in three layouts:

  * Standard CAN (DataFieldID 0): the data field is just MeasureID/Value pairs.
  * FTCAN single packet (DataFieldID 2/3, first byte 0xFF): pairs after the 0xFF.
  * FTCAN segmented (first byte = segment index): segment 0 carries a 2-byte
    total length then the payload start; following segments append; reassembled
    into MeasureID/Value pairs.

We listen to every device on the bus (ECU + wideband, etc.) and map the DataIDs
we care about into SensorState. (See decode_dump.py to inventory a capture, and
log_realtime() below to discover still-unmapped signals like the fan output.)
"""

import can
import time

from model import SensorState

# Numeric measurements: DataID -> (SensorState field, multiplier).
# Validated against dump.txt and the FTCAN 2.0 measure table. 16-bit values are
# read as signed (two's complement) so temps / MAP can go negative.
MEASURE_MAP = {
    0x0001: ("tps", 0.1),
    0x0002: ("map", 0.001),                 # bar (signed: vacuum is negative)
    0x0003: ("air_temp", 0.1),
    0x0004: ("engine_temp", 0.1),
    0x0005: ("oil_pressure_bar", 0.001),
    0x0006: ("fuel_pressure_bar", 0.001),
    0x0007: ("water_pressure_bar", 0.001),
    0x0009: ("battery", 0.01),              # volts (12.06 V from the dump)
    0x000C: ("wheel_speed_fl_kmh", 1),
    0x000D: ("wheel_speed_fr_kmh", 1),
    0x000E: ("wheel_speed_rl_kmh", 1),
    0x000F: ("wheel_speed_rr_kmh", 1),
    0x0027: ("lambda_afr", 0.001),          # general Exhaust O2 (from the wideband)
    0x0042: ("rpm", 1),
    0x008C: ("oil_temp", 0.1),
}

# Status / special DataIDs handled below in _apply().
DATAID_GEAR = 0x0011        # signed gear (Note 2)
DATAID_LAUNCH = 0x0008      # ECU launch mode (2-step / 3-step / burnout): nonzero = armed
DATAID_DAYNIGHT = 0x007D    # day/night (tentative — verify live; 1 = night)

GEAR_LABEL = {-2: "P", -1: "R", 0: "N", 1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6"}


def _signed(v):
    return v - 65536 if v >= 32768 else v


def _pairs(payload, out):
    """Append (measure_id, raw_value) for each 4-byte pair in the payload."""
    for i in range(0, len(payload) - 3, 4):
        mid = (payload[i] << 8) | payload[i + 1]
        val = (payload[i + 2] << 8) | payload[i + 3]
        if mid:
            out.append((mid, val))


def _decode(cid, data, seg):
    """Decode one frame into a list of (measure_id, raw_value), reassembling
    segmented FTCAN packets via the per-id `seg` buffer."""
    out = []
    if not data:
        return out
    data_field_id = (cid >> 11) & 0x7
    if data_field_id == 0x00:                  # standard CAN
        _pairs(bytes(data), out)
    else:                                       # FTCAN (0x02 / 0x03 bridge)
        b0 = data[0]
        if b0 == 0xFF:                          # single packet
            _pairs(bytes(data[1:]), out)
        elif b0 == 0x00:                        # segment 0: total length + payload start
            total = (data[1] << 8) | data[2]
            seg[cid] = [total, bytearray(data[3:])]
        elif cid in seg:                        # continuation segment
            seg[cid][1] += bytes(data[1:])
            total, buf = seg[cid]
            if len(buf) >= total:
                _pairs(bytes(buf[:total]), out)
                del seg[cid]
    return out


def _apply(state, measures):
    """Map decoded measures into a SensorState update (stamps the CAN clock)."""
    updates = {}
    for mid, raw in measures:
        did = mid >> 1
        val = _signed(raw)
        if did in MEASURE_MAP:
            field, scale = MEASURE_MAP[did]
            updates[field] = val * scale
        elif did == DATAID_GEAR:
            updates["gear"] = val
            updates["gear_label"] = GEAR_LABEL.get(val, str(val))
        elif did == DATAID_LAUNCH:
            updates["two_step"] = (val != 0)
        elif did == DATAID_DAYNIGHT:
            updates["night"] = (val == 1)
    if updates:
        state.update(updates)


def read_can(interface="socketcan", channel="can0", state=None):
    if state is None:
        state = SensorState()
    print("Starting FTCAN 2.0 tagged-broadcast listener on", channel, flush=True)

    # Real-time broadcast frames have a low byte of 0xFF (any FuelTech device).
    filters = [{"can_id": 0x000000FF, "can_mask": 0x000000FF, "extended": True}]
    bus = can.Bus(interface=interface, channel=channel,
                  receive_own_messages=False, can_filters=filters)
    seg = {}
    try:
        while True:
            msg = bus.recv(timeout=1.0)
            if msg is None:
                continue
            if not msg.is_extended_id:
                continue
            _apply(state, _decode(msg.arbitration_id, msg.data, seg))
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        bus.shutdown()


# --- Discovery logger: dump unmapped real-time measures (find fan, day/night) ---
RT_NAMES = {did: f[0] for did, f in MEASURE_MAP.items()}
RT_NAMES.update({DATAID_GEAR: "gear", DATAID_LAUNCH: "launch/2step", DATAID_DAYNIGHT: "day/night?"})


def log_realtime(interface="socketcan", channel="can0"):
    """Log real-time broadcast measures on change (tag: [canrt]) for discovery."""
    filters = [{"can_id": 0x000000FF, "can_mask": 0x000000FF, "extended": True}]
    try:
        bus = can.Bus(interface=interface, channel=channel,
                      receive_own_messages=False, can_filters=filters)
    except Exception as e:
        print("[canrt] could not open bus:", e, flush=True)
        return
    print("[canrt] real-time broadcast logger on", channel, flush=True)
    seg, last = {}, {}
    try:
        while True:
            msg = bus.recv(timeout=1.0)
            if msg is None:
                continue
            for mid, raw in _decode(msg.arbitration_id, msg.data, seg):
                did = mid >> 1
                now = time.monotonic()
                prev = last.get(did)
                if prev and prev[0] == raw and now - prev[1] < 1.5:
                    continue
                last[did] = (raw, now)
                name = RT_NAMES.get(did, "")
                print(f"[canrt] DataID=0x{did:04X} {name} = {_signed(raw)} (0x{raw:04X})",
                      flush=True)
    except Exception as e:
        print("[canrt] error:", e, flush=True)
    finally:
        bus.shutdown()
