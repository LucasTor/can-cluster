"""Reusable title + value readout whose colour flips to a warning colour.

Used by ``CenterInfo`` for both the compact rows and the big tiles. The Label
widgets are owned by the caller; ``Readout`` only drives their text and colour
so the "format a value, turn it red past a threshold" pattern lives in one
place instead of being re-implemented per field.
"""

from theme import FG, WARNING


class Readout:
    def __init__(self, title_label, value_label, fmt="{:.0f}", warn=None):
        self.title = title_label
        self.value = value_label
        self.fmt = fmt
        self.warn = warn or (lambda v: False)

    def set(self, value):
        """Update the displayed value; ``None`` leaves the readout unchanged."""
        if value is None:
            return
        self.value.text = self.fmt.format(value)
        color = WARNING if self.warn(value) else FG
        self.value.color = color
        self.title.color = color
