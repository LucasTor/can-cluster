#!/usr/bin/env python3
import can
import struct
from collections import deque

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

def read_can(interface="socketcan", channel="can0", print_fast=False, data = {}):
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
            data.update(parsed)

            if print_fast:
                # Minimal “fast path” print for RPM and a vehicle speed estimation.
                # Vehicle speed = average of the 4 wheel speeds when present.
                rpm = data.get("rpm")
                wheels = [data.get("wheel_speed_fr_kmh"),
                          data.get("wheel_speed_fl_kmh"),
                          data.get("wheel_speed_rr_kmh"),
                          data.get("wheel_speed_rl_kmh")]
                spds = [v for v in wheels if isinstance(v, int)]
                veh_kmh = round(sum(spds) / len(spds), 1) if spds else None

                line = f"RPM={rpm if rpm is not None else '-'}"
                if veh_kmh is not None:
                    line += f"  Speed≈{veh_kmh} km/h"
                if not last_lines or last_lines[-1] != line:
                    print(line)
                    last_lines.append(line)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        bus.shutdown()

from concurrent.futures import ThreadPoolExecutor
if __name__ == "__main__":
    data = {}

    def print_can(recv):
        print('RPM:', recv.get('rpm', 0))

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="ftcan") as ex:
        fut_reader   = ex.submit(read_can, data=data)
        fut_consumer = ex.submit(print_can, recv=data)

