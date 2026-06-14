#!/usr/bin/env python3
"""Decode a candump capture of the FuelTech FTCAN 2.0 bus.

Reassembles the segmented real-time broadcast and prints every DataID found
with its latest value. Handy for discovering which signals the ECU broadcasts
(fan output, 2-step, day/night, etc.) without a live capture.

Usage:  python decode_dump.py [dump.txt]
Input lines look like:  can0  140812FF   [8]  00 00 70 00 06 00 AC 00
"""
import re
import sys

# DataID -> name (partial; from the FTCAN 2.0 protocol measure table). Extend as
# signals are identified. MeasureID = (DataID << 1) | status_bit.
NAMES = {
    0x0001: "TPS", 0x0002: "MAP", 0x0003: "AirTemp", 0x0004: "EngineTemp",
    0x0005: "OilPress", 0x0006: "WaterPress", 0x0007: "LaunchMode/2step",
    0x0008: "Battery", 0x000A: "TractionSpeed", 0x000C: "WheelSpd_LF",
    0x000D: "WheelSpd_RF", 0x000E: "WheelSpd_LR", 0x000F: "WheelSpd_RR",
    0x0010: "DriveshaftRPM", 0x0011: "Gear", 0x0042: "RPM", 0x0048: "2StepSignal",
}

ECU_PREFIX = 0x1408  # top 16 bits of this ECU's frame IDs (0x1408xxFF)


def main(path):
    seg_buf = {}
    payloads = []
    for line in open(path):
        m = re.match(r"\s*\w+\s+([0-9A-Fa-f]+)\s+\[(\d+)\]\s+(.*)", line)
        if not m:
            continue
        cid = int(m.group(1), 16)
        data = [int(x, 16) for x in m.group(3).split()]
        if (cid >> 16) != ECU_PREFIX or not data:
            continue
        b0 = data[0]
        if b0 == 0xFF:                       # single packet
            payloads.append(bytes(data[1:]))
        elif b0 == 0x00:                     # segment 0: size (2B) then payload
            total = (data[1] << 8) | data[2]
            seg_buf[cid] = [total, bytearray(data[3:])]
        elif cid in seg_buf:                 # continuation segment
            seg_buf[cid][1] += bytes(data[1:])
            total, buf = seg_buf[cid]
            if len(buf) >= total:
                payloads.append(bytes(buf[:total]))
                del seg_buf[cid]

    seen = {}
    for p in payloads:
        for i in range(0, len(p) - 3, 4):
            mid = (p[i] << 8) | p[i + 1]
            val = (p[i + 2] << 8) | p[i + 3]
            if mid == 0:
                continue
            seen[mid >> 1] = (val, mid & 1)

    print(f"{len(payloads)} payloads reassembled, {len(seen)} unique DataIDs\n")
    for did in sorted(seen):
        val, status = seen[did]
        signed = val - 65536 if val >= 32768 else val
        kind = "STATUS" if status else "value"
        print(f"  DataID 0x{did:04X} {NAMES.get(did, ''):18s} {kind}={signed:6d} (0x{val:04X})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dump.txt")
