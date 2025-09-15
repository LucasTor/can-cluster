import os
DEV = os.environ.get('DEV', True)

if DEV:
    os.environ['KIVY_METRICS_DENSITY'] = '1'  # Default is usually 1, try 0.5 if UI is too large
    os.environ['KIVY_DPI'] = '96'             # Standard DPI

from kivy.config import Config
Config.set("graphics", "width", "1920")
Config.set("graphics", "height", "720")
Config.set('modules', 'show_fps', '1')

import os
import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import (
    Color,
    RoundedRectangle,
)
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.properties import NumericProperty


from widgets import CenterInfo, Gauge

import random

kivy.require("2.0.0")


# LabelBase.register(DEFAULT_FONT, "fonts/consolas-bold.ttf")
LabelBase.register(DEFAULT_FONT, "fonts/ShareTechMono-Regular.ttf")
from kivy.graphics import Color
from kivy.graphics import Color, RoundedRectangle


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
            font_size="64sp",
            color=(1, 0, 0, 0.0),  # hidden until visible
            halign="center",
            valign="middle",
            font_name='fonts/RobotoMono-Bold.ttf'
            # size_hint=(None, None),
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
        self.size = (450, 600)
        self._center_vert = (720 / 2) - (self.size[1] / 2)

        # rect geometry
        # self._rect.pos = (bx, self._center_vert)
        self._rect.size = (450, 600)
        self._reposition()
        # self._rect.radius = [self.corner_px]

        # label centered & wrapped
        self._label.size = self.size
        
        self._label.text_size = self._label.size
        self._label.halign = "center"
        self._label.valign = "middle"

        print(self._label.center, self._rect.pos, self._rect.size)

        # self._label.y -= self._rect.size[1] * 0.02

    def _reposition(self):
        # center horizontally
        self._rect.pos = ((Window.width - 450) / 2, self._center_vert)
        self._label.pos = ((Window.width - 450) / 2, self._center_vert)


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
        if DEV:
            Window.size = (1920 / 2, 720 / 2)
            # Clock.schedule_once(lambda x: Clock.schedule_interval(self.simulate_data, 1), 3)
        Clock.schedule_once(lambda x: self.set_triggers(), 3)

        self.shift_overlay = ShiftCenterBanner(shift_rpm=6000, blink_hz=5)
        self.add_widget(self.shift_overlay)

        # with self.canvas:
        #     Color(0, 0, 0, .2)
        #     Rectangle(pos=(0, 0), size=(1920, 720))

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
    print(Window.size)
    CarClusterApp().run()
    print(Window.size)
