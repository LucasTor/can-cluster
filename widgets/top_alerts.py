"""Top-of-cluster tell-tale row (the "alerts").

A horizontal row of indicator "pills" centred at the top of the cluster. Each
pill is a calm faint outline until its signal fires, then it lights up in its
ISO colour — matching the minimal Painel Gol design where the tell-tales stay
invisible until they have something to say. Turn signals, the 2-step and the
over-boost warning blink while active.
"""

import os

from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Line, RoundedRectangle, Triangle
from kivy.core.window import Window
from kivy.clock import Clock

from theme import (
    FONT_MONO, WINDOW_HEIGHT,
    TT_GREEN, TT_BLUE, TT_RED, TT_AMBER, TT_CYAN, TT_BOOST,
    PILL_OFF_BORDER, PILL_OFF_TEXT,
)

PILL_HEIGHT = 36
PILL_RADIUS = 7
PILL_GAP = 8
CHAR_W = 11          # approx glyph advance at the label font size
PILL_PAD = 14        # horizontal padding inside a pill
ARROW_WIDTH = 52
ROW_TOP_MARGIN = 24  # gap between the window top and the pill row
BLINK_PERIOD = 0.4   # seconds per blink toggle
WIFI_MARGIN_X = 40   # left inset of the standalone WiFi tell-tale
WIFI_POLL = 3.0      # seconds between WiFi status checks


def _wifi_connected():
    """True if any wireless interface is associated/up (read straight from sysfs)."""
    base = "/sys/class/net"
    try:
        for iface in os.listdir(base):
            d = os.path.join(base, iface)
            if os.path.isdir(os.path.join(d, "wireless")) or os.path.exists(os.path.join(d, "phy80211")):
                try:
                    with open(os.path.join(d, "operstate")) as f:
                        if f.read().strip() == "up":
                            return True
                except OSError:
                    continue
    except OSError:
        pass
    return False


class TellTale(Widget):
    """A single indicator pill: rounded outline + label or arrow."""

    def __init__(self, key, color, label=None, arrow=None, blinks=False, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self.on_color = color
        self.blinks = blinks
        self._arrow = arrow

        self.size_hint = (None, None)
        self.size = (ARROW_WIDTH if arrow else max(48, len(label or "") * CHAR_W + 2 * PILL_PAD),
                     PILL_HEIGHT)

        with self.canvas:
            self._fill_col = Color(0, 0, 0, 0)          # subtle lit background
            self._fill = RoundedRectangle(radius=[PILL_RADIUS])
            self._border_col = Color(*PILL_OFF_BORDER)
            self._border = Line(width=1.2)
            self._mark_col = Color(*PILL_OFF_TEXT)       # arrow glyph colour
            self._tri = Triangle(points=[0, 0, 0, 0, 0, 0])

        if arrow:
            self._label = None
        else:
            self._mark_col.a = 0                          # no triangle on text pills
            self._label = Label(
                text=label, font_name=FONT_MONO, font_size="16sp",
                color=PILL_OFF_TEXT, halign="center", valign="middle",
            )
            self.add_widget(self._label)

        self.bind(pos=self._layout, size=self._layout)
        self.set_lit(False)

    def _layout(self, *_):
        x, y = self.pos
        w, h = self.size
        self._fill.pos = self.pos
        self._fill.size = self.size
        self._border.rounded_rectangle = [x, y, w, h, PILL_RADIUS]
        if self._arrow:
            cx, cy = x + w / 2, y + h / 2
            r = h * 0.24
            if self._arrow == "left":
                self._tri.points = [cx - r, cy, cx + r, cy + r, cx + r, cy - r]
            else:
                self._tri.points = [cx + r, cy, cx - r, cy + r, cx - r, cy - r]
        if self._label:
            self._label.pos = self.pos
            self._label.size = self.size
            self._label.text_size = self.size

    def set_lit(self, lit):
        if lit:
            r, g, b, _ = self.on_color
            self._fill_col.rgba = (r, g, b, 0.10)
            self._border_col.rgba = self.on_color
            if self._label:
                self._label.color = self.on_color
            else:
                self._mark_col.rgba = self.on_color
        else:
            self._fill_col.rgba = (0, 0, 0, 0)
            self._border_col.rgba = PILL_OFF_BORDER
            if self._label:
                self._label.color = PILL_OFF_TEXT
            else:
                self._mark_col.rgba = PILL_OFF_TEXT


class TopAlerts(Widget):
    """Row of tell-tale pills across the top of the cluster."""

    # (key, pill kwargs, colour, blinks)
    PILLS = [
        ("left",  {"arrow": "left"},   TT_GREEN, False),
        ("high",  {"label": "HIGH"},   TT_BLUE,  False),
        ("oil",   {"label": "OIL"},    TT_RED,   True),
        ("batt",  {"label": "BATT"},   TT_RED,   False),
        ("temp",  {"label": "TEMP"},   TT_RED,   True),
        ("fan",   {"label": "FAN"},    TT_BLUE,  False),
        # ("cel",   {"label": "CEL"},    TT_AMBER, False),
        ("fuel",  {"label": "FUEL"},   TT_AMBER, False),
        ("brake", {"label": "BRAKE"},  TT_RED,   False),
        ("2step", {"label": "2-STEP"}, TT_CYAN,  False),
        # ("boost", {"label": "BOOST"},  TT_BOOST, True),
        ("right", {"arrow": "right"},  TT_GREEN, False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._active = {}
        self._blink_on = True

        self.row = BoxLayout(orientation="horizontal", size_hint=(None, None),
                             spacing=PILL_GAP, height=PILL_HEIGHT)
        self.pills = {}
        for key, pill_kwargs, color, blinks in self.PILLS:
            pill = TellTale(key, color, blinks=blinks, **pill_kwargs)
            self.pills[key] = pill
            self.row.add_widget(pill)
        self.add_widget(self.row)

        self.row.width = (sum(p.width for p in self.pills.values())
                          + PILL_GAP * (len(self.pills) - 1))

        # standalone WiFi tell-tale (top-left): hidden unless connected, blue when up
        self.wifi_pill = TellTale("wifi", TT_BLUE, label="WIFI")
        self.add_widget(self.wifi_pill)
        self.wifi_pill.opacity = 0

        self._reposition()
        Window.bind(on_resize=lambda *_: self._reposition())
        Clock.schedule_interval(self._blink, BLINK_PERIOD)
        Clock.schedule_once(self._check_wifi, 1)
        Clock.schedule_interval(self._check_wifi, WIFI_POLL)

    def _reposition(self, *_):
        top_y = WINDOW_HEIGHT - PILL_HEIGHT - ROW_TOP_MARGIN
        self.row.pos = ((Window.width - self.row.width) / 2, top_y)
        self.wifi_pill.pos = (WIFI_MARGIN_X, top_y)

    def _blink(self, _):
        self._blink_on = not self._blink_on
        self._refresh()

    def _check_wifi(self, _):
        if _wifi_connected():
            self.wifi_pill.opacity = 1
            self.wifi_pill.set_lit(True)
        else:
            self.wifi_pill.opacity = 0

    def set_state(self, state):
        """Recompute which tell-tales are active from the sensor state.

        Only signals we actually have are wired; the rest (BATT/CEL/BRAKE/2-STEP)
        stay dark until a source exists, which keeps the cluster calm rather than
        showing warnings we can't substantiate.
        """
        io = state.io
        fuel = state.fuel_level
        self._active = {
            "left":  io.left_indicator,
            "right": io.right_indicator,
            "high":  io.high_beam,
            "temp":  state.engine_temp > 100,
            # genuine loss of oil pressure only (avoid false alarms at rest)
            "oil":   state.rpm > 500 and 0 < state.oil_pressure_bar < 0.8,
            "fuel":  0 < fuel < 15,
            "boost": state.map > 1.32,
            "fan":   state.radiator_fan,
            "2step": state.two_step,
            "brake": io.parking_brake,
            "batt":  False,
            "cel":   False,
        }
        self._refresh()

    def _refresh(self):
        for key, pill in self.pills.items():
            on = self._active.get(key, False)
            pill.set_lit(on and (not pill.blinks or self._blink_on))
