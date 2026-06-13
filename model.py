"""Typed, thread-safe sensor state shared between the reader threads and the UI.

The CAN and GPIO reader threads write into a single ``SensorState`` instance;
the Kivy dashboard reads from it ~30x/s. Centralising the schema here (instead
of a bare dict of magic string keys) makes the producer/consumer contract
explicit and turns key typos into attribute errors instead of silent misses.
"""

from dataclasses import dataclass, field, fields
from threading import Lock


@dataclass
class IoState:
    """Digital inputs read from the Raspberry Pi GPIO header."""

    left_indicator: bool = False
    right_indicator: bool = False
    headlights: bool = False

    def update(self, values):
        """Merge a ``{pin_name: bool}`` mapping; unknown pins are ignored."""
        for key, value in values.items():
            if key in _IO_FIELDS:
                setattr(self, key, value)


@dataclass
class SensorState:
    # engine
    rpm: float = 0.0
    map: float = 0.0              # manifold pressure / boost (bar)
    tps: float = 0.0             # throttle position (%)
    air_temp: float = 0.0        # intake air temperature (°C)
    engine_temp: float = 0.0     # coolant temperature (°C)
    oil_temp: float = 0.0        # oil temperature (°C)
    oil_pressure_bar: float = 0.0
    fuel_pressure_bar: float = 0.0
    water_pressure_bar: float = 0.0
    lambda_afr: float = 1.0      # exhaust O2 / lambda
    gear: int = 0
    gear_label: str = "N"
    pit_limit: bool = False
    fuel_level: float = 0.0      # %
    # wheel speeds (km/h)
    wheel_speed_fr_kmh: float = 0.0
    wheel_speed_fl_kmh: float = 0.0
    wheel_speed_rr_kmh: float = 0.0
    wheel_speed_rl_kmh: float = 0.0
    # digital io
    io: IoState = field(default_factory=IoState)

    def __post_init__(self):
        self._lock = Lock()

    def update(self, values):
        """Merge a partial mapping (e.g. a decoded CAN frame) into the state.

        Unknown keys are ignored. The CAN parser's ``lambda`` key is mapped to
        ``lambda_afr`` since ``lambda`` is a reserved word. The whole merge is
        applied under a lock so the dashboard never reads a half-updated frame.
        """
        with self._lock:
            for key, value in values.items():
                attr = _KEY_ALIASES.get(key, key)
                if attr in _SCALAR_FIELDS:
                    setattr(self, attr, value)


_KEY_ALIASES = {"lambda": "lambda_afr"}
_IO_FIELDS = {f.name for f in fields(IoState)}
_SCALAR_FIELDS = {f.name for f in fields(SensorState)} - {"io"}
