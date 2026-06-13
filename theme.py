"""Centralised colour palette and layout constants for the cluster UI.

Every widget pulls its colours and shared dimensions from here so the whole
cluster can be restyled in one place and the two centre-aligned widgets
(``CenterInfo`` and ``ShiftCenterBanner``) can't drift out of sync.
"""

# --- Colours (RGBA, 0..1) ---
ACCENT = (0.2392, 0.4588, 0.6588, 1.0)   # card / dial accent blue
FG = (1.0, 1.0, 1.0, 1.0)                # default foreground / text
WARNING = (1.0, 0.0, 0.0, 1.0)           # over-threshold red
DARK = (0.1, 0.1, 0.1, 1.0)              # dial face / inactive fill
NEEDLE = (0.9882, 0.2471, 0.1490, 1.0)   # gauge needle
INDICATOR_ON = (0.0, 1.0, 0.0, 1.0)      # turn indicator active (green)
INDICATOR_OFF = (0.1, 0.1, 0.1, 1.0)     # turn indicator inactive
SHIFT_FILL = (1.0, 1.0, 0.0, 1.0)        # shift banner background (yellow)
SHIFT_TEXT = (1.0, 0.0, 0.0, 1.0)        # shift banner text (red)
REDLINE = (1.0, 0.0, 0.0, 0.5)           # gauge redline arc

# --- Window ---
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 720

# --- Centre card (engine info + shift banner share these) ---
CARD_WIDTH = 450
CARD_HEIGHT = 600
CARD_RADIUS = 20
