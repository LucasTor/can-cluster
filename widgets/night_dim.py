"""Night-mode dimming — a full-screen translucent black overlay.

When the ECU reports night mode, this fades up a black veil over the whole
cluster to knock the brightness down so it isn't blinding at night. Sits below
the alarm banner so critical alarms stay full-brightness.
"""

from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.animation import Animation

NIGHT_DIM = 0.55   # veil opacity at night (0 = no dimming, 1 = black)
FADE = 0.6         # seconds to fade in/out


class NightDim(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            self._col = Color(0, 0, 0, 0)
            self._rect = Rectangle()
        self._night = False
        self._layout()
        Window.bind(size=lambda *_: self._layout())

    def _layout(self, *_):
        self._rect.pos = (0, 0)
        self._rect.size = Window.size

    def set_night(self, night):
        night = bool(night)
        if night == self._night:
            return
        self._night = night
        Animation.cancel_all(self._col, "a")
        Animation(a=NIGHT_DIM if night else 0.0, duration=FADE).start(self._col)
