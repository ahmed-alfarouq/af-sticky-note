"""Design tokens and QSS shared by the full screens (settings, archive)."""

from __future__ import annotations

__all__ = ["get_screen_stylesheet"]

# -- Panel and nav ------------------------------------------------------------
PANEL_MARGINS = (16, 12, 16, 16)   # left, top, right, bottom (matches the paper)
PANEL_GAP = 12                     # between the nav and the blocks below it
NAV_GAP = 4
BACK_BUTTON_SIZE = 44
BACK_ICON_SIZE = 20
BACK_ICON_COLOR = "#a3aec2"
BACK_ICON_HOVER = "#ffffff"
TITLE_PX = 20

FOCUS_COLOR = "#8FB8D8"
FOCUS_WIDTH = 2

# -- Motion -------------------------------------------------------------------
OPEN_SLIDE_MS = 320                # the screen slides in from the left, home slides out
CLOSE_SLIDE_MS = 280               # and back


def get_screen_stylesheet() -> str:
    """QSS for the screen frame: its title and back button."""
    return f"""
    QWidget#screenPanel {{
        background: transparent;
        border: none;
    }}

    QLabel#screenTitle {{
        color: #ffffff;
        font-size: {TITLE_PX}px;
        font-weight: 700;
        background: transparent;
    }}

    QToolButton#screenBackButton {{
        background-color: transparent;
        border: none;
        border-radius: 12px;
    }}

    QToolButton#screenBackButton:focus {{
        border: 2px solid {FOCUS_COLOR};
        border-radius: 12px;
    }}
    """