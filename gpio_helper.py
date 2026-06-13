import time
from enum import Enum
import RPi.GPIO as GPIO

from model import SensorState

class Pin(Enum):
    C = 5
    LEFT_INDICATOR = 6
    HEADLIGHTS = 13
    SOMETHING = 19
    OTHER_THING = 26
    A = 16
    B = 20
    RIGHT_INDICATOR = 21

def read_io(state=None):
    if state is None:
        state = SensorState()
    GPIO.setmode(GPIO.BCM)
    try:
        for pin in Pin:
            GPIO.setup(pin.value, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        while True:
            readings = {pin.name.lower(): not GPIO.input(pin.value) for pin in Pin}
            state.io.update(readings)

            time.sleep(1 / 30)
    except Exception as e:
        print(e)
