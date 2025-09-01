import can

# List of FT450 Simplified Packet IDs
FT450_IDS = [
    0x14080600,
    0x14080601,
    0x14080602,
    0x14080603,
    0x14080604,
    0x14080605,
    0x14080606,
    0x14080607,
    0x14080608
]

# Build CAN filters: exact match using mask 0xFFFFFFFF
can_filters = [{"can_id": can_id, "can_mask": 0x1FFFFFFF} for can_id in FT450_IDS]

class FT450Listener(can.Listener):
    def on_message_received(self, msg):
        print(f"[{hex(msg.arbitration_id)}] Data: {msg.data.hex()}")

def main(interface='can0', bustype='socketcan'):
    bus = can.interface.Bus(channel=interface, bustype=bustype, can_filters=can_filters)

    listener = FT450Listener()
    notifier = can.Notifier(bus, [listener])

    print("Listening only for FT450 Simplified Packet IDs...")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        notifier.stop()
        print("Stopped.")

if __name__ == "__main__":
    main()
