"""Reusable value readout whose colour reflects a threshold.

Drives a value Label's text and colour from a sensor reading: the value turns
``warn_color`` when ``warn(value)`` is true, otherwise ``base_color``. The
accompanying title label is static (the caller sets it once), matching the
minimal design where only the value reacts.
"""

from theme import VALUE, WARNING


class Readout:
    def __init__(self, value_label, fmt="{:.0f}", warn=None,
                 base_color=VALUE, warn_color=WARNING):
        self.value = value_label
        self.fmt = fmt
        self.warn = warn or (lambda v: False)
        self.base_color = base_color
        self.warn_color = warn_color

    def set(self, value):
        """Update the displayed value; ``None`` leaves the readout unchanged."""
        if value is None:
            return
        self.value.text = self.fmt.format(value)
        self.value.color = self.warn_color if self.warn(value) else self.base_color
