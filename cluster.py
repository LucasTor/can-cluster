import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rotate, PushMatrix, PopMatrix
from kivy.uix.label import Label
from kivy.clock import Clock
import math
import random

kivy.require('2.0.0')

class Gauge(Widget):
    def __init__(self, title="Speed", max_value=180, unit="km/h", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.max_value = max_value
        self.unit = unit
        self.needle_angle = -130  # Starting angle

        with self.canvas:
            self.draw_gauge()

        # self.label = Label(text=f"{self.title}: 0 {self.unit}", size_hint=(None, None),
        #                    pos=(self.x + self.width / 4, self.y - 30), font_size='16sp')
        # self.add_widget(self.label)

        Clock.schedule_once(self.init_needle, 0)

    def draw_gauge(self):
        center_x, center_y = self.center
        radius = min(self.width, self.height) / 2

        # Background circle
        Color(0.1, 0.1, 0.1)
        Ellipse(pos=self.pos, size=self.size)

        # Draw ticks and numbers
        tick_count = 12
        for i in range(tick_count + 1):
            # FIX: Flip direction — low values on the left
            angle_deg = -130 + ((tick_count - i) / tick_count) * -260
            angle_rad = math.radians(angle_deg)
            inner_radius = radius * 0.8
            outer_radius = radius * 0.95

            x1 = center_x + inner_radius * math.cos(angle_rad)
            y1 = center_y + inner_radius * math.sin(angle_rad)
            x2 = center_x + outer_radius * math.cos(angle_rad)
            y2 = center_y + outer_radius * math.sin(angle_rad)

            Color(1, 1, 1)
            Line(points=[x1, y1, x2, y2], width=2)

            # Number labels
            value = int(((tick_count - i) / tick_count) * self.max_value)
            label_x = center_x + (radius * 1.20) * math.cos(angle_rad) - 48
            label_y = center_y + (radius * 1.20) * math.sin(angle_rad) - 48
            self.add_widget(Label(text=str(value), pos=(label_x, label_y), font_size='12sp'))

        # Add gauge title
        self.add_widget(Label(text=self.title, pos=(self.center_x - 30, self.y + 10), font_size='16sp'))

    def init_needle(self, *args):
        # Draw the needle
        self.center_x = self.x + self.width / 2
        self.center_y = self.y + self.height / 2
        with self.canvas:
            PushMatrix()
            self.rot = Rotate(origin=(self.center_x, self.center_y), angle=self.needle_angle)
            Color(1, 0, 0)
            self.needle = Line(points=[self.center_x, self.center_y,
                                       self.center_x, self.center_y + self.height / 2.5], width=2)
            PopMatrix()

    def update_value(self, value):
        clamped = max(0, min(value, self.max_value))
        angle = -130 + (clamped / self.max_value) * 260
        self.needle_angle = angle
        if hasattr(self, 'rot'):
            self.rot.angle = angle
        # self.label.text = f"{self.title}: {int(clamped)} {self.unit}"

class Dashboard(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.speed_gauge = Gauge(title="Speed", max_value=240, unit="km/h", size=(300, 300), pos=(50, 150))
        # self.rpm_gauge = Gauge(title="RPM", max_value=8000, unit="rpm", size=(300, 300), pos=(400, 150))

        self.add_widget(self.speed_gauge)
        # self.add_widget(self.rpm_gauge)

        Clock.schedule_interval(self.simulate_data, 0.5)

    def simulate_data(self, dt):
        speed = random.uniform(0, 240)
        rpm = random.uniform(0, 8000)

        self.speed_gauge.update_value(speed)
        # self.rpm_gauge.update_value(rpm)

class CarClusterApp(App):
    def build(self):
        return Dashboard()

if __name__ == '__main__':
    CarClusterApp().run()
