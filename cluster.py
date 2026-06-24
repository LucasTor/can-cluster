"""
Car Cluster Dashboard Application

Main application file for the car cluster display system.
"""

import os
import time
from kivy.config import Config

from theme import WINDOW_WIDTH, WINDOW_HEIGHT, BG

# Development mode flag
DEV = os.environ.get('DEV', 'true').lower() == 'true'

if DEV:
    os.environ['KIVY_METRICS_DENSITY'] = '1'
    os.environ['KIVY_DPI'] = '96'

Config.set('graphics', 'show_cursor', '0')  # must be before Window import
Config.set("graphics", "width", str(WINDOW_WIDTH))
Config.set("graphics", "height", str(WINDOW_HEIGHT))

import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase, DEFAULT_FONT

from widgets import CenterInfo, Gauge, TopAlerts, AlarmBar, NightDim
from model import SensorState
from demo import simulate

kivy.require("2.0.0")

# ============================================================================
# Configuration Constants
# ============================================================================

# Gauge configuration
SPEED_GAUGE_CONFIG = {
    'title': "SPEED",
    'subtitle': "KM/H",
    'max_value': 240,
    'unit': "km/h",
    'size': (600, 600),
    'pos': (60, 60),
    'ticks': 13,
    'angle_range': 270,
}

def _rpm_text(v):
    """Full number below 1000 rpm, compact 'x.xk' at/above 1000."""
    v = int(v)
    return str(v) if v < 1000 else f"{v / 1000:.1f}k"


RPM_GAUGE_CONFIG = {
    'title': "RPM",
    'subtitle': "X1000",
    'max_value': 8000,
    'unit': "rpm",
    'size': (600, 600),
    'pos': (1260, 60),
    'ticks': 9,
    'redline_from': 5500,
    'value_formatter': _rpm_text,
    'label_map': {
        1000: "1",
        2000: "2",
        3000: "3",
        4000: "4",
        5000: "5",
        6000: "6",
        7000: "7",
        8000: "8",
    },
}

# Shift light: flash the RPM gauge above this engine speed
SHIFT_RPM_THRESHOLD = 6000

# Critical alarm thresholds (the bottom red banner)
ALARM_LEAN_LAMBDA = 1.05       # lean mixture
ALARM_OVERHEAT_C = 110         # coolant overheat
ALARM_OIL_PRESS_BAR = 1.0      # minimum oil pressure...
ALARM_OIL_PRESS_RPM = 1500     # ...only checked above this rpm (idle runs lower)

# After this many seconds with no CAN frame, run the animated demo loop so the
# cluster shows live values on a bench / when not connected to the car.
NO_CAN_DEMO_DELAY = 3.0

# Start rendering live data once the gauges' startup sweep has finished.
RENDER_START_DELAY = 5.0

# ============================================================================
# Application Setup
# ============================================================================


Window.show_fps = False
Window.clearcolor = BG  # near-black background for the minimal look

# Register custom font
LabelBase.register(DEFAULT_FONT, "fonts/Compagnon-Medium.otf")


# ============================================================================
# Dashboard Widget
# ============================================================================

class Dashboard(Widget):
    """Main dashboard widget containing all gauge and info displays."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._setup_gauges()
        self._setup_center_info()
        self._setup_top_alerts()
        self._setup_night_dim()
        self._setup_alarms()

        if DEV:
            Window.size = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)

    def _setup_gauges(self):
        """Initialize speed and RPM gauges."""
        self.speed_gauge = Gauge(**SPEED_GAUGE_CONFIG)
        self.add_widget(self.speed_gauge)

        self.rpm_gauge = Gauge(**RPM_GAUGE_CONFIG)
        self.add_widget(self.rpm_gauge)

    def _setup_center_info(self):
        """Initialize center information display."""
        self.center_info = CenterInfo()
        self.add_widget(self.center_info)

    def _setup_top_alerts(self):
        """Initialize the top tell-tale alert row (turn signals, warnings, etc.)."""
        self.top_alerts = TopAlerts()
        self.add_widget(self.top_alerts)

    def _setup_night_dim(self):
        """Night dimming veil (below the alarm banner so alarms stay bright)."""
        self.night_dim = NightDim()
        self.add_widget(self.night_dim)

    def _setup_alarms(self):
        """Critical alarm banner (bottom). Added last so it sits on top."""
        self.alarm_bar = AlarmBar()
        self.add_widget(self.alarm_bar)

    def update(self, state):
        """
        Update all dashboard displays from the shared sensor state.

        Args:
            state: A ``SensorState`` instance, continuously updated by the CAN
                and GPIO reader threads (see model.py for the full schema).
        """
        self.rpm_gauge.update_value(state.rpm)
        self.speed_gauge.update_value(state.wheel_speed_fl_kmh)

        self.rpm_gauge.set_shift(state.rpm >= SHIFT_RPM_THRESHOLD)

        self.center_info.set_values(
            intake_c=state.air_temp,
            water_c=state.engine_temp,
            oil_press_bar=state.oil_pressure_bar,
            lambda_val=state.lambda_afr,
            boost_bar=max(0.0, state.map),  # boost only; vacuum clamps to 0.00
            fuel_level=state.fuel_level,
            fuel_press_bar=state.fuel_pressure_bar,
            gear=state.gear_label,
            rpm=state.rpm,
        )

        self.top_alerts.set_state(state)
        self.night_dim.set_night(state.night)
        self.alarm_bar.set_alarms(self._alarms(state))

    @staticmethod
    def _alarms(state):
        """Active critical alarms for the bottom banner."""
        alarms = []
        # engine not running (off / cranking) — these readings aren't meaningful
        # (lambda pegs lean on ambient O2, etc.), so keep the banner clear.
        if state.rpm < 500:
            return alarms
        if state.lambda_afr > ALARM_LEAN_LAMBDA:
            alarms.append("LEAN")
        if state.engine_temp > ALARM_OVERHEAT_C:
            alarms.append("OVERHEAT")
        # low oil pressure, but only above idle (idle naturally runs lower)
        if state.rpm > ALARM_OIL_PRESS_RPM and state.oil_pressure_bar < ALARM_OIL_PRESS_BAR:
            alarms.append("OIL PRESSURE")
        return alarms


# ============================================================================
# Application Entry Point
# ============================================================================

class CarClusterApp(App):
    """Main Kivy application for the car cluster dashboard."""

    def __init__(self, state=None):
        super().__init__()
        self.state = state or SensorState()
        self.dashboard = None
        self._demo_t0 = None  # monotonic time the demo loop engaged

    def build(self):
        """Build and return the main dashboard widget."""
        self.dashboard = Dashboard()
        return self.dashboard

    def on_start(self):
        """Start the render loop once the gauges have finished their intro sweep."""
        Clock.schedule_once(
            lambda _: Clock.schedule_interval(self.update_values, 1 / 30), RENDER_START_DELAY
        )

    def update_values(self, _):
        """Render the current state, falling back to the demo loop with no CAN."""
        if not self.dashboard:
            return
        if self.state.since_can() > NO_CAN_DEMO_DELAY:
            self._run_demo()
        else:
            self._demo_t0 = None
        self.dashboard.update(self.state)

    def _run_demo(self):
        """Feed the animated simulation into the state when no CAN is present.

        Writes only engine/CAN-derived fields (not GPIO inputs) directly into the
        state — bypassing ``update()`` so it doesn't reset the CAN-activity clock.
        Real CAN frames take over automatically the moment they arrive.
        """
        if self._demo_t0 is None:
            self._demo_t0 = time.monotonic()
        vals = simulate(time.monotonic() - self._demo_t0)
        s = self.state
        s.rpm = vals["rpm"]
        s.wheel_speed_fl_kmh = vals["speed"]
        s.map = vals["map"]
        s.lambda_afr = vals["lambda_afr"]
        s.engine_temp = vals["engine_temp"]
        s.air_temp = vals["air_temp"]
        s.oil_pressure_bar = vals["oil"]
        s.fuel_level = vals["fuel"]


def run_cluster(state):
    """
    Run the cluster application against the provided sensor state.

    Args:
        state: A ``SensorState`` instance to display (and read live updates from).
    """
    try:
        app = CarClusterApp(state)
        app.run()
    except Exception as e:
        print(f"Error running cluster: {e}")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print(f"Window size: {Window.size}")
    
    # Sample data for testing
    state = SensorState(
        wheel_speed_fl_kmh=63,
        lambda_afr=0.826,
        map=0.345,
        engine_temp=67,
        air_temp=102,
        rpm=1420,
        oil_pressure_bar=2.7,
        fuel_level=68,
    )

    run_cluster(state)
