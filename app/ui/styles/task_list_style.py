"""Design tokens and QSS for the task list and its special blocks."""

from __future__ import annotations

__all__ = ["get_task_list_stylesheet"]

# -- Geometry (px) ----------------------------------------------------------
LIST_ITEM_SPACING = 8

HEADER_CHEVRON_SIZE = 14
HEADER_GAP = 6                 # chevron <-> text
HEADER_PAD_V = 4
HEADER_PAD_H = 2
HEADER_TEXT_PX = 13

BANNER_RADIUS = 14
BANNER_PADDING = 14
BANNER_GAP = 12               # icon <-> text
BANNER_ICON_SIZE = 22
BANNER_TEXT_PX = 15

EMPTY_CIRCLE_SIZE = 56
EMPTY_PLUS_SIZE = 20

# -- Colors -----------------------------------------------------------------
HEADER_COLOR = "#a3aec2"
FOCUS_COLOR = "#8FB8D8"

BANNER_FILL = "#1d3530"
BANNER_BORDER = "#2f5a4d"
BANNER_TEXT_COLOR = "#b5e8d0"
BANNER_ICON_COLOR = "#6fcfa3"

EMPTY_CIRCLE_COLOR = "#4a5670"
EMPTY_PLUS_COLOR = "#7a87a0"
EMPTY_TITLE_COLOR = "#ffffff"
EMPTY_BODY_COLOR = "#a3aec2"


def get_task_list_stylesheet() -> str:
    """QSS for the list, completed header, banner, and empty state."""
    return f"""
    /* Task list: a plain transparent vertical stack. */
    QScrollArea#taskListScroll {{
        background: transparent;
        border: none;
    }}

    QWidget#taskListContainer {{
        background: transparent;
    }}

    /* "مكتملة · N" group header: flat text, no fill. */
    QLabel#completedGroupText {{
        color: {HEADER_COLOR};
        font-size: {HEADER_TEXT_PX}px;
        font-weight: 600;
        background: transparent;
    }}

    /* All-done banner (green). */
    QFrame#allDoneBanner {{
        background-color: {BANNER_FILL};
        border: 1px solid {BANNER_BORDER};
        border-radius: {BANNER_RADIUS}px;
    }}

    QLabel#allDoneText {{
        color: {BANNER_TEXT_COLOR};
        font-size: {BANNER_TEXT_PX}px;
        font-weight: 600;
        background: transparent;
    }}

    /* Empty day. */
    QLabel#emptyStateTitle {{
        color: {EMPTY_TITLE_COLOR};
        font-size: 16px;
        font-weight: 600;
        background: transparent;
    }}

    QLabel#emptyStateBody {{
        color: {EMPTY_BODY_COLOR};
        font-size: 14px;
        background: transparent;
    }}
    """
