"""Design tokens and QSS for the add-task bar (input row + picker chips)."""

from __future__ import annotations

__all__ = ["get_add_task_bar_stylesheet"]

# -- Bar --------------------------------------------------------------------
BAR_GAP = 8                    # input row <-> chips row, and chip <-> chip
LOCK_OPACITY = 0.45            # whole bar while a past day is shown

# -- Input row --------------------------------------------------------------
INPUT_HEIGHT = 52
INPUT_RADIUS = 14
INPUT_FILL = "#222b3c"
INPUT_PAD_LEFT = 14
INPUT_PAD_RIGHT = 8
INPUT_GAP = 10                 # text <-> plus button
INPUT_TEXT_PX = 14
INPUT_TEXT_COLOR = "#ffffff"
INPUT_PLACEHOLDER_COLOR = "#a3aec2"

# -- Plus button ------------------------------------------------------------
PLUS_SIZE = 36
PLUS_FILL = "#4f86d9"
PLUS_LOCKED_FILL = "#4a5670"
PLUS_GLYPH_COLOR = "#ffffff"
PLUS_GLYPH_HALF = 5.25         # half the length of each bar of the "+"
PLUS_GLYPH_STROKE = 1.5

# -- Chips ------------------------------------------------------------------
CHIP_HEIGHT = 44
CHIP_RADIUS = 12
CHIP_PAD_H = 14
CHIP_GAP = 8                   # marker <-> label
CHIP_ICON_SIZE = 16
CHIP_FILL = "#222b3c"
CHIP_TEXT_COLOR = "#c9d2e2"
CHIP_TEXT_PX = 13

FOCUS_COLOR = "#8FB8D8"
FOCUS_WIDTH = 2


def get_add_task_bar_stylesheet() -> str:
    """QSS for the input row, its text field, and the picker chips."""
    return f"""
    /* Add-task bar: flat input row with a round plus button, then chips. */
    QFrame#taskInputRow {{
        background-color: {INPUT_FILL};
        border: none;
        border-radius: {INPUT_RADIUS}px;
    }}

    QLineEdit#taskInputField {{
        background: transparent;
        border: none;
        padding: 0px;
        color: {INPUT_TEXT_COLOR};
        font-size: {INPUT_TEXT_PX}px;
        placeholder-text-color: {INPUT_PLACEHOLDER_COLOR};
    }}

    /* Picker chips (category, priority): flat pill, marker + label. */
    QWidget[pickerChip="true"] {{
        background-color: {CHIP_FILL};
        border: none;
        border-radius: {CHIP_RADIUS}px;
    }}

    QLabel#pickerChipText {{
        color: {CHIP_TEXT_COLOR};
        font-size: {CHIP_TEXT_PX}px;
        background: transparent;
    }}
    """