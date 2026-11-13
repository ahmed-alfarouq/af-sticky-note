"""Design tokens and QSS for the settings screen."""

from __future__ import annotations

__all__ = ["get_settings_stylesheet"]

# -- Panel ------------------------------------------------------------------
PANEL_MARGINS = (16, 12, 16, 16)   # left, top, right, bottom (matches the paper)
PANEL_GAP = 12                     # between nav, sections, and inside a section

# -- Nav --------------------------------------------------------------------
NAV_GAP = 4
BACK_BUTTON_SIZE = 44
BACK_ICON_SIZE = 20
BACK_ICON_COLOR = "#a3aec2"
BACK_ICON_HOVER = "#ffffff"
TITLE_PX = 20

# -- Group and rows ---------------------------------------------------------
GROUP_FILL = "#222b3c"
GROUP_RADIUS = 14
DIVIDER_COLOR = "#2c3649"
ROW_MIN_HEIGHT = 56
ROW_PAD_H = 14
ROW_GAP = 10
ROW_TITLE_PX = 14
ROW_HINT_PX = 12
ROW_HINT_GAP = 1
VALUE_PX = 13
VALUE_GAP = 4
CHEVRON_SIZE = 16
MUTED_COLOR = "#a3aec2"

# -- Switch -----------------------------------------------------------------
SWITCH_WIDTH = 46
SWITCH_HEIGHT = 28
SWITCH_PAD = 3
SWITCH_KNOB = 22
SWITCH_SQUEEZE = 4                 # knob grows by this many px while pressed
SWITCH_OFF = "#3a4660"
SWITCH_ON = "#4f86d9"
SWITCH_KNOB_COLOR = "#ffffff"
SWITCH_MS = 200
SWITCH_PRESS_MS = 120

# -- Segmented control ------------------------------------------------------
SEG_TRACK = "#11161f"
SEG_TRACK_RADIUS = 10
SEG_PAD = 3
SEG_GAP = 2
SEG_HEIGHT = 40
SEG_PAD_H = 12
SEG_RADIUS = 8
SEG_ACTIVE = "#4f86d9"
SEG_TEXT_PX = 13
SEG_TEXT_ACTIVE = "#ffffff"
SEG_TEXT_IDLE = "#a3aec2"
SEG_MS = 240

FOCUS_COLOR = "#8FB8D8"
FOCUS_WIDTH = 2

# -- Motion -----------------------------------------------------------------
PANEL_OPEN_MS = 300
PANEL_CLOSE_MS = 220
PANEL_SLIDE_OFFSET = 48            # panel enters from the left (RTL "forward")
REVEAL_MS = 340
REVEAL_STAGGER_MS = 60
REVEAL_RISE = 16


def get_settings_stylesheet() -> str:
    """QSS for the settings screen's text and back button."""
    return f"""
    QWidget#settingsPanel,
    QWidget#settingsContent,
    QScrollArea#settingsScroll {{
        background: transparent;
        border: none;
    }}

    QLabel#settingsTitle {{
        color: #ffffff;
        font-size: {TITLE_PX}px;
        font-weight: 700;
        background: transparent;
    }}

    QLabel#settingsSection {{
        color: {MUTED_COLOR};
        font-size: 12px;
        font-weight: 600;
        background: transparent;
        padding: 6px 4px 0px 4px;
    }}

    QLabel#settingsRowTitle {{
        color: #ffffff;
        font-size: {ROW_TITLE_PX}px;
        background: transparent;
    }}

    QLabel#settingsRowHint {{
        color: {MUTED_COLOR};
        font-size: {ROW_HINT_PX}px;
        background: transparent;
    }}

    QLabel#settingsRowValue {{
        color: {MUTED_COLOR};
        font-size: {VALUE_PX}px;
        background: transparent;
    }}

    QToolButton#settingsBackButton {{
        background-color: transparent;
        border: none;
        border-radius: 12px;
    }}

    QToolButton#settingsBackButton:focus {{
        border: 2px solid {FOCUS_COLOR};
        border-radius: 12px;
    }}
    """