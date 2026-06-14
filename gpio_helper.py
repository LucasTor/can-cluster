import time
from enum import Enum
import RPi.GPIO as GPIO

from model import SensorState

class Pin(Enum):
    LEFT_INDICATOR = 6
    RIGHT_INDICATOR = 21
    HIGH_BEAM = 13
    PARKING_BRAKE = 16
    B = 20
    C = 5
    D = 19
    E = 26

def read_io(state=None):
    if state is None:
        state = SensorState()
    GPIO.setmode(GPIO.BCM)
    prev = {}
    try:
        for pin in Pin:
            GPIO.setup(pin.value, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        print("[gpio] watching: " + ", ".join(f"{p.name}=GPIO{p.value}" for p in Pin),
              flush=True)

        while True:
            readings = {}
            for pin in Pin:
                active = not GPIO.input(pin.value)
                readings[pin.name.lower()] = active
                # log only on change so toggling a switch reveals its pin
                if prev.get(pin.name) != active:
                    prev[pin.name] = active
                    print(f"[gpio] {pin.name} (GPIO{pin.value}) -> {'ON' if active else 'off'}",
                          flush=True)
            state.io.update(readings)

            time.sleep(1 / 30)
    except Exception as e:
        print("[gpio] error:", e, flush=True)
