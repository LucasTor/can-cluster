from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import NumericProperty
from kivy.clock import Clock
from kivy.core.window import Window

from theme import SHIFT_FILL, SHIFT_TEXT, CARD_WIDTH, CARD_HEIGHT, WINDOW_HEIGHT


class ShiftCenterBanner(Widget):
    """
    Plain yellow rounded rectangle with red 'SHIFT' centered.
    Appears when rpm >= shift_rpm; hidden otherwise.
    Blinks while visible. Draws in canvas.after so it sits on top.
    """

    shift_rpm = NumericProperty(7000)

    def __init__(
        self,
        shift_rpm=7000,
        width_ratio=0.36,
        height_ratio=0.18,
        corner_px=22,
        blink_hz=2.0,  # blink frequency (cycles/sec)
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.shift_rpm = shift_rpm
        self.width_ratio = width_ratio
        self.height_ratio = height_ratio
        self.corner_px = corner_px
        self.blink_hz = blink_hz

        # state
        self._visible = False
        self._blink_on = False
        self._blink_ev = None

        # graphics refs
        self._fill_col = None
        self._rect = None

        # draw on top of siblings
        with self.canvas:
            self._fill_col = Color(*SHIFT_FILL[:3], 0.0)  # yellow, hidden initially
            self._rect = RoundedRectangle(
                pos=(0, 0), size=(0, 0), radius=[self.corner_px]
            )

        self._label = Label(
            text="[b]SHIFT[/b]",
            markup=True,
            font_size="64sp",
            color=(*SHIFT_TEXT[:3], 0.0),  # hidden until visible
            halign="center",
            valign="middle",
            font_name='fonts/RobotoMono-Bold.ttf'
        )

        self.add_widget(self._label)

        # cover the parent
        self.bind(pos=self._layout, size=self._layout)

    # keep sized to parent (Dashboard)
    def on_parent(self, *args):
        if self.parent:
            self.size = self.parent.size
            self.pos = self.parent.pos
            self.parent.bind(size=self._sync_to_parent, pos=self._sync_to_parent)
            self._layout()

    def _sync_to_parent(self, *_):
        if self.parent:
            self.size = self.parent.size
            self.pos = self.parent.pos
            self._layout()

    def _layout(self, *_):
        self.size = (CARD_WIDTH, CARD_HEIGHT)
        self._center_vert = (WINDOW_HEIGHT / 2) - (self.size[1] / 2)

        # rect geometry
        self._rect.size = (CARD_WIDTH, CARD_HEIGHT)
        self._reposition()

        # label centered & wrapped
        self._label.size = self.size
        self._label.text_size = self._label.size
        self._label.halign = "center"
        self._label.valign = "middle"

    def _reposition(self):
        # center horizontally
        self._rect.pos = ((Window.width - CARD_WIDTH) / 2, self._center_vert)
        self._label.pos = ((Window.width - CARD_WIDTH) / 2, self._center_vert)

    # --- visibility & blinking ---

    def _apply_visible(self, show: bool):
        if self._visible == show:
            return
        self._visible = show

        if show:
            # set initial "bright" state
            self._set_alpha(fill=0.95, text=1.0)
            self._start_blink()
        else:
            self._stop_blink()
            self._set_alpha(fill=0.0, text=0.0)

    def _set_alpha(self, fill: float, text: float):
        # fill (yellow)
        fr, fg, fb, _ = self._fill_col.rgba
        self._fill_col.rgba = (fr, fg, fb, fill)
        # text (red)
        self._label.color = (*SHIFT_TEXT[:3], text)

    def _blink_tick(self, dt):
        # toggle between bright and dim states
        self._blink_on = not self._blink_on
        if not self._visible:
            return
        if self._blink_on:
            self._set_alpha(fill=1, text=1.0)
        else:
            self._set_alpha(fill=1, text=0.60)

    def _start_blink(self):
        if self._blink_ev is None:
            # toggle twice per cycle => schedule at half-period
            half_period = max(0.05, 0.5 / max(0.1, self.blink_hz))
            self._blink_ev = Clock.schedule_interval(self._blink_tick, half_period)

    def _stop_blink(self):
        if self._blink_ev is not None:
            self._blink_ev.cancel()
            self._blink_ev = None
        self._blink_on = False

    # --- public API ---

    def set_rpm(self, rpm: float):
        self._apply_visible(rpm >= self.shift_rpm)

    # optional: force a one-off flash to confirm visibility
    def demo_flash(self, seconds=0.8):
        self._apply_visible(True)
        Clock.schedule_once(lambda *_: self._apply_visible(False), seconds)

