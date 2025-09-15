from kivy.uix.widget import Widget

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

class CenterInfo(Widget):
    """
    A center 'card' showing engine stats.
    Top: compact grid (AIR / ENGINE / OIL)
    Bottom: BIG readouts that expand to fill remaining space (BOOST / LAMBDA)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # initial size and position (will auto-center on window resize)
        self.size = (450, 600)
        self._center_vert = (720 / 2) - (self.size[1] / 2)
        self._reposition()

        # background card
        with self.canvas.before:
            Color(0.2392, 0.4588, 0.6588, 1.0)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[20])
            Color(1, 1, 1, 1)
            self.border = Line(
                rounded_rectangle=[self.x, self.y, self.width, self.height, 20], width=2
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
            rows=3,  # only the compact rows up here
            size_hint=(1, None),
            height=160,
            spacing=10,
        )
        self.vbox.add_widget(self.grid)

        def add_row(label_text):
            name = Label(
                text=f"[b]{label_text}[/b]",
                markup=True,
                font_size="40sp",
                halign="left",
                valign="middle",
                size_hint=(1, None),
                height=40,
            )
            val = Label(
                text="—",
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
            return name, val

        self.lbl_iat = add_row("AIR")
        self.lbl_clt = add_row("ENGINE")
        self.lbl_oilp = add_row("OIL")

        # BOTTOM: BIG readouts (fills remaining vertical space)
        self.big = GridLayout(
            rows=2,
            size_hint=(1, 1),  # take all remaining space
            spacing=12,
        )
        self.vbox.add_widget(self.big)

        # BOOST big tile
        self.boost_box = BoxLayout(orientation="vertical", padding=[10, 10, 10, 10])
        self.big.add_widget(self.boost_box)
        self.big_boost_title = Label(
            text="[b]BOOST[/b]",
            markup=True,
            font_size="44sp",
            padding=[0, 0, 0, 32],
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=30,
        )
        self.boost_box.add_widget(self.big_boost_title)
        self.big_boost_value = Label(
            text="0.00", font_size="160sp", bold=True, halign="center", valign="middle"
        )
        self.big_boost_value.bind(size=self.big_boost_value.setter("text_size"))
        self.boost_box.add_widget(self.big_boost_value)

        # LAMBDA big tile
        self.lambda_box = BoxLayout(orientation="vertical", padding=[10, 10, 10, 10])
        self.big.add_widget(self.lambda_box)
        self.big_lambda_title = Label(
            text="[b]LAMBDA[/b]",
            markup=True,
            font_size="44sp",
            padding=[0, 0, 0, 32],
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=30,
        )
        self.lambda_box.add_widget(self.big_lambda_title)
        self.big_lambda_value = Label(
            text="1.00", font_size="160sp", bold=True, halign="center", valign="middle"
        )
        self.big_lambda_value.bind(size=self.big_lambda_value.setter("text_size"))
        self.lambda_box.add_widget(self.big_lambda_value)

        # keep visuals in place on size/pos changes
        self.bind(pos=self._sync_graphics, size=self._sync_graphics)
        Window.bind(on_resize=lambda *_: self._reposition())

    def _reposition(self):
        # center horizontally
        self.pos = ((Window.width - self.width) / 2, self._center_vert)

    def _sync_graphics(self, *_):
        # move background + outline with widget
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = [self.x, self.y, self.width, self.height, 20]
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
    ):
        # compact rows
        if intake_c is not None:
            self.lbl_iat[1].text = f"{int(round(intake_c))} °C"
            if intake_c > 50:
                self.lbl_iat[0].color = (1, 0, 0, 1)
                self.lbl_iat[1].color = (1, 0, 0, 1)
            else:
                self.lbl_iat[0].color = (1, 1, 1, 1)
                self.lbl_iat[1].color = (1, 1, 1, 1)

        if water_c is not None:
            self.lbl_clt[1].text = f"{int(round(water_c))} °C"

        if oil_press_bar is not None:
            self.lbl_oilp[1].text = f"{oil_press_bar:.1f} bar"

        # BIG tiles
        if boost_bar is not None:
            self.big_boost_value.text = f"{boost_bar:.2f}"
            # optional color hint >1.0 bar
            if boost_bar >= 1.0:
                self.big_boost_value.color = (1, 0, 0, 1)
                self.big_boost_title.color = (1, 0, 0, 1)
            else:
                self.big_boost_value.color = (1, 1, 1, 1)
                self.big_boost_title.color = (1, 1, 1, 1)

        if lambda_val is not None:
            self.big_lambda_value.text = f"{lambda_val:.2f}"
            # optional color hint for rich/lean
            if lambda_val < 0.85 or lambda_val > 1.15:
                self.big_lambda_value.color = (1, 0, 0, 1)
                self.big_lambda_title.color = (1, 0, 0, 1)
            else:
                self.big_lambda_value.color = (1, 1, 1, 1)
                self.big_lambda_title.color = (1, 1, 1, 1)

