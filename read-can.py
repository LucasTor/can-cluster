import can
import struct

# Define FT450 simplified broadcast packet IDs
FT450_IDS = {
    0x14080600: "TPS/MAP/Air Temp/Engine Temp",
    0x14080601: "Oil/Fuel/Water Pressure + Gear",
    0x14080602: "Exhaust O2 / RPM / Oil Temp / Pit Limit",
    0x14080603: "Wheel Speeds FR/FL/RR/RL",
    0x14080604: "Traction Ctrl: Slip/Retard/Cut/Heading",
    0x14080605: "Shock Sensors FR/FL/RR/RL",
    0x14080606: "G-Forces: Accel/Lateral/Yaw",
    0x14080607: "Lambda Corr / Fuel Flow / Inj Times",
    0x14080608: "Oil Temp / Trans Temp / Fuel Consump / Brake Pressure",
}


# Parser functions for each packet type
def parse_0x14080600(data):
    return {
        "TPS_%": data[0] * 0.5,  # 0–100% (scale 0.5)
        "MAP_kPa": data[1] * 2,  # 0–500kPa
        "Air_Temp_C": data[2] * 0.1,
        "Engine_Temp_C": data[3] * 0.1,
    }


def parse_0x14080601(data):
    return {
        "Oil_Pressure_kPa": data[0] * 0.5,
        "Fuel_Pressure_kPa": data[1] * 0.5,
        "Water_Pressure_kPa": data[2] * 0.5,
        "Gear": data[3],
    }


def parse_0x14080602(data):
    rpm = struct.unpack(">H", data[1:3])[0]
    return {
        "Exhaust_O2_raw": data[
            0
        ],  # No unit defined — maybe AFR or lambda depending on config
        "RPM": rpm,
        "Oil_Temp_C": data[3] * 0.1,
        "Pit_Limit": bool(data[4]),
    }


def parse_0x14080603(data):
    return {
        "Wheel_Speed_FR": data[0],
        "Wheel_Speed_FL": data[1],
        "Wheel_Speed_RR": data[2],
        "Wheel_Speed_RL": data[3],
    }


def parse_0x14080604(data):
    return {
        "TC_Slip": data[0],
        "TC_Retard_deg": data[1] * 0.25,
        "TC_Cut_%": data[2] * 0.5,
        "Heading_deg": data[3] * 2,
    }


def parse_0x14080605(data):
    return {
        "Shock_FR": data[0],
        "Shock_FL": data[1],
        "Shock_RR": data[2],
        "Shock_RL": data[3],
    }


def parse_0x14080606(data):
    return {
        "Accel_G": (data[0] - 127) * 0.01,
        "Lateral_G": (data[1] - 127) * 0.01,
        "Yaw_Front": data[2],  # unit not specified
        "Yaw_Lateral": data[3],  # unit not specified
    }


def parse_0x14080607(data):
    return {
        "Lambda_Corr_%": data[0] * 0.5,
        "Fuel_Flow_cc": data[1],
        "Inj_Time_Bank_A_ms": data[2] * 0.1,
        "Inj_Time_Bank_B_ms": data[3] * 0.1,
    }


def parse_0x14080608(data):
    return {
        "Oil_Temp_C": data[0] * 0.1,
        "Trans_Temp_C": data[1] * 0.1,
        "Fuel_Consumption_L": data[2] * 0.1,
        "Brake_Pressure_kPa": data[3] * 0.5,
    }


# Map CAN ID to parser
PARSERS = {
    0x14080600: parse_0x14080600,
    0x14080601: parse_0x14080601,
    0x14080602: parse_0x14080602,
    0x14080603: parse_0x14080603,
    0x14080604: parse_0x14080604,
    0x14080605: parse_0x14080605,
    0x14080606: parse_0x14080606,
    0x14080607: parse_0x14080607,
    0x14080608: parse_0x14080608,
}

def main(interface='socketcan', channel='can0'):
    print("Starting FTCAN 2.0 listener for FT450...")
    bus = can.Bus(interface=interface, channel=channel)

    try:
        message = can.Message(arbitration_id=0x123, is_extended_id=False, data=[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
        try:
            bus.send(message, timeout=0.2)
            print(f"Message sent: {message}")
        except can.CanOperationError as e:
            print(f"Error sending message: {e}")
        while True:
            msg = bus.recv()
            print(msg)
            if msg.arbitration_id in PARSERS:
                parsed = PARSERS[msg.arbitration_id](msg.data)
                print(
                    f"[{hex(msg.arbitration_id)}] {FT450_IDS[msg.arbitration_id]}:\n  {parsed}\n"
                )

    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
