import logging

logging.getLogger("kivy").setLevel(logging.CRITICAL)

import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rotate, PushMatrix, PopMatrix
from kivy.uix.label import Label
from kivy.clock import Clock
import math
import random

from kivy.config import Config

Config.set("graphics", "fullscreen", "0")
Config.set("graphics", "width", "1920")
Config.set("graphics", "height", "720")

kivy.require("2.0.0")

from kivy.core.window import Window

print("Window size:", Window.size)

from kivy.core.text import LabelBase, DEFAULT_FONT

LabelBase.register(DEFAULT_FONT, "./Michroma.ttf")


class Gauge(Widget):
    def __init__(
        self,
        title="Speed",
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
        self.max_value = max_value
        self.unit = unit
        self.ticks = ticks
        self.angle_range = angle_range
        self.label_map = label_map
        self.show_title = show_digital_value
        self.needle_angle = -45
        self.current_angle = -45

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
        if show_digital_value:
            self.add_widget(self.value_label)

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

    def init_needle(self, *args):
        self.center_x = self.x + self.width / 2
        self.center_y = self.y + self.height / 2
        with self.canvas:
            PushMatrix()
            self.rot = Rotate(
                origin=(self.center_x, self.center_y), angle=self.needle_angle
            )
            Color(0.0118, 0.3373, 0.9882, 0.8)
            start_y = self.center_y + self.height / 4
            end_y = self.center_y + self.height / 2

            self.needle = Line(
                points=[self.center_x, start_y, self.center_x, end_y], width=6
            )

            PopMatrix()

    def update_value(self, value):
        clamped = max(0, min(value, self.max_value))
        angle = -(
            (-self.angle_range / 2) + ((clamped / self.max_value) * self.angle_range)
        )
        self.needle_angle = angle

        self.value_label.text = f"{int(clamped)}"

        self.value_label.center = self.center

    def smooth_update(self, dt):

        smoothing_speed = 5
        diff = self.needle_angle - self.current_angle
        self.current_angle += diff * smoothing_speed * dt

        if hasattr(self, "rot"):
            self.rot.angle = self.current_angle


class Dashboard(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.speed_gauge = Gauge(
            title="SPEED",
            max_value=240,
            unit="km/h",
            size=(600, 600),
            pos=(100, 60),
            ticks=13,
            angle_range=270,
        )
        self.rpm_gauge = Gauge(
            title="RPM",
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

        self.fuel_gauge = Gauge(
            title="",
            max_value=100,
            unit="%",
            size=(200, 200),
            pos=(860, 60),
            ticks=5,
            angle_range=270,
            label_map={0: "E", 25: "", 50: "", 75: "", 100: "F"},
            show_digital_value=False,
        )

        self.add_widget(self.speed_gauge)
        self.add_widget(self.rpm_gauge)
        self.add_widget(self.fuel_gauge)

        Clock.schedule_interval(self.simulate_data, 2)

        from kivy.core.window import Window

        Window.size = (1920 / 2, 720 / 2)

    def simulate_data(self, dt):
        speed = random.uniform(0, 250)
        rpm = random.uniform(0, 8000)
        fuel = random.uniform(10, 100)

        self.speed_gauge.update_value(speed)
        self.rpm_gauge.update_value(rpm)
        self.fuel_gauge.update_value(fuel)


class CarClusterApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    CarClusterApp().run()
    from kivy.core.window import Window

    print(Window.size)
