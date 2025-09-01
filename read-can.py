import can
import struct

# FT450 simplified broadcast packet #2
FT450_ID_02 = 0x14080602

def parse_ft450_packet_02(msg):
    if msg.arbitration_id != FT450_ID_02 or len(msg.data) < 5:
        return None

    # According to manual:
    # Byte 0: Exhaust O2 (0–255) → lambda or AFR depending on config
    # Byte 1–2: RPM (2 bytes, Big Endian)
    # Byte 3: Oil Temp (°C * 0.1)
    # Byte 4: Pit Limit (0 = off, 1 = on)

    exhaust_o2 = msg.data[0]  # raw value
    rpm = struct.unpack('>H', msg.data[1:3])[0]
    oil_temp = msg.data[3] * 0.1  # °C
    pit_limit = msg.data[4]

    return {
        "exhaust_o2": exhaust_o2,
        "rpm": rpm,
        "oil_temp_c": oil_temp,
        "pit_limit": bool(pit_limit)
    }

def listen_for_ft450_packets(interface='can0'):
    bus = can.interface.Bus(channel=interface, bustype='socketcan')
    print("Listening for FT450 simplified broadcast packets...")
    try:
        while True:
            msg = bus.recv()
            if msg.arbitration_id == FT450_ID_02:
                parsed = parse_ft450_packet_02(msg)
                if parsed:
                    print(parsed)
    except KeyboardInterrupt:
        print("Stopped.")

# Start listening
listen_for_ft450_packets()
