"""Minimal centre readout (no box).

Top: a quiet mono micro-grid in 3 columns (AIR / ENGINE / OIL / FUEL P / FUEL / GEAR).
Below, split by hairlines: big bold BOOST and LAMBDA values.

Matches the minimal "Painel Gol" design — calm on a near-black background, one
accent, colour reserved for out-of-range values.
"""

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle

from theme import (
    FONT_MONO, VALUE, LABEL_DIM, LABEL_ACCENT, UNIT_DIM, HAIRLINE,
    BOOST_NORMAL, TT_RED, TT_AMBER, CARD_WIDTH, CARD_HEIGHT,
    WINDOW_HEIGHT,
)
from .readout import Readout


BIG_VALUE_FONT = "120sp"
CENTER_Y_OFFSET = 32  # nudge the whole readout down, away from the top tell-tales


class CenterInfo(Widget):
    # (key, label, value format, warn predicate, warn colour)
    MICRO_FIELDS = [
        ("air",    "AIR",    "{:.0f} °C",  lambda v: v > 58,  TT_AMBER),
        ("engine", "ENGINE", "{:.0f} °C",  lambda v: v > 104, TT_RED),
        ("oil",    "OIL",    "{:.1f} BAR", None,              None),
        ("fpress", "FUEL P", "{:.1f} BAR", None,              None),
        ("fuel",   "FUEL",   "{:.0f} %",   None,              None),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.readouts = {}

        self.size = (CARD_WIDTH, CARD_HEIGHT)
        self._center_vert = (WINDOW_HEIGHT / 2) - (self.size[1] / 2) - CENTER_Y_OFFSET
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

        # --- micro-grid: 3 columns, 2 rows (temps / pressures / level / gear) ---
        grid = GridLayout(cols=3, size_hint=(1, None), height=134, spacing=[14, 6])
        self.vbox.add_widget(grid)
        for key, label, fmt, warn, warn_color in self.MICRO_FIELDS:
            grid.add_widget(self._micro_cell(key, label, fmt, warn, warn_color))
        gear_cell, self.gear_value = self._cell("GEAR", "N")
        grid.add_widget(gear_cell)

        self.vbox.add_widget(self._hairline())

        # --- big BOOST ---
        self.boost_value = self._big_block("BOOST", "BAR")
        self.vbox.add_widget(self._hairline())

        # --- big LAMBDA --- (starts at stoich 1.00, blue)
        self.lambda_value, self.lambda_tag = self._big_block(
            "LAMBDA", "STOICH", initial="1.00", with_ref=True)

        self.bind(pos=self._sync, size=self._sync)
        Window.bind(on_resize=lambda *_: self._reposition())

    # ---- builders ----

    def _cell(self, label, initial):
        """A label-over-value micro cell; returns (cell, value_label)."""
        cell = BoxLayout(orientation="vertical", spacing=2)
        name = Label(text=label, font_name=FONT_MONO, font_size="18sp",
                     color=LABEL_DIM, halign="center", valign="middle",
                     size_hint=(1, None), height=22)
        value = Label(text=initial, font_name=FONT_MONO, font_size="28sp",
                      color=VALUE, halign="center", valign="middle",
                      size_hint=(1, None), height=40)
        for lbl in (name, value):
            lbl.bind(size=lbl.setter("text_size"))
        cell.add_widget(name)
        cell.add_widget(value)
        return cell, value

    def _micro_cell(self, key, label, fmt, warn, warn_color):
        cell, value = self._cell(label, "—")
        kw = {"fmt": fmt}
        if warn is not None:
            kw.update(warn=warn, warn_color=warn_color)
        self.readouts[key] = Readout(value, **kw)
        return cell

    def _big_block(self, title, unit, initial="0.00", with_ref=False):
        # The value sizes to its own rendered glyphs (never clipped). Title and
        # unit are placed just outside the visible digits using a fraction of the
        # value's *rendered* glyph height — that fraction scales with font/density
        # so the spacing is identical on the dev Mac and the Pi.
        # Starts in the accent blue so it matches the gauges during the intro
        # sweep (before any data arrives), rather than flashing white first.
        block = FloatLayout(size_hint=(1, None), height=200)
        value = Label(text=initial, bold=True, font_size=BIG_VALUE_FONT,
                      color=BOOST_NORMAL, size_hint=(None, None))
        name = Label(text=title, font_name=FONT_MONO, font_size="30sp",
                     color=LABEL_ACCENT, size_hint=(None, None))
        sub = Label(text=unit, font_name=FONT_MONO, font_size="16sp",
                    color=UNIT_DIM, size_hint=(None, None))
        for lbl in (value, name, sub):
            lbl.bind(texture_size=lbl.setter("size"))
            block.add_widget(lbl)

        def place(*_):
            # Digits aren't centred in their line box (big ascent leading): the
            # caps sit ~0.22 above centre, the baseline ~0.42 below. Offsets are
            # fractions of the rendered glyph height, so they hold at any density.
            cx, cy = block.center_x, block.center_y
            value.center_x, value.center_y = cx, cy
            top = value.height * 0.27   # just above the digit caps
            bot = value.height * 0.42   # just below the digit baseline
            name.center_x = cx
            name.center_y = cy + top + name.height * 0.5 + 1
            sub.center_x = cx
            sub.center_y = cy - bot - sub.height * 0.5 - 1

        for lbl in (value, name, sub):
            lbl.bind(size=place)
        block.bind(pos=place, size=place)

        self.vbox.add_widget(block)
        return (value, sub) if with_ref else value

    def _hairline(self):
        # An AnchorLayout reliably centres the bar regardless of layout order
        # (positioning a raw Rectangle by center_x raced the layout on the Pi).
        holder = AnchorLayout(size_hint=(1, None), height=22)
        bar = Widget(size_hint=(None, None), size=(64, 1))
        with bar.canvas:
            Color(*HAIRLINE)
            rect = Rectangle(size=bar.size)
        bar.bind(pos=lambda *_: setattr(rect, "pos", bar.pos),
                 size=lambda *_: setattr(rect, "size", bar.size))
        holder.add_widget(bar)
        return holder

    # ---- layout housekeeping ----

    def _reposition(self):
        self.pos = ((Window.width - self.width) / 2, self._center_vert)

    def _sync(self, *_):
        self.vbox.pos = self.pos
        self.vbox.size = self.size

    # ---- data ----

    def set_values(self, intake_c=None, water_c=None, oil_press_bar=None,
                   lambda_val=None, boost_bar=None, fuel_level=None,
                   fuel_press_bar=None, gear=None, rpm=None):
        self.readouts["air"].set(intake_c)
        self.readouts["engine"].set(water_c)
        self.readouts["oil"].set(oil_press_bar)
        self.readouts["fpress"].set(fuel_press_bar)
        self.readouts["fuel"].set(fuel_level)
        if gear is not None:
            self.gear_value.text = str(gear)

        if boost_bar is not None:
            self.boost_value.text = f"{boost_bar:.2f}"
            self.boost_value.color = TT_RED if boost_bar > 1.32 else BOOST_NORMAL

        if lambda_val is not None:
            self.lambda_value.text = f"{lambda_val:.2f}"
            # Below ~500 rpm the engine isn't burning, so lambda reads pegged-lean
            # on ambient O2 — suppress the RICH/LEAN alert and stay neutral.
            if rpm is not None and rpm < 500:
                self.lambda_value.color, self.lambda_tag.text = BOOST_NORMAL, "STOICH"
            # Match the rest of the cluster's palette: accent blue when safe,
            # amber when rich, red when lean (lean is the dangerous side).
            elif lambda_val < 0.85:
                self.lambda_value.color, self.lambda_tag.text = TT_AMBER, "RICH"
            elif lambda_val > 1.05:
                self.lambda_value.color, self.lambda_tag.text = TT_RED, "LEAN"
            else:
                self.lambda_value.color, self.lambda_tag.text = BOOST_NORMAL, "STOICH"
