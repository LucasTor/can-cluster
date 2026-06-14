"""Minimal centre readout (no box).

Top: a quiet 2x2 mono micro-grid (AIR / ENGINE / OIL / FUEL).
Below, split by hairlines: big bold BOOST and LAMBDA values.

Matches the minimal "Painel Gol" design — calm on a near-black background, one
accent, colour reserved for out-of-range values.
"""

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle

from theme import (
    FONT_MONO, VALUE, LABEL_DIM, LABEL_ACCENT, UNIT_DIM, HAIRLINE,
    TEXT, BOOST_NORMAL, TT_RED, TT_AMBER, LAMBDA_RICH, LAMBDA_LEAN,
    LAMBDA_STOICH, CARD_WIDTH, CARD_HEIGHT, WINDOW_HEIGHT,
)
from .readout import Readout


class CenterInfo(Widget):
    # (key, label, value format, warn predicate, warn colour)
    MICRO_FIELDS = [
        ("air",    "AIR",    "{:.0f} °C",  lambda v: v > 58,  TT_AMBER),
        ("engine", "ENGINE", "{:.0f} °C",  lambda v: v > 104, TT_RED),
        ("oil",    "OIL",    "{:.1f} BAR", None,              None),
        ("fuel",   "FUEL",   "{:.0f} %",   None,              None),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.readouts = {}

        self.size = (CARD_WIDTH, CARD_HEIGHT)
        self._center_vert = (WINDOW_HEIGHT / 2) - (self.size[1] / 2)
        self._reposition()

        self.vbox = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=self.size,
            pos=self.pos,
            padding=[10, 8, 10, 8],
            spacing=6,
        )
        self.add_widget(self.vbox)

        # --- micro-grid: AIR / ENGINE / OIL / FUEL ---
        grid = GridLayout(cols=2, size_hint=(1, None), height=150, spacing=[30, 6])
        self.vbox.add_widget(grid)
        for key, label, fmt, warn, warn_color in self.MICRO_FIELDS:
            grid.add_widget(self._micro_cell(key, label, fmt, warn, warn_color))

        self.vbox.add_widget(self._hairline())

        # --- big BOOST ---
        self.boost_value = self._big_block("BOOST", "BAR")
        self.vbox.add_widget(self._hairline())

        # --- big LAMBDA ---
        self.lambda_value, self.lambda_tag = self._big_block("LAMBDA", "STOICH", with_ref=True)

        self.bind(pos=self._sync, size=self._sync)
        Window.bind(on_resize=lambda *_: self._reposition())

    # ---- builders ----

    def _micro_cell(self, key, label, fmt, warn, warn_color):
        cell = BoxLayout(orientation="vertical", spacing=2)
        name = Label(text=label, font_name=FONT_MONO, font_size="18sp",
                     color=LABEL_DIM, halign="center", valign="middle",
                     size_hint=(1, None), height=22)
        value = Label(text="—", font_name=FONT_MONO, font_size="30sp",
                      color=VALUE, halign="center", valign="middle",
                      size_hint=(1, None), height=40)
        for lbl in (name, value):
            lbl.bind(size=lbl.setter("text_size"))
        cell.add_widget(name)
        cell.add_widget(value)
        kw = {"fmt": fmt}
        if warn is not None:
            kw.update(warn=warn, warn_color=warn_color)
        self.readouts[key] = Readout(value, **kw)
        return cell

    def _big_block(self, title, unit, with_ref=False):
        box = BoxLayout(orientation="vertical", spacing=2)
        box.add_widget(Label(text=title, font_name=FONT_MONO, font_size="30sp",
                             color=LABEL_ACCENT, halign="center", valign="middle",
                             size_hint=(1, None), height=38))
        value = Label(text="0.00", bold=True, font_size="120sp",
                      color=TEXT, halign="center", valign="middle")
        value.bind(size=value.setter("text_size"))
        box.add_widget(value)
        sub = Label(text=unit, font_name=FONT_MONO, font_size="16sp",
                    color=UNIT_DIM, halign="center", valign="middle",
                    size_hint=(1, None), height=22)
        box.add_widget(sub)
        self.vbox.add_widget(box)
        return (value, sub) if with_ref else value

    def _hairline(self):
        w = Widget(size_hint=(1, None), height=22)
        with w.canvas:
            Color(*HAIRLINE)
            rect = Rectangle()

        def sync(*_):
            rect.size = (64, 1)
            rect.pos = (w.center_x - 32, w.center_y)

        w.bind(pos=sync, size=sync)
        return w

    # ---- layout housekeeping ----

    def _reposition(self):
        self.pos = ((Window.width - self.width) / 2, self._center_vert)

    def _sync(self, *_):
        self.vbox.pos = self.pos
        self.vbox.size = self.size

    # ---- data ----

    def set_values(self, intake_c=None, water_c=None, oil_press_bar=None,
                   lambda_val=None, boost_bar=None, fuel_level=None):
        self.readouts["air"].set(intake_c)
        self.readouts["engine"].set(water_c)
        self.readouts["oil"].set(oil_press_bar)
        self.readouts["fuel"].set(fuel_level)

        if boost_bar is not None:
            sign = "+" if boost_bar >= 0 else "−"
            self.boost_value.text = f"{sign}{abs(boost_bar):.2f}"
            self.boost_value.color = TT_RED if boost_bar > 1.32 else BOOST_NORMAL

        if lambda_val is not None:
            self.lambda_value.text = f"{lambda_val:.2f}"
            if lambda_val < 0.85:
                self.lambda_value.color, self.lambda_tag.text = LAMBDA_RICH, "RICH"
            elif lambda_val > 1.05:
                self.lambda_value.color, self.lambda_tag.text = LAMBDA_LEAN, "LEAN"
            else:
                self.lambda_value.color, self.lambda_tag.text = LAMBDA_STOICH, "STOICH"
