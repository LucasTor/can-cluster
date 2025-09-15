from kivy.uix.widget import Widget
from kivy.graphics import (
    Color,
    Ellipse,
    Line,
    Rotate,
    PushMatrix,
    PopMatrix,
    BoxShadow,
)
from kivy.uix.label import Label
from kivy.clock import Clock

import math


class Gauge(Widget):
    def __init__(
        self,
        title="Speed",
        subtitle="",
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
            font_size="128sp",
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
        Clock.schedule_once(
            lambda _: self.update_value(max_value, update_label=False), 1
        )
        Clock.schedule_once(lambda _: self.update_value(0), 2)

    def draw_gauge(self):
        center_x, center_y = self.center
        radius = min(self.width, self.height) / 2

        Color(1, 1, 1, 1)
        self.border = Line(
            rounded_rectangle=[
                self.center_x - radius,
                self.center_y - radius,
                self.width,
                self.height,
                radius,
            ],
            width=4,
        )
        # Ellipse(pos=(self.pos[0] - radius * .015, self.pos[1] - radius * .015), size=(radius * 2.03, radius * 2.03), halign="center", valign="middle")
        Color(0.1, 0.1, 0.1)
        # botar um fade q sai do coiso do centro
        Ellipse(pos=self.pos, size=self.size)
        Color(0.2392, 0.4588, 0.6588, 1)
        BoxShadow(inset=True, pos=(self.pos[0] , self.pos[1] ), size=(radius * 2, radius * 2), halign="center", valign="middle", border_radius=(radius * 2.03, radius * 2.03, radius * 2.03, radius * 2.03), blur_radius=100)
        Color(0.1, 0.1, 0.1)
        print(self._angle_for_value(0), self._angle_for_value(self.max_value))
        Ellipse(pos=self.pos, size=self.size, angle_start=self._angle_for_value(self.max_value), angle_end=self._angle_for_value(self.max_value) + (360 - self.angle_range))
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
                    font_size="44sp",
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
                font_size="64sp",
                halign="center",
                valign="middle",
            )
        )

        self.add_widget(
            Label(
                text=self.subtitle,
                size=(self.width, 30),
                pos=(self.x, self.y + self.size[0] * 0.02),
                font_size="24sp",
                halign="center",
                valign="middle",
            )
        )

        if (
            self.redline_from
            and self.redline_from > 0
            and self.redline_from < self.max_value
        ):
            start = self._angle_for_value(self.redline_from)
            end = self._angle_for_value(self.max_value)
            # Ensure start < end for Kivy's CCW arc
            if start > end:
                start, end = end, start
            Color(1, 0, 0, 0.5)
            # Slightly inside the outer edge so it looks clean
            Line(
                circle=(center_x, center_y, radius * 0.97, start, end),
                width=10,
                cap="round",
            )

    def _angle_for_value(self, v):
        # Convert a value in [0, max_value] to screen angle (degrees),
        # matching your needle orientation (0° to the right, CCW positive; your dial spans 'angle_range').
        v = max(0, min(v, self.max_value))
        # this mirrors your update_value() math:
        return (-self.angle_range / 2.0) + (
            v / float(self.max_value)
        ) * self.angle_range

    def init_needle(self, *args):
        self.center_x = self.x + self.width / 2
        self.center_y = self.y + self.height / 2
        with self.canvas:
            PushMatrix()
            self.rot = Rotate(
                origin=(self.center_x, self.center_y), angle=self.needle_angle
            )
            Color(0.9882, 0.2471, 0.1490, 1.0)
            start_y = self.center_y + self.height / 4
            end_y = self.center_y + self.height / 2
            self.needle = Line(
                points=[self.center_x, start_y, self.center_x, end_y], width=6
            )
            PopMatrix()

    def update_value(self, value, smooth=True, update_label=True):
        clamped = max(0, min(value, self.max_value))
        self.value = clamped
        angle = -(
            (-self.angle_range / 2) + ((clamped / self.max_value) * self.angle_range)
        )
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
