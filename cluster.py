import os
import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rotate, PushMatrix, PopMatrix, RoundedRectangle
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.config import Config
from kivy.uix.gridlayout import GridLayout
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout

import math
import random

PROD = bool(os.environ.get('PROD', False))

if not PROD:
    Config.set("graphics", "fullscreen", "0")
    Config.set("graphics", "width", "1920")
    Config.set("graphics", "height", "720")

kivy.require("2.0.0")

LabelBase.register(DEFAULT_FONT, "./Audiowide.ttf")

class Gauge(Widget):
    def __init__(
        self,
        title="Speed",
        subtitle='',
        max_value=180,
        unit="km/h",
        ticks=10,
        angle_range=270,
        label_map={},
        show_digital_value=True,
        redline_from=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.title = title
        self.subtitle = subtitle
        self.max_value = max_value
        self.unit = unit
        self.ticks = ticks
        self.angle_range = angle_range
        self.label_map = label_map
        self.show_title = show_digital_value
        self.redline_from = redline_from
        self.needle_angle = 180
        self.current_angle = 180
        self.value = 0

        with self.canvas:
            self.draw_gauge()

        Clock.schedule_once(self.init_needle, 0)
        Clock.schedule_interval(self.smooth_update, 1 / 60.0)

        self.value_label = Label(
            text="0",
            font_size="32sp",
            bold=True,
            pos=(self.center_x, self.center_y),
            size_hint=(None, None),
            size=(100, 50),
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1),
        )
        self.value_label.bind(size=self.value_label.setter("text_size"))
        self.value_label.center = self.center
        if show_digital_value:
            self.add_widget(self.value_label)

        self.update_value(0, smooth=False)
        Clock.schedule_once(lambda _: self.update_value(max_value, update_label=False), 1)
        Clock.schedule_once(lambda _: self.update_value(0), 2)

    def draw_gauge(self):
        center_x, center_y = self.center
        radius = min(self.width, self.height) / 2

        Color(0.1, 0.1, 0.1)
        Ellipse(pos=self.pos, size=self.size)

        tick_count = self.ticks
        tick_angle = (-self.angle_range) / (tick_count - 1)

        for i in range(0, tick_count):
            angle_deg = (-90 - ((360 - self.angle_range) / 2)) + (tick_angle * i)
            angle_rad = math.radians(angle_deg)
            inner_radius = radius * 0.9
            outer_radius = radius * 1

            x1 = center_x + inner_radius * math.cos(angle_rad)
            y1 = center_y + inner_radius * math.sin(angle_rad)
            x2 = center_x + outer_radius * math.cos(angle_rad)
            y2 = center_y + outer_radius * math.sin(angle_rad)

            Color(1, 1, 1)
            Line(points=[x1, y1, x2, y2], width=2)

            value = int((i / (tick_count - 1)) * self.max_value)
            label_x = center_x + (radius * 0.75) * math.cos(angle_rad) - 48
            label_y = center_y + (radius * 0.75) * math.sin(angle_rad) - 48
            label = self.label_map.get(value, value)
            self.add_widget(
                Label(
                    text=f"[b]{str(label)}[/b]",
                    pos=(label_x, label_y),
                    font_size="12sp",
                    markup=True,
                    halign="center",
                    valign="middle",
                )
            )

        self.add_widget(
            Label(
                text=self.title,
                size=(self.width, 30),
                pos=(self.x, self.y + self.size[0] * 0.1),
                font_size="16sp",
                halign="center",
                valign="middle",
            )
        )

        self.add_widget(
            Label(
                text=self.subtitle,
                size=(self.width, 30),
                pos=(self.x, self.y + self.size[0] * 0.04),
                font_size="8sp",
                halign="center",
                valign="middle",
            )
        )

        if self.redline_from and self.redline_from > 0 and self.redline_from < self.max_value:
            start = self._angle_for_value(self.redline_from)
            end   = self._angle_for_value(self.max_value)
            # Ensure start < end for Kivy's CCW arc
            if start > end:
                start, end = end, start
            Color(1, 0, 0, .5)
            # Slightly inside the outer edge so it looks clean
            Line(circle=(center_x, center_y, radius * 0.98, start, end),
                width=10, cap='round')
            
    def _angle_for_value(self, v):
        # Convert a value in [0, max_value] to screen angle (degrees),
        # matching your needle orientation (0° to the right, CCW positive; your dial spans 'angle_range').
        v = max(0, min(v, self.max_value))
        # this mirrors your update_value() math:
        return ( (-self.angle_range / 2.0) + (v / float(self.max_value)) * self.angle_range )

    def init_needle(self, *args):
        self.center_x = self.x + self.width / 2
        self.center_y = self.y + self.height / 2
        with self.canvas:
            PushMatrix()
            self.rot = Rotate(origin=(self.center_x, self.center_y), angle=self.needle_angle)
            Color(0.0118, 0.3373, 0.9882, 0.8)
            start_y = self.center_y + self.height / 4
            end_y = self.center_y + self.height / 2
            self.needle = Line(points=[self.center_x, start_y, self.center_x, end_y], width=6)
            PopMatrix()

    def update_value(self, value, smooth=True, update_label=True):
        clamped = max(0, min(value, self.max_value))
        self.value = clamped
        angle = -( (-self.angle_range / 2) + ((clamped / self.max_value) * self.angle_range) )
        if smooth:
            self.needle_angle = angle
        else:
            self.needle_angle = angle
            self.current_angle = angle

        if update_label:
            self.value_label.text = f"{int(clamped)}"

            if self.redline_from and self.value > self.redline_from:
                self.value_label.color = (1, 0, 0, 1)
            else:
                self.value_label.color = (1, 1, 1, 1)

        self.value_label.center = self.center

    def smooth_update(self, dt):
        smoothing_speed = 5
        diff = self.needle_angle - self.current_angle
        self.current_angle += diff * smoothing_speed * dt

        if hasattr(self, "rot"):
            self.rot.angle = self.current_angle

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
            Color(0.0118, 0.3373, 0.9882, 0.5)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[20])
            Color(1, 1, 1, 0.15)
            self.border = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 20], width=1)

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
            name = Label(text=f"[b]{label_text}[/b]",
                         markup=True,
                         font_size="14sp",
                         halign="left", valign="middle",
                         size_hint=(1, None), height=40)
            val = Label(text="—",
                        font_size="14sp",
                        bold=True,
                        halign="right", valign="middle",
                        size_hint=(1, None), height=40)
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
            size_hint=(1, 1),   # take all remaining space
            spacing=12,
        )
        self.vbox.add_widget(self.big)

        # BOOST big tile
        self.boost_box = BoxLayout(orientation="vertical", padding=[10, 10, 10, 10])
        self.big.add_widget(self.boost_box)
        self.big_boost_title = Label(text="[b]BOOST[/b]", markup=True, font_size="18sp",
                                     halign="center", valign="middle", size_hint=(1, None), height=30)
        self.boost_box.add_widget(self.big_boost_title)
        self.big_boost_value = Label(text="0.00", font_size="64sp", bold=True,
                                     halign="center", valign="middle")
        self.big_boost_value.bind(size=self.big_boost_value.setter("text_size"))
        self.boost_box.add_widget(self.big_boost_value)

        # LAMBDA big tile
        self.lambda_box = BoxLayout(orientation="vertical", padding=[10, 10, 10, 10])
        self.big.add_widget(self.lambda_box)
        self.big_lambda_title = Label(text="[b]LAMBDA[/b]", markup=True, font_size="18sp",
                                      halign="center", valign="middle", size_hint=(1, None), height=30)
        self.lambda_box.add_widget(self.big_lambda_title)
        self.big_lambda_value = Label(text="1.00", font_size="64sp", bold=True,
                                      halign="center", valign="middle")
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

    def set_values(self, intake_c=None, water_c=None, oil_press_bar=None,
                   lambda_val=None, boost_bar=None):
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

class Dashboard(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.speed_gauge = Gauge(
            title="SPEED",
            subtitle="KM/H",
            max_value=240,
            unit="km/h",
            size=(600, 600),
            pos=(100, 60),
            ticks=13,
            angle_range=270,
        )

        self.rpm_gauge = Gauge(
            title="RPM",
            subtitle="X1000",
            max_value=8000,
            unit="rpm",
            size=(600, 600),
            pos=(1220, 60),
            ticks=9,
            redline_from=5500,
            label_map={
                1000: "1",
                2000: "2",
                3000: "3",
                4000: "4",
                5000: "5",
                6000: "6",
                7000: "7",
                8000: "8",
            },
        )

        self.center_info = CenterInfo()

        self.add_widget(self.speed_gauge)
        self.add_widget(self.rpm_gauge)
        self.add_widget(self.center_info)

        # demo smaller window while developing
        if PROD:
            pass
        else:
            Window.size = (1920 / 2, 720 / 2)
            Clock.schedule_once(lambda x: Clock.schedule_interval(self.simulate_data, 1), 3)
        

    def simulate_data(self, dt):
        speed = random.uniform(0, 250)
        rpm = random.uniform(1000, 8000)

        # Simulated engine stats
        intake_c = random.uniform(25, 65)
        water_c = random.uniform(70, 105)
        oil_press_bar = random.uniform(1.5, 5.0)
        lambda_val = random.uniform(0.8, 1.2)
        boost_bar = random.uniform(0.0, 1.5)  # demo boost

        self.speed_gauge.update_value(speed)
        self.rpm_gauge.update_value(rpm)
        self.center_info.set_values(
            intake_c=intake_c,
            water_c=water_c,
            oil_press_bar=oil_press_bar,
            lambda_val=lambda_val,
            boost_bar=boost_bar,
        )



class CarClusterApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    CarClusterApp().run()
    print(Window.size)
