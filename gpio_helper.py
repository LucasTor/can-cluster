import time
from enum import Enum
import RPi.GPIO as GPIO

class Pin(Enum):
    RIGHT_INDICATOR = 5
    LEFT_INDICTOR = 6
    HEADLIGHTS = 13
    SOMETHING = 19
    OTHER_THING = 26
    A = 16
    B = 20
    C = 21

def read_io(data = {}):
    print('READING IO')
    GPIO.setmode(GPIO.BCM)
    try:
        for pin in Pin:
            GPIO.setup(pin.value, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        if not data.get('io'):
            data['io'] = {}

        while True:
            for pin in Pin:
                data['io'][pin.name.lower()] = GPIO.input(pin.value)

            print(data['io'])

            time.sleep(0.1)
    except Exception as e:
        print(e)