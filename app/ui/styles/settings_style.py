"""Design tokens and QSS for the settings screen."""

from __future__ import annotations

from app.ui.styles.screen_style import FOCUS_COLOR, FOCUS_WIDTH

__all__ = ["FOCUS_COLOR", "FOCUS_WIDTH", "get_settings_stylesheet"]

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

PANEL_GAP = 12                     # between a section's heading and its group


def get_settings_stylesheet() -> str:
    """QSS for the settings screen's rows and text."""
    return f"""
    QWidget#settingsContent,
    QScrollArea#settingsScroll {{
        background: transparent;
        border: none;
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

    QLabel#settingsRowValue[pressed="true"] {{
        color: #ffffff;
    }}
    """