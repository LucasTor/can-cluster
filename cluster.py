import logging

logging.getLogger("kivy").setLevel(logging.CRITICAL)

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

import math
import random

Config.set("graphics", "fullscreen", "0")
Config.set("graphics", "width", "1920")
Config.set("graphics", "height", "720")

kivy.require("2.0.0")

print("Window size:", Window.size)

LabelBase.register(DEFAULT_FONT, "./Michroma.ttf")


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
        self.needle_angle = 180
        self.current_angle = 180

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
        angle = -( (-self.angle_range / 2) + ((clamped / self.max_value) * self.angle_range) )
        if smooth:
            self.needle_angle = angle
        else:
            self.needle_angle = angle
            self.current_angle = angle

        if update_label:
            self.value_label.text = f"{int(clamped)}"

        self.value_label.center = self.center

    def smooth_update(self, dt):
        smoothing_speed = 5
        diff = self.needle_angle - self.current_angle
        self.current_angle += diff * smoothing_speed * dt

        if hasattr(self, "rot"):
            self.rot.angle = self.current_angle


class CenterInfo(Widget):
    """
    A small 'card' in the middle to show engine stats.
    Use set_values(...) to update from your data source.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # initial size and position (will auto-center on window resize)
        self.size = (450, 600)
        self._center_vert = (720 / 2) - (self.size[1] / 2)  # y from bottom where the card sits
        self._reposition()

        # background card
        with self.canvas.before:
            Color(0.0118, 0.3373, 0.9882, 0.5)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[20])
            Color(1, 1, 1, 0.15)
            # outline
            self.border = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 20], width=1)

        # layout & labels
        self.grid = GridLayout(
            cols=2,
            rows=4,
            padding=[20, 18, 20, 18],
            spacing=10,
            size_hint=(None, None),
            size=self.size,
            pos=self.pos,
        )
        self.add_widget(self.grid)

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
            return val

        self.lbl_iat = add_row("AIR")
        self.lbl_clt = add_row("ENGINE")
        self.lbl_oilp = add_row("OIL")

        # keep visuals in place on size/pos changes
        self.bind(pos=self._sync_graphics, size=self._sync_graphics)
        Window.bind(on_resize=lambda *_: self._reposition())

    def _reposition(self):
        # center horizontally
        self.pos = ((Window.width - self.width) / 2, self._center_vert)

    def _sync_graphics(self, *_):
        # move background + outline + grid with widget
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = [self.x, self.y, self.width, self.height, 20]
        self.grid.pos = self.pos
        self.grid.size = self.size

    def set_values(self, intake_c=None, water_c=None, oil_press_bar=None, oil_temp_c=None):
        if intake_c is not None:
            self.lbl_iat.text = f"{int(round(intake_c))} °C"
        if water_c is not None:
            self.lbl_clt.text = f"{int(round(water_c))} °C"
        if oil_press_bar is not None:
            # show one decimal for pressure
            self.lbl_oilp.text = f"{oil_press_bar:.1f} bar"

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
        Window.size = (1920 / 2, 720 / 2)

        # Demo data feed (replace with your real sensors and call set_values)
        Clock.schedule_interval(self.simulate_data, 1)

    def simulate_data(self, dt):
        speed = random.uniform(0, 250)
        rpm = random.uniform(1000, 8000)

        # Simulated engine stats
        intake_c = random.uniform(25, 65)
        water_c = random.uniform(70, 105)
        oil_temp_c = random.uniform(70, 120)
        oil_press_bar = random.uniform(1.5, 5.0)

        self.speed_gauge.update_value(speed)
        self.rpm_gauge.update_value(rpm)
        self.center_info.set_values(
            intake_c=intake_c,
            water_c=water_c,
            oil_temp_c=oil_temp_c,
            oil_press_bar=oil_press_bar,
        )


class CarClusterApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    CarClusterApp().run()
    print(Window.size)
