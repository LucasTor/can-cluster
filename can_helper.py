#!/usr/bin/env python3
import can
import time
import struct
from collections import deque

from model import SensorState

# --------- Simplified broadcast (FT450/550/600): 0x14080600..0x14080603 ----------
# Each frame packs 4 signed 16-bit values (big-endian) = 8 bytes total.
# Units/scalers per FT CAN 2.0 manual.

# Message IDs (extended)
MSG_TPS_MAP_TEMPS   = 0x14080600  # TPS / MAP / AirTemp / EngineTemp
MSG_PRESSURES_GEAR  = 0x14080601  # OilPress / FuelPress / WaterPress / Gear
MSG_O2_RPM_OILT_PIT = 0x14080602  # Exhaust O2 (lambda) / RPM / Oil Temp / Pit Limit
MSG_WHEEL_SPEEDS    = 0x14080603  # Wheel Speeds FR / FL / RR / RL

# Optional: map numeric gear to a friendlier label (Note 2 in manual)
GEAR_LABEL = {
    -2: "P",
    -1: "R",
     0: "N",
     1: "1",
     2: "2",
     3: "3",
     4: "4",
     5: "5"
}

def parse_0x14080600(data: bytes):
    tps, map, air_temp, engine_temp = struct.unpack(">4h", data[:8])
    return {
        "tps":                tps * 0.1, 
        "map":                map * 0.001,
        "air_temp":           air_temp * 0.1, 
        "engine_temp":        engine_temp * 0.1, 
    }

def parse_0x14080601(data: bytes):
    oil_pressure, fuel_pressure, water_pressure, gear = struct.unpack(">4h", data[:8])
    return {
        "oil_pressure_bar":   oil_pressure * 0.001,
        "fuel_pressure_bar":  fuel_pressure * 0.001,
        "water_pressure_bar": water_pressure * 0.001,
        "gear":               gear,
        "gear_label":         GEAR_LABEL.get(gear, str(gear)),
    }

def parse_0x14080602(data: bytes):
    o2, rpm, oil_tmep, pit = struct.unpack(">4h", data[:8])
    return {
        "lambda":             o2 * 0.001,
        "rpm":                int(rpm),
        "oil_temp":         oil_tmep * 0.1,
        "pit_limit":          (pit != 0),
    }

def parse_0x14080603(data: bytes):
    fr, fl, rr, rl = struct.unpack(">4h", data[:8])
    return {
        "wheel_speed_fr_kmh": int(fr),
        "wheel_speed_fl_kmh": int(fl),
        "wheel_speed_rr_kmh": int(rr),
        "wheel_speed_rl_kmh": int(rl),
    }

PARSERS = {
    MSG_TPS_MAP_TEMPS:   parse_0x14080600,
    MSG_PRESSURES_GEAR:  parse_0x14080601,
    MSG_O2_RPM_OILT_PIT: parse_0x14080602,
    MSG_WHEEL_SPEEDS:    parse_0x14080603,
}

def read_can(interface="socketcan", channel="can0", print_fast=False, state=None):
    if state is None:
        state = SensorState()
    print("Starting FTCAN 2.0 simplified listener on", channel)

    # Filters: only the simplified frames we care about (extended IDs)
    filters = [{"can_id": mid, "can_mask": 0x1FFFFFFF, "extended": True} for mid in PARSERS]
    bus = can.Bus(interface=interface, channel=channel, receive_own_messages=False, can_filters=filters)

    # Optional rolling buffers if you want "fast" prints without flooding
    last_lines = deque(maxlen=1)

    try:
        while True:
            msg = bus.recv(timeout=1.0)
            if msg is None:
                continue
            if not msg.is_extended_id:
                continue
            parser = PARSERS.get(msg.arbitration_id)
            if not parser:
                continue

            parsed = parser(msg.data)
            state.update(parsed)

            if print_fast:
                # Minimal “fast path” print for RPM and a vehicle speed estimation.
                # Vehicle speed = average of the 4 wheel speeds.
                rpm = state.rpm
                wheels = [state.wheel_speed_fr_kmh,
                          state.wheel_speed_fl_kmh,
                          state.wheel_speed_rr_kmh,
                          state.wheel_speed_rl_kmh]
                veh_kmh = round(sum(wheels) / len(wheels), 1)

                line = f"RPM={rpm}  Speed≈{veh_kmh} km/h"
                if not last_lines or last_lines[-1] != line:
                    print(line)
                    last_lines.append(line)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        bus.shutdown()

# --- Real-time tagged broadcast logger (discovery: fan, 2-step, ECU outputs) -----
# The full FTCAN real-time broadcast (MessageID 0x_FF, i.e. frame low byte 0xFF)
# tags every measure with a MeasureID = (DataID << 1) | status_bit. We don't
# consume it yet — this just logs frames (raw + a best-effort single-packet decode)
# so signals like the fan output and 2-step can be identified on the bench.
RT_NAMES = {
    0x0001: "TPS", 0x0002: "MAP", 0x0003: "AirTemp", 0x0004: "EngineTemp",
    0x0005: "OilPress", 0x0006: "WaterPress", 0x0007: "LaunchMode/2step",
    0x0008: "Battery", 0x0011: "Gear", 0x0042: "RPM", 0x0048: "2StepSignal",
}


def log_realtime(interface="socketcan", channel="can0"):
    """Log the FTCAN real-time tagged broadcast for signal discovery (tag: [canrt]).

    Opens its own socket (socketcan multiplexes, so it runs alongside read_can),
    and logs each frame's raw bytes when they change (rate-limited per ID), plus a
    decode of single-packet measures (DataID = value). Segmented frames are logged
    raw so they can be reassembled offline.
    """
    filters = [{"can_id": 0xFF, "can_mask": 0xFF, "extended": True}]
    try:
        bus = can.Bus(interface=interface, channel=channel,
                      receive_own_messages=False, can_filters=filters)
    except Exception as e:
        print("[canrt] could not open bus:", e, flush=True)
        return
    print("[canrt] real-time broadcast logger on", channel, flush=True)
    last = {}  # arbitration_id -> (raw bytes, monotonic time)
    try:
        while True:
            msg = bus.recv(timeout=1.0)
            if msg is None:
                continue
            raw = bytes(msg.data)
            now = time.monotonic()
            prev = last.get(msg.arbitration_id)
            if prev and prev[0] == raw and now - prev[1] < 1.5:
                continue  # unchanged and logged recently -> skip
            last[msg.arbitration_id] = (raw, now)
            hexd = " ".join(f"{b:02X}" for b in raw)
            decoded = ""
            if raw[:1] == b"\xff":  # single packet: 0xFF + MeasureID(2)+Value(2)...
                for i in range(1, len(raw) - 3, 4):
                    mid = (raw[i] << 8) | raw[i + 1]
                    val = (raw[i + 2] << 8) | raw[i + 3]
                    if mid == 0:
                        continue
                    did = mid >> 1
                    name = RT_NAMES.get(did, "")
                    tag = "status" if (mid & 1) else "value"
                    decoded += f" | 0x{did:04X}{('(' + name + ')') if name else ''} {tag}={val}"
            print(f"[canrt] id=0x{msg.arbitration_id:08X} [{len(raw)}] {hexd}{decoded}", flush=True)
    except Exception as e:
        print("[canrt] error:", e, flush=True)
    finally:
        bus.shutdown()


from concurrent.futures import ThreadPoolExecutor
if __name__ == "__main__":
    state = SensorState()

    def print_can(recv):
        while True:
            print('RPM:', recv.rpm)
            time.sleep(0.1)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="ftcan") as ex:
        fut_reader   = ex.submit(read_can, state=state)
        fut_consumer = ex.submit(print_can, recv=state)

