from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Triangle
from kivy.properties import BooleanProperty, NumericProperty, OptionProperty
from kivy.clock import Clock


class TurnIndicator(Widget):
    """
    A turn indicator arrow (shaft + triangular head).
    side: 'left' or 'right'
    """
    side = OptionProperty('left', options=('left', 'right'))
    blink_hz = NumericProperty(2.0)
    active = BooleanProperty(False)

    def __init__(self, side='left', blink_hz=2.0, **kwargs):
        super().__init__(**kwargs)
        self.side = side
        self.blink_hz = blink_hz

        # state
        self._blink_on = False
        self._blink_ev = None

        # graphics refs
        self._col = None
        self._shaft = None
        self._head = None

        with self.canvas:
            # Arrow color
            self._col = Color(0.0, 1.0, 0.0, 0.0)  # green, hidden initially
            # shaft + head
            self._shaft = Line(points=[], width=12, cap='square')
            self._head = Triangle(points=[0, 0, 0, 0, 0, 0])

        self.bind(pos=self._layout, size=self._layout)

    def on_parent(self, *_):
        if not self.size or self.size == (0, 0):
            self.size = (90, 90)
        self._layout()

    def _layout(self, *_):
        x, y = self.pos
        w, h = self.size
        cx, cy = x + w / 2, y + h / 2
        r = min(w, h) * 0.5

        if self.side == 'left':
            tip = (cx - r * 0.8, cy)
            base1 = (tip[0] + r * 0.5, cy + r * 0.45)
            base2 = (tip[0] + r * 0.5, cy - r * 0.45)
            shaft_far = (cx + r * 0.2, cy)
        else:
            tip = (cx + r * 0.8, cy)
            base1 = (tip[0] - r * 0.5, cy + r * 0.45)
            base2 = (tip[0] - r * 0.5, cy - r * 0.45)
            shaft_far = (cx - r * 0.2, cy)

        # triangle head
        self._head.points = [*tip, *base1, *base2]

        # base midpoint
        bx = (base1[0] + base2[0]) / 2.0
        by = (base1[1] + base2[1]) / 2.0

        # direction vector (tip - base)
        dx = tip[0] - bx
        dy = tip[1] - by
        mag = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux, uy = dx / mag, dy / mag

        # backoff from base (avoid overlap)
        shaft_width = getattr(self._shaft, 'width', 4)
        backoff = shaft_width * 0.5 + 1.0
        shaft_start = (bx - ux * backoff, by - uy * backoff)

        # final shaft line
        self._shaft.points = [*shaft_start, *shaft_far]


    # --- visibility / blinking ---

    def _set_alpha(self, a_arrow: float):
        r, g, b, _ = self._col.rgba
        self._col.rgba = (r, g, b, a_arrow)

    def _set_color(self, on):
        color_on = (0.1, 0.1, 0.1, 1)
        color_off = (0.0, 1.0, 0.0, 1)
        self._col.rgba = color_on if on else color_off

    def _blink_tick(self, dt):
        if not self.active:
            return
        self._blink_on = not self._blink_on
        self._set_color(self._blink_on)
        # if self._blink_on:
        #     self._set_alpha(1.0)   # full green
        # else:
        #     self._set_alpha(0.3)   # dimmed / ghosted

    def _start_blink(self):
        if self._blink_ev is None:
            half_period = max(0.05, 0.5 / max(0.1, self.blink_hz))
            self._blink_ev = Clock.schedule_interval(self._blink_tick, half_period)

    def _stop_blink(self):
        if self._blink_ev is not None:
            self._blink_ev.cancel()
            self._blink_ev = None
        self._blink_on = False

    def set_active(self, on: bool):
        if self.active == on:
            return
        self.active = on
        if on:
            self._set_alpha(1.0)
            self._start_blink()
        else:
            self._stop_blink()
            self._set_alpha(0.2)  # idle = faint arrow
