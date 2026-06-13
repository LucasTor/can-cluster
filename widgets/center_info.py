from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import (
    Color,
    Line,
    RoundedRectangle,
)

from theme import ACCENT, FG, CARD_WIDTH, CARD_HEIGHT, CARD_RADIUS, WINDOW_HEIGHT
from .readout import Readout


class CenterInfo(Widget):
    """
    A center 'card' showing engine stats.
    Top: compact grid (AIR / ENGINE / OIL / FUEL)
    Bottom: BIG readouts that expand to fill remaining space (BOOST / LAMBDA)

    The displayed fields are driven by the ``COMPACT_FIELDS`` / ``BIG_FIELDS``
    specs below — adding or restyling a readout is a one-line change.
    """

    # (key, label, value format, initial value, warn predicate)
    COMPACT_FIELDS = [
        ("air",    "AIR",    "{:.0f} °C",  None, lambda v: v > 50),
        ("engine", "ENGINE", "{:.0f} °C",  None, None),
        ("oil",    "OIL",    "{:.1f} BAR", None, None),
        ("fuel",   "FUEL",   "{:.0f} %",   None, None),
    ]
    BIG_FIELDS = [
        ("boost",  "BOOST",  "{:.2f}", 0.0, lambda v: v >= 1.0),
        ("lambda", "LAMBDA", "{:.2f}", 1.0, lambda v: v < 0.85 or v > 1.05),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.readouts = {}

        # initial size and position (will auto-center on window resize)
        self.size = (CARD_WIDTH, CARD_HEIGHT)
        self._center_vert = (WINDOW_HEIGHT / 2) - (self.size[1] / 2)
        self._reposition()

        # background card
        with self.canvas.before:
            Color(*ACCENT)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[CARD_RADIUS])
            Color(*FG)
            self.border = Line(
                rounded_rectangle=[self.x, self.y, self.width, self.height, CARD_RADIUS],
                width=2,
            )

        # ---- layouts ----
        # container that stretches over the whole card
        self.vbox = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=self.size,
            pos=self.pos,
            padding=[20, 18, 20, 18],
            spacing=12,
        )
        self.add_widget(self.vbox)

        # TOP: compact grid (fixed height)
        self.grid = GridLayout(
            cols=2,
            rows=len(self.COMPACT_FIELDS),
            size_hint=(1, None),
            height=200,
            spacing=10,
        )
        self.vbox.add_widget(self.grid)
        for key, label, fmt, initial, warn in self.COMPACT_FIELDS:
            self._add_compact_row(key, label, fmt, initial, warn)

        # BOTTOM: BIG readouts (fills remaining vertical space)
        self.big = GridLayout(
            rows=len(self.BIG_FIELDS),
            size_hint=(1, 1),  # take all remaining space
            spacing=12,
        )
        self.vbox.add_widget(self.big)
        for key, label, fmt, initial, warn in self.BIG_FIELDS:
            self._add_big_tile(key, label, fmt, initial, warn)

        # keep visuals in place on size/pos changes
        self.bind(pos=self._sync_graphics, size=self._sync_graphics)
        Window.bind(on_resize=lambda *_: self._reposition())

    def _add_compact_row(self, key, label, fmt, initial, warn):
        name = Label(
            text=f"[b]{label}[/b]",
            markup=True,
            font_size="40sp",
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=40,
        )
        val = Label(
            text="—" if initial is None else fmt.format(initial),
            font_size="40sp",
            bold=True,
            halign="right",
            valign="middle",
            size_hint=(1, None),
            height=40,
        )
        name.bind(size=name.setter("text_size"))
        val.bind(size=val.setter("text_size"))
        self.grid.add_widget(name)
        self.grid.add_widget(val)
        self.readouts[key] = Readout(name, val, fmt, warn)

    def _add_big_tile(self, key, label, fmt, initial, warn):
        box = BoxLayout(orientation="vertical", padding=[10, 10, 10, 10])
        self.big.add_widget(box)
        title = Label(
            text=f"[b]{label}[/b]",
            markup=True,
            font_size="44sp",
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=30,
        )
        box.add_widget(title)
        value = Label(
            text=fmt.format(initial if initial is not None else 0.0),
            font_size="160sp",
            bold=True,
            halign="center",
            valign="middle",
            padding=[0, 0, 0, 24],
        )
        value.bind(size=value.setter("text_size"))
        box.add_widget(value)
        self.readouts[key] = Readout(title, value, fmt, warn)

    def _reposition(self):
        # center horizontally
        self.pos = ((Window.width - self.width) / 2, self._center_vert)

    def _sync_graphics(self, *_):
        # move background + outline with widget
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = [self.x, self.y, self.width, self.height, CARD_RADIUS]
        # sync the layout container
        self.vbox.pos = self.pos
        self.vbox.size = self.size

    def set_values(
        self,
        intake_c=None,
        water_c=None,
        oil_press_bar=None,
        lambda_val=None,
        boost_bar=None,
        fuel_level=None,
    ):
        self.readouts["air"].set(intake_c)
        self.readouts["engine"].set(water_c)
        self.readouts["oil"].set(oil_press_bar)
        self.readouts["fuel"].set(fuel_level)
        self.readouts["boost"].set(boost_bar)
        self.readouts["lambda"].set(lambda_val)
