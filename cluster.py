import os
import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import (
    Color,
    Ellipse,
    Line,
    Rotate,
    PushMatrix,
    PopMatrix,
    RoundedRectangle,
    BoxShadow,
)
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.config import Config
from kivy.uix.gridlayout import GridLayout
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty

import math
import random

PROD = bool(os.environ.get("PROD", False))

if not PROD:
    Config.set("graphics", "fullscreen", "0")
    Config.set("graphics", "width", "1920")
    Config.set("graphics", "height", "720")

kivy.require("2.0.0")

# LabelBase.register(DEFAULT_FONT, "fonts/consolas-bold.ttf")
LabelBase.register(DEFAULT_FONT, "fonts/ShareTechMono-Regular.ttf")
from kivy.graphics import Color, Ellipse
from kivy.graphics import Color, RoundedRectangle, Line


class ShiftCenterBanner(Widget):
    """
    Plain yellow rounded rectangle with red 'SHIFT' centered.
    Appears when rpm >= shift_rpm; hidden otherwise.
    Blinks while visible. Draws in canvas.after so it sits on top.
    """

    shift_rpm = NumericProperty(7000)

    def __init__(
        self,
        shift_rpm=7000,
        width_ratio=0.36,
        height_ratio=0.18,
        corner_px=22,
        blink_hz=2.0,  # blink frequency (cycles/sec)
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.shift_rpm = shift_rpm
        self.width_ratio = width_ratio
        self.height_ratio = height_ratio
        self.corner_px = corner_px
        self.blink_hz = blink_hz

        # state
        self._visible = False
        self._blink_on = False
        self._blink_ev = None

        # graphics refs
        self._fill_col = None
        self._border_col = None
        self._rect = None
        self._border = None

        # label

        # draw on top of siblings
        with self.canvas:
            self._fill_col = Color(1, 1, 0, 0.0)  # yellow, hidden initially
            self._rect = RoundedRectangle(
                pos=(0, 0), size=(0, 0), radius=[self.corner_px]
            )

        self._label = Label(
            text="[b]SHIFT[/b]",
            markup=True,
            font_size="180sp",
            color=(1, 0, 0, 0.0),  # hidden until visible
            halign="center",
            valign="middle",
            size_hint=(None, None),
        )

        self.add_widget(self._label)

        # cover the parent
        self.bind(pos=self._layout, size=self._layout)

    # keep sized to parent (Dashboard)
    def on_parent(self, *args):
        if self.parent:
            self.size = self.parent.size
            self.pos = self.parent.pos
            self.parent.bind(size=self._sync_to_parent, pos=self._sync_to_parent)
            self._layout()

    def _sync_to_parent(self, *_):
        if self.parent:
            self.size = self.parent.size
            self.pos = self.parent.pos
            self._layout()

    def _layout(self, *_):
        pw, ph = self.width, self.height
        bw = max(80, pw * self.width_ratio)
        bh = max(60, ph * self.height_ratio)
        bx = self.x + (pw - (bw * 2)) / 2.0
        by = self.y + (ph - (bh * 3)) / 2.0

        # rect geometry
        self._rect.pos = (bx, by)
        self._rect.size = (bw * 2, bh * 3)
        self._rect.radius = [self.corner_px]

        # label centered & wrapped
        self._label.size = (bw * 2, bh * 2)
        self._label.center = (self.x + pw / 2.0, self.y + ph / 2.0)
        self._label.text_size = self._label.size
        self._label.halign = "center"
        self._label.valign = "middle"

    # --- visibility & blinking ---

    def _apply_visible(self, show: bool):
        if self._visible == show:
            return
        self._visible = show

        if show:
            # set initial "bright" state
            self._set_alpha(fill=0.95, text=1.0, border=1.0)
            self._start_blink()
        else:
            self._stop_blink()
            self._set_alpha(fill=0.0, text=0.0, border=0.0)

    def _set_alpha(self, fill: float, text: float, border: float):
        # fill (yellow)
        fr, fg, fb, _ = self._fill_col.rgba
        self._fill_col.rgba = (fr, fg, fb, fill)
        # text (red)
        self._label.color = (1, 0, 0, text)
        # border (white)
        # br, bg, bb, _ = self._border_col.rgba
        # self._border_col.rgba = (br, bg, bb, border)

    def _blink_tick(self, dt):
        # toggle between bright and dim states
        self._blink_on = not self._blink_on
        if not self._visible:
            return
        if self._blink_on:
            self._set_alpha(fill=1, text=1.0, border=1.0)
        else:
            self._set_alpha(
                fill=1, text=0.60, border=1.0
            )  # keep border steady; change if you want

    def _start_blink(self):
        if self._blink_ev is None:
            # toggle twice per cycle => schedule at half-period
            half_period = max(0.05, 0.5 / max(0.1, self.blink_hz))
            from kivy.clock import Clock

            self._blink_ev = Clock.schedule_interval(self._blink_tick, half_period)

    def _stop_blink(self):
        if self._blink_ev is not None:
            self._blink_ev.cancel()
            self._blink_ev = None
        self._blink_on = False

    # --- public API ---

    def set_rpm(self, rpm: float):
        self._apply_visible(rpm >= self.shift_rpm)

    # optional: force a one-off flash to confirm visibility
    def demo_flash(self, seconds=0.8):
        self._apply_visible(True)
        from kivy.clock import Clock

        Clock.schedule_once(lambda *_: self._apply_visible(False), seconds)


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
            font_size="48sp",
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
        # BoxShadow(pos=(self.pos[0] + radius * .05, self.pos[1] + radius * .05), size=(radius * 1.9, radius * 1.9), halign="center", valign="middle", border_radius=(radius * 2.03, radius * 2.03, radius * 2.03, radius * 2.03), blur_radius=50)
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
                    font_size="24sp",
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
                font_size="32sp",
                halign="center",
                valign="middle",
            )
        )

        self.add_widget(
            Label(
                text=self.subtitle,
                size=(self.width, 30),
                pos=(self.x, self.y + self.size[0] * 0.04),
                font_size="12sp",
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
            Color(0.012, 0.337, 0.988, 1)
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
                font_size="20sp",
                halign="left",
                valign="middle",
                size_hint=(1, None),
                height=40,
            )
            val = Label(
                text="—",
                font_size="20sp",
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
            font_size="22sp",
            padding=[0, 0, 0, 32],
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=30,
        )
        self.boost_box.add_widget(self.big_boost_title)
        self.big_boost_value = Label(
            text="0.00", font_size="80sp", bold=True, halign="center", valign="middle"
        )
        self.big_boost_value.bind(size=self.big_boost_value.setter("text_size"))
        self.boost_box.add_widget(self.big_boost_value)

        # LAMBDA big tile
        self.lambda_box = BoxLayout(orientation="vertical", padding=[10, 10, 10, 10])
        self.big.add_widget(self.lambda_box)
        self.big_lambda_title = Label(
            text="[b]LAMBDA[/b]",
            markup=True,
            font_size="22sp",
            padding=[0, 0, 0, 32],
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=30,
        )
        self.lambda_box.add_widget(self.big_lambda_title)
        self.big_lambda_value = Label(
            text="1.00", font_size="80sp", bold=True, halign="center", valign="middle"
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


class Dashboard(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.accelerating = False
        self.speed = 0
        self.rpm = 1000

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
            # Clock.schedule_once(lambda x: Clock.schedule_interval(self.simulate_data, 1), 3)
            Clock.schedule_once(lambda x: self.set_triggers(), 3)

        self.shift_overlay = ShiftCenterBanner(shift_rpm=6000, blink_hz=5)
        self.add_widget(self.shift_overlay)

        Clock.schedule_once(lambda *_: self.shift_overlay.demo_flash(1.0), 0.5)

    def set_triggers(self):
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)

        Clock.schedule_interval(self.update_gauges, 1 / 30)

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
        self.shift_overlay.set_rpm(self.rpm)
        self.center_info.set_values(
            intake_c=intake_c,
            water_c=water_c,
            oil_press_bar=oil_press_bar,
            lambda_val=lambda_val,
            boost_bar=boost_bar,
        )

    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        # Key 273 = up arrow; change as needed (e.g., 119 for 'w')
        if key == 273:
            self.accelerating = True

    def on_key_up(self, window, key, scancode):
        if key == 273:
            self.accelerating = False

    def update_gauges(self, dt):
        if self.accelerating:
            self.speed += 60 * dt  # e.g., accelerate at 60 km/h per second
            self.rpm += 3000 * dt  # increase RPM
        else:
            self.speed -= 30 * dt  # slow down
            self.rpm -= 2000 * dt

        # Clamp values
        self.speed = max(0, min(self.speed, 240))
        self.rpm = max(1000, min(self.rpm, 8000))

        self.speed_gauge.update_value(self.speed)
        self.rpm_gauge.update_value(self.rpm)
        self.shift_overlay.set_rpm(self.rpm)  # <--- add this
        import random

        # You can fake some center info too
        self.center_info.set_values(
            intake_c=30 + self.speed / 10,
            water_c=85 + (self.rpm - 1000) / 1000,
            oil_press_bar=1.5 + (self.rpm / 8000) * 3.5,
            lambda_val=random.uniform(0.9, 0.99),
            boost_bar=(self.rpm - 1000) / 7000 * 1.5,
        )


class CarClusterApp(App):
    def build(self):
        return Dashboard()


if __name__ == "__main__":
    CarClusterApp().run()
    print(Window.size)
