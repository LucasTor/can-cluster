#!/usr/bin/env python3
import can
import sys
import time
from datetime import datetime

# ---------- Basic FuelTech ID → (name, unit, scale, signed_24bit) ----------
# Add/extend as you like. Unknown IDs will be printed with raw value.
FT_IDS = {
    0x0006: ("Brake Pressure", "bar", 0.001, False),
    0x0014: ("MAP",           "bar", 0.01,  False),
    0x007C: ("Engine Temp",   "°C",  0.1,   True),
    0x007E: ("Oil Temp",      "°C",  0.1,   True),
    0x0080: ("Coolant Press", "bar", 0.01,  False),  # example placeholder
    0x0084: ("RPM",           "rpm", 1.0,   False),
    0x00EA: ("Lambda 1",      "",    0.001, False),
    0x00EC: ("Lambda 2",      "",    0.001, False),
    0x00F8: ("Fuel Temp",     "°C",  0.1,   True),
    0x00FE: ("Oil Press",     "bar", 0.01,  False),
    0x0138: ("Battery Temp",  "°C",  0.1,   True),
    0x013A: ("IAT",           "°C",  0.1,   True),
    0x013C: ("Gear Calc",     "",    1.0,   False),
    0x013E: ("TPS",           "%",   0.1,   False),
    0x0140: ("Ign Advance",   "°",   0.1,   True),
    0x0142: ("Fuel PW",       "ms",  0.01,  False),
    0x0144: ("Battery Volt",  "V",   0.01,  False),
    0x0146: ("Wheel Speed",   "km/h",0.1,   False),
    0x0372: ("Traction %",    "%",   0.1,   True),
    0x0374: ("Slip %",        "%",   0.1,   True),
    0x0376: ("Boost Target",  "bar", 0.01,  False),
    0x0378: ("Boost Duty",    "%",   0.1,   False),
    0x037A: ("Launch RPM",    "rpm", 1.0,   False),
    0x037C: ("Cut Level",     "%",   0.1,   False),
    0x037E: ("Ign Trim",      "°",   0.1,   True),
}

# Utility: sign-extend a 24-bit little-endian value if needed
def decode_24bit_le(b0, b1, b2, signed=False):
    val = (b0 | (b1 << 8) | (b2 << 16))
    if signed:
        # 24-bit sign bit is bit 23
        if val & 0x800000:
            val = val - 0x1000000
    return val

def fmt_id_name(data_id):
    meta = FT_IDS.get(data_id)
    if not meta:
        return f"0x{data_id:04X}", "", 1.0, False
    name, unit, scale, signed = meta
    return name, unit, scale, signed

class SegmentedAssembler:
    """
    Assembles FTCAN 2.0 segmented payloads for a given arbitration ID.
    Segment format:
      seg[0]: [idx=0] [size_lo] [size_hi] [payload...]
      seg[>0]: [idx] [payload...]
    """
    def __init__(self):
        # key: arbitration_id -> state
        self.states = {}

    def reset(self, key):
        if key in self.states:
            del self.states[key]

    def push(self, arb_id, data):
        """
        Feed one 8-byte segment payload.
        Returns: bytes(payload) when complete, else None.
        """
        if not data:
            return None
        idx = data[0]
        state = self.states.get(arb_id)

        if idx == 0:
            if len(data) < 3:
                return None
            total = data[1] | (data[2] << 8)
            buf = bytearray()
            buf.extend(data[3:])
            self.states[arb_id] = {
                "expected_len": total,
                "next_idx": 1,
                "buf": buf,
                "last_ts": time.time(),
            }
            # completion check (can happen if tiny payload)
            st = self.states[arb_id]
            if len(st["buf"]) >= st["expected_len"]:
                payload = bytes(st["buf"][:st["expected_len"]])
                self.reset(arb_id)
                return payload
            return None
        else:
            # Ignore out-of-order starts
            if state is None:
                return None
            # Optionally enforce monotonic idx: if idx != state["next_idx"], you could drop.
            # We'll be tolerant and just append:
            state["buf"].extend(data[1:])
            state["next_idx"] = idx + 1
            state["last_ts"] = time.time()
            if len(state["buf"]) >= state["expected_len"]:
                payload = bytes(state["buf"][:state["expected_len"]])
                self.reset(arb_id)
                return payload
            return None

def parse_items(payload_bytes):
    """
    Parse 5-byte items: [DataID (LE16)] + [Value (LE24)].
    Returns list of dicts.
    """
    out = []
    i = 0
    n = len(payload_bytes)
    while i + 5 <= n:
        data_id = payload_bytes[i] | (payload_bytes[i+1] << 8)
        raw0, raw1, raw2 = payload_bytes[i+2], payload_bytes[i+3], payload_bytes[i+4]
        name, unit, scale, signed = fmt_id_name(data_id)
        raw_val = decode_24bit_le(raw0, raw1, raw2, signed=signed)
        scaled = raw_val * scale
        out.append({
            "data_id": data_id,
            "name": name,
            "raw": raw_val,
            "value": scaled,
            "unit": unit
        })
        i += 5
    # Note: leftover bytes (<5) are ignored (padding)
    return out

def main():
    # The two segmented arbitration IDs we care about
    IDS = {0x140812FF, 0x140813FF}

    try:
        bus = can.interface.Bus(bustype="socketcan", channel="can0")
    except Exception as e:
        print(f"Error opening can0: {e}", file=sys.stderr)
        sys.exit(1)

    # Filters: only extended IDs 0x140812FF and 0x140813FF
    try:
        bus.set_filters([
            {"can_id": 0x140812FF, "can_mask": 0x1FFFFFFF, "extended": True},
            {"can_id": 0x140813FF, "can_mask": 0x1FFFFFFF, "extended": True},
        ])
    except Exception:
        # Some backends ignore set_filters—safe to continue.
        pass

    assembler = SegmentedAssembler()

    print("Listening on can0 for 0x140812FF and 0x140813FF (segmented FTCAN 2.0)…")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            msg = bus.recv(timeout=1.0)
            if msg is None:
                continue
            if not msg.is_extended_id:
                continue
            arb_id = msg.arbitration_id
            if arb_id not in IDS:
                continue
            data = bytes(msg.data)

            # Feed segment assembler
            payload = assembler.push(arb_id, data)
            if payload is None:
                continue

            # Completed payload → decode items
            items = parse_items(payload)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"\n[{ts}] Completed {len(payload)} bytes from 0x{arb_id:08X} → {len(items)} item(s)")

            for it in items:
                name = it["name"]
                if name.startswith("0x"):  # unknown ID
                    print(f"  DataID {name}: raw={it['raw']}")
                else:
                    unit = it["unit"]
                    if unit:
                        print(f"  {name:<16} = {it['value']:.3f} {unit}  (raw {it['raw']})")
                    else:
                        print(f"  {name:<16} = {it['value']:.3f}      (raw {it['raw']})")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        try:
            bus.shutdown()
        except Exception:
            pass

if __name__ == "__main__":
    main()
