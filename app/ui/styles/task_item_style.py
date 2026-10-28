"""Design tokens and QSS for the task row (see ``widgets/task_item``)."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

__all__ = ["get_task_item_stylesheet", "repolish"]

# -- Geometry (px) ----------------------------------------------------------
ROW_MIN_HEIGHT = 56
ROW_RADIUS = 14
ROW_PADDING_V = 10
ROW_PADDING_H = 14
ROW_CONTENT_GAP = 12          # checkbox <-> text block
META_TOP_GAP = 2              # title <-> meta line
META_DOT_SIZE = 8
META_DOT_GAP = 6              # dot <-> meta text

CHECKBOX_SIZE = 28
CHECKBOX_OUTLINE = 2
CHECK_ICON_SIZE = 16
CHECK_STROKE = 3

TITLE_PX = 15
META_PX = 12

# -- Colors -----------------------------------------------------------------
ROW_FILL = "#222b3c"
TITLE_COLOR = "#ffffff"
MUTED_COLOR = "#a3aec2"
WARNING_COLOR = "#f0b24a"
FOCUS_COLOR = "#8FB8D8"

CHECK_OUTLINE_COLOR = "#7a87a0"
CHECK_DONE_FILL = "#6fcfa3"
CHECK_DONE_MARK = "#12301f"
CHECK_PAST_COLOR = "#4a5670"
CHECK_PAST_OPEN_OPACITY = 0.7
CHECK_PAST_MARK = ROW_FILL

PRIORITY_URGENT_COLOR = "#f08a6c"
PRIORITY_NORMAL_COLOR = "#5b8fd6"
PRIORITY_LOW_COLOR = "#8f9bb0"


def repolish(widget: QWidget) -> None:
    """Re-evaluate QSS after a dynamic property or object-name change."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def get_task_item_stylesheet() -> str:
    """QSS for the task row, to be included in the application stylesheet."""
    return f"""
    /* Task row: flat dark-slate card, no border, no shadow, no hover. */
    QFrame#taskItemFrame {{
        background-color: {ROW_FILL};
        border: none;
        border-radius: {ROW_RADIUS}px;
    }}

    QLabel#taskTitle {{
        color: {TITLE_COLOR};
        background: transparent;
    }}

    QLabel#taskTitle[muted="true"] {{
        color: {MUTED_COLOR};
    }}

    QLabel#taskTitle:focus {{
        border: 2px solid {FOCUS_COLOR};
        border-radius: 4px;
    }}

    QLabel#taskMetaText {{
        color: {MUTED_COLOR};
        background: transparent;
    }}

    QLabel#taskMetaText[tone="warning"] {{
        color: {WARNING_COLOR};
    }}

    /* Inline title edit field. */
    QLineEdit#taskTitleEdit {{
        background-color: #0F141D;
        color: {TITLE_COLOR};
        font-size: {TITLE_PX}px;
        border: 1px solid #4F7CAC;
        border-radius: 8px;
        padding: 0px 8px;
    }}

    QLineEdit#taskTitleEdit:focus {{
        border: 2px solid {FOCUS_COLOR};
    }}
    """