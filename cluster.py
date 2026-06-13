"""
Car Cluster Dashboard Application

Main application file for the car cluster display system.
"""

import os
from kivy.config import Config

from theme import WINDOW_WIDTH, WINDOW_HEIGHT

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

from widgets import CenterInfo, Gauge, TurnIndicator, ShiftCenterBanner
from model import SensorState

kivy.require("2.0.0")

# ============================================================================
# Configuration Constants
# ============================================================================

# Shift banner dimensions
SHIFT_BANNER_WIDTH = 450
SHIFT_BANNER_HEIGHT = 600

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

RPM_GAUGE_CONFIG = {
    'title': "RPM",
    'subtitle': "X1000",
    'max_value': 8000,
    'unit': "rpm",
    'size': (600, 600),
    'pos': (1260, 60),
    'ticks': 9,
    'redline_from': 5500,
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

# Turn indicator positions
LEFT_INDICATOR_POS = (635, 560)
RIGHT_INDICATOR_POS = (1185, 560)
INDICATOR_SIZE = (100, 100)

# Shift banner configuration
SHIFT_RPM_THRESHOLD = 6000
SHIFT_BLINK_HZ = 5

# Keyboard controls
KEY_UP_ARROW = 273

# Keyboard demo (dev mode): synthetic rev/speed while the up arrow is held
DEMO_ACCEL_RPM_PER_S = 3000
DEMO_COAST_RPM_PER_S = 2000
DEMO_ACCEL_KMH_PER_S = 60
DEMO_COAST_KMH_PER_S = 30
DEMO_IDLE_RPM = 1000
DEMO_MAX_RPM = 8000
DEMO_MAX_KMH = 240

# ============================================================================
# Application Setup
# ============================================================================


Window.show_fps = True

# Register custom font
LabelBase.register(DEFAULT_FONT, "fonts/Compagnon-Medium.otf")


# ============================================================================
# Dashboard Widget
# ============================================================================

class Dashboard(Widget):
    """Main dashboard widget containing all gauge and info displays."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.accelerating = False
        self.hazard_on = False

        self._setup_gauges()
        self._setup_center_info()
        self._setup_turn_indicators()
        self._setup_shift_banner()

        if DEV:
            Window.size = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)

        Clock.schedule_once(lambda x: self._setup_keyboard_triggers(), 3)

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

    def _setup_turn_indicators(self):
        """Initialize left and right turn indicators."""
        self.left_indicator = TurnIndicator(
            side='left',
            size=INDICATOR_SIZE,
            pos=LEFT_INDICATOR_POS
        )
        self.right_indicator = TurnIndicator(
            side='right',
            size=INDICATOR_SIZE,
            pos=RIGHT_INDICATOR_POS
        )
        self.add_widget(self.left_indicator)
        self.add_widget(self.right_indicator)

    def _setup_shift_banner(self):
        """Initialize shift indicator banner."""
        self.shift_overlay = ShiftCenterBanner(
            shift_rpm=SHIFT_RPM_THRESHOLD,
            blink_hz=SHIFT_BLINK_HZ
        )
        self.add_widget(self.shift_overlay)

    def _setup_keyboard_triggers(self):
        """Set up keyboard event handlers."""
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)

    def update(self, state):
        """
        Update all dashboard displays from the shared sensor state.

        Args:
            state: A ``SensorState`` instance, continuously updated by the CAN
                and GPIO reader threads (see model.py for the full schema).
        """
        self.rpm_gauge.update_value(state.rpm)
        self.speed_gauge.update_value(state.wheel_speed_fl_kmh)

        self.shift_overlay.set_rpm(state.rpm)

        self.center_info.set_values(
            intake_c=state.air_temp,
            water_c=state.engine_temp,
            oil_press_bar=state.oil_pressure_bar,
            lambda_val=state.lambda_afr,
            boost_bar=max(state.map, 0),
            fuel_level=state.fuel_level,
        )

        self.right_indicator.set_active(state.io.right_indicator)
        self.left_indicator.set_active(state.io.left_indicator)

    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        """Handle key press events."""
        print(key)
        if key == KEY_UP_ARROW:
            self.accelerating = True

    def on_key_up(self, window, key, scancode):
        """Handle key release events."""
        if key == KEY_UP_ARROW:
            self.accelerating = False


# ============================================================================
# Application Entry Point
# ============================================================================

class CarClusterApp(App):
    """Main Kivy application for the car cluster dashboard."""

    def __init__(self, state=None):
        super().__init__()
        self.state = state or SensorState()
        self.dashboard = None

    def build(self):
        """Build and return the main dashboard widget."""
        self.dashboard = Dashboard()
        return self.dashboard

    def on_start(self):
        """Start the render loop (plus the keyboard demo source in dev mode)."""
        def start_update(_):
            Clock.schedule_interval(self.update_values, 1 / 30)
            if DEV:
                # No CAN bus on a desktop — let the up-arrow key feed synthetic
                # data into the same state the render loop reads.
                Clock.schedule_interval(self._demo_step, 1 / 60)
        Clock.schedule_once(start_update, 3)

    def update_values(self, _):
        """Update dashboard with current data."""
        if self.dashboard:
            self.dashboard.update(self.state)

    def _demo_step(self, dt):
        """Advance synthetic RPM/speed from the up-arrow accelerator (dev only).

        Acts as a stand-in CAN source: it mutates the same ``SensorState`` the
        render loop reads, so holding the up arrow revs the engine and the whole
        cluster (gauges, shift banner) responds exactly as it would to real data.
        """
        if self.dashboard and self.dashboard.accelerating:
            self.state.rpm = min(self.state.rpm + DEMO_ACCEL_RPM_PER_S * dt, DEMO_MAX_RPM)
            self.state.wheel_speed_fl_kmh = min(
                self.state.wheel_speed_fl_kmh + DEMO_ACCEL_KMH_PER_S * dt, DEMO_MAX_KMH
            )
        else:
            self.state.rpm = max(self.state.rpm - DEMO_COAST_RPM_PER_S * dt, DEMO_IDLE_RPM)
            self.state.wheel_speed_fl_kmh = max(
                self.state.wheel_speed_fl_kmh - DEMO_COAST_KMH_PER_S * dt, 0
            )


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
