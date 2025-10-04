import time
from enum import Enum
import RPi.GPIO as GPIO

class Pin(Enum):
    C = 5
    LEFT_INDICTOR = 6
    HEADLIGHTS = 13
    SOMETHING = 19
    OTHER_THING = 26
    A = 16
    B = 20
    RIGHT_INDICATOR = 21

def read_io(data = {}):
    GPIO.setmode(GPIO.BCM)
    try:
        for pin in Pin:
            GPIO.setup(pin.value, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        if not data.get('io'):
            data['io'] = {}

        while True:
            for pin in Pin:
                data['io'][pin.name.lower()] = not GPIO.input(pin.value)

            print(data['io'])

            time.sleep(1 / 30)
    except Exception as e:
        print(e)
