import time
from enum import Enum
from gpiozero import DigitalInputDevice

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
    pins = {}
    for pin in Pin:
        pins[pin.name] = DigitalInputDevice(pin.value, pull_up=True)

    if not data.get('io'):
        data['io'] = {}

    while True:
        for name, pin in pins.items():
            data['io'][name.lower()] = pin.value

        print(data['io'])

        time.sleep(0.1)
