"""Critical alarm banner — a full-width flashing red bar along the bottom.

Hidden until a genuinely dangerous condition is active (lean mixture, coolant
overheat, low oil pressure), then it flashes the named alarm(s). Unlike the calm
tell-tales, this is meant to be impossible to miss.
"""

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock

from theme import FONT_MONO, ALARM_BG, ALARM_TEXT

ALARM_HEIGHT = 60
ALARM_BLINK = 0.25   # seconds per flash toggle
FLASH_HI = 1.0
FLASH_LO = 0.16


class AlarmBar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            self._bg_col = Color(*ALARM_BG[:3], 0)
            self._bg = Rectangle()
        self._label = Label(text="", font_name=FONT_MONO, font_size="34sp", bold=True,
                            color=(*ALARM_TEXT[:3], 0), halign="center", valign="middle")
        self.add_widget(self._label)
        self._alarms = None
        self._on = True
        self._ev = None
        self._layout()
        Window.bind(size=lambda *_: self._layout())

    def _layout(self, *_):
        self._bg.pos = (0, 0)
        self._bg.size = (Window.width, ALARM_HEIGHT)
        self._label.pos = (0, 0)
        self._label.size = (Window.width, ALARM_HEIGHT)
        self._label.text_size = (Window.width, ALARM_HEIGHT)

    def set_alarms(self, alarms):
        """alarms: list of active alarm names; empty/None hides the bar."""
        alarms = list(alarms or [])
        if alarms == self._alarms:
            return
        self._alarms = alarms
        if alarms:
            self._label.text = "      ".join(alarms)
            if self._ev is None:
                self._ev = Clock.schedule_interval(self._blink, ALARM_BLINK)
        else:
            if self._ev is not None:
                self._ev.cancel()
                self._ev = None
            self._bg_col.a = 0
            self._label.color = (*ALARM_TEXT[:3], 0)

    def _blink(self, _):
        self._on = not self._on
        self._bg_col.a = FLASH_HI if self._on else FLASH_LO
        self._label.color = (*ALARM_TEXT[:3], 1.0 if self._on else 0.55)
