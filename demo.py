"""Drive simulation used when there's no CAN signal (bench / not-in-car).

A ~15s loop — idle -> 2-step -> on-boost pull -> cruise -> decel — ported from
the Painel Gol design's animation. Only engine / CAN-derived fields are produced;
GPIO inputs (turn signals, headlights) are left to the real hardware.
"""

import math

CYCLE = 15.0  # seconds per loop


def _lerp(a, b, k):
    k = max(0.0, min(1.0, k))
    return a + (b - a) * k


def _ease(k):
    if k <= 0:
        return 0.0
    if k >= 1:
        return 1.0
    return k * k * (3 - 2 * k)


def simulate(t):
    """Return simulated sensor values (dict of SensorState fields) at time t."""
    t = t % CYCLE
    speed, rpm, boost, lam = 0.0, 900.0, -0.5, 0.99
    coolant, intake, oil, fuel = 80.0, 36.0, 3.2, 64.0

    if t < 2:  # idle
        rpm = 900 + 40 * math.sin(t * 9)
        boost, lam, coolant, intake = -0.5, 0.99, 78, 36
    elif t < 4:  # 2-step armed
        rpm = 4750 + 220 * math.sin(t * 22)
        boost = _lerp(0.2, 0.7, _ease((t - 2) / 2))
        lam, coolant, intake = 0.90, 84, 42
    elif t < 10:  # on boost, through the gears
        p = (t - 4) / 6
        speed = _lerp(0, 188, _ease(p))
        lp = ((t - 4) % 2.0) / 2.0
        rpm = _lerp(3700, 6850, lp)
        boost = 1.22 + 0.16 * math.sin((t - 4) * 3.0)
        lam, oil = 0.82, 3.6
        coolant, intake = _lerp(88, 104, p), _lerp(44, 63, p)
    elif t < 13:  # cruise
        p = (t - 10) / 3
        speed = _lerp(188, 118, p)
        rpm = 3000 + 60 * math.sin(t * 4)
        boost, lam, intake = 0.06, 0.95, 56
        coolant = _lerp(104, 101, p)
    else:  # decel
        p = (t - 13) / 2
        speed = _lerp(118, 0, _ease(p))
        rpm = _lerp(2600, 900, _ease(p))
        boost, lam, intake = -0.4, 1.03, 48
        coolant = _lerp(101, 96, p)

    return {
        "rpm": rpm, "speed": speed, "map": boost, "lambda_afr": lam,
        "engine_temp": coolant, "air_temp": intake, "oil": oil, "fuel": fuel,
    }
