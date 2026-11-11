"""Design tokens and QSS for the bottom option sheet."""

from __future__ import annotations

__all__ = ["get_option_sheet_stylesheet"]

# -- Overlay ----------------------------------------------------------------
OVERLAY_INSET = 16            # sheet distance from the paper edges
DIM_OPACITY = 0.7             # paper color over the content behind the sheet

# -- Sheet ------------------------------------------------------------------
SHEET_FILL = "#232d40"
SHEET_RADIUS = 22
SHEET_PAD_TOP = 10
SHEET_PAD_SIDE = 14
SHEET_PAD_BOTTOM = 14
SHEET_SPACING = 8
SHEET_SHADOW_BLUR = 24
SHEET_SHADOW_OFFSET_Y = -8
SHEET_SHADOW_ALPHA = 89       # 35% black
SHEET_OPEN_MS = 260           # slide up + dim fade in
SHEET_CLOSE_MS = 200          # slide down + dim fade out

GRABBER_WIDTH = 40
GRABBER_HEIGHT = 4
GRABBER_COLOR = "#4a5670"
GRABBER_GAP_BELOW = 6

TITLE_PX = 16
TITLE_MARGINS = (4, 2, 4, 6)  # left, top, right, bottom

# -- Option row -------------------------------------------------------------
OPTION_MIN_HEIGHT = 52
OPTION_PAD_H = 14
OPTION_GAP = 12
OPTION_RADIUS = 14
OPTION_BORDER = 1.5
OPTION_FILL = "#2a3549"
OPTION_SELECTED_FILL = "#2a3a58"
OPTION_SELECTED_BORDER = "#4f86d9"
OPTION_FOCUS_BORDER = "#8FB8D8"
OPTION_LABEL_PX = 15
OPTION_HINT_PX = 12
OPTION_HINT_COLOR = "#a3aec2"
OPTION_HINT_GAP = 1
MARKER_SIZE = 12
MARKER_SQUARE_RADIUS = 4
OPTION_ICON_SIZE = 20
CHECK_SIZE = 18
CHECK_COLOR = "#9fc2f5"


def get_option_sheet_stylesheet() -> str:
    """QSS for the sheet frame and its text."""
    return f"""
    /* Bottom option sheet (category / priority pickers). */
    QWidget#optionSheetOverlay {{
        background: transparent;
    }}

    QFrame#optionSheet {{
        background-color: {SHEET_FILL};
        border: none;
        border-radius: {SHEET_RADIUS}px;
    }}

    QFrame#optionSheetGrabber {{
        background-color: {GRABBER_COLOR};
        border: none;
        border-radius: {GRABBER_HEIGHT // 2}px;
    }}

    QLabel#optionSheetTitle {{
        color: #ffffff;
        font-size: {TITLE_PX}px;
        font-weight: 600;
        background: transparent;
    }}

    QScrollArea#optionSheetScroll,
    QWidget#optionSheetOptions {{
        background: transparent;
        border: none;
    }}

    QLabel#optionLabel {{
        color: #ffffff;
        font-size: {OPTION_LABEL_PX}px;
        background: transparent;
    }}

    QLabel#optionHint {{
        color: {OPTION_HINT_COLOR};
        font-size: {OPTION_HINT_PX}px;
        background: transparent;
    }}
    """