import can
import struct

# Define FT450 simplified broadcast packet IDs
FT450_IDS = {
    0x14080600: "TPS/MAP/Air Temp/Engine Temp",
    0x14080601: "Oil/Fuel/Water Pressure + Gear",
    0x14080602: "Exhaust O2 / RPM / Oil Temp / Pit Limit",
    0x14080603: "Wheel Speeds FR/FL/RR/RL",
}


# Parser functions for each packet type
def parse_0x14080600(data):
    return {
        "tps": data[0] * 0.5,  # 0–100% (scale 0.5)
        "map": data[1] * 2,  # 0–500kPa
        "air_temp": data[2] * 0.1,
        "engine_temp": data[3] * 0.1,
    }


def parse_0x14080601(data):
    return {
        "oil_pressure": data[0] * 0.5,
        "fuel_pressure": data[1] * 0.5,
        "water_pressure": data[2] * 0.5,
        "gear": data[3],
    }


def parse_0x14080602(data):
    rpm = struct.unpack(">H", data[1:3])[0]
    print('RPM:', rpm)
    return {
        "lambda": data[
            0
        ],  # No unit defined — maybe AFR or lambda depending on config
        "rpm": rpm,
        "oil_temp": data[3] * 0.1,
        "pit_limit": bool(data[4]),
    }


def parse_0x14080603(data):
    return {
        "wheel_speed_fr": data[0],
        "wheel_speed_fl": data[1],
        "wheel_speed_rr": data[2],
        "wheel_speed_rl": data[3],
    }

# Map CAN ID to parser
PARSERS = {
    0x14080600: parse_0x14080600,
    0x14080601: parse_0x14080601,
    0x14080602: parse_0x14080602,
    0x14080603: parse_0x14080603,
}

data = {}

def main(interface='socketcan', channel='can0'):
    print("Starting FTCAN 2.0 listener for FT450...")
    bus = can.Bus(interface=interface, channel=channel)

    try:
        while True:
            msg = bus.recv()
            if msg.arbitration_id in PARSERS:
                parsed = PARSERS[msg.arbitration_id](msg.data)
                data.update(parsed)

            # print(data['rpm'])


    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
