"""Design tokens and QSS for the archive screens."""

from __future__ import annotations

__all__ = ["get_archive_stylesheet"]

MUTED = "#a3aec2"

# -- Cards ---------------------------------------------------------------------
CARD_FILL = "#222b3c"
CARD_RADIUS = 16
CARD_PAD = 12
CARD_GAP = 8                    # between the parts of the day card
PROGRESS_GAP = 12               # ring <-> its texts
BLOCK_GAP = 12                  # between cards and sections
LIST_GAP = 8                    # between task rows

# -- Day card ------------------------------------------------------------------
NAV_BUTTON_HEIGHT = 48
NAV_BUTTON_FILL = "#2a3549"
NAV_BUTTON_FILL_OFF = "#232b3b"
NAV_BUTTON_TEXT_OFF = "#5c6578"
NAV_BUTTON_ICON = 16
DATE_PRIMARY_PX = 16
DATE_SECONDARY_PX = 12
RING_SIZE = 48
PROGRESS_TITLE_PX = 15
PROGRESS_SUB_PX = 12

# -- Chip ("اختيار يوم") --------------------------------------------------------
CHIP_HEIGHT = 44
CHIP_PAD = 12
CHIP_GAP = 6
CHIP_RADIUS = 12
CHIP_ICON = 16
CHIP_PX = 13
CHIP_FILL = "#222b3c"
CHIP_FILL_ON = "#2a3a58"
CHIP_BORDER_ON = "#4f86d9"
CHIP_BORDER_WIDTH = 1.5
CHIP_TEXT = "#c9d2e2"
CHIP_TEXT_ON = "#ffffff"

# -- Task row badges -------------------------------------------------------------
BADGE_SIZE = 28
BADGE_FILL = "#1a2130"
BADGE_RADIUS = 8
BADGE_ICON = 16

# -- Calendar grid ---------------------------------------------------------------
GRID_COLUMNS = 7
GRID_GAP = 6
CELL_HEIGHT = 44
CELL_RADIUS = 11
CELL_FILL = "#2a3549"
CELL_SELECTED_FILL = "#4f86d9"
CELL_TEXT = "#ffffff"
CELL_TEXT_OFF = "#4a5670"
CELL_DAY_PX = 15
TODAY_RING = "#4a5670"
TODAY_RING_WIDTH = 1.5
WEEKDAY_PX = 11
WEEKDAY_HEIGHT = 24
MONTH_TITLE_PX = 16

# -- Go button ------------------------------------------------------------------
GO_HEIGHT = 48
GO_RADIUS = 14
GO_FILL = "#4f86d9"
GO_FILL_OFF = "#2a3549"
GO_TEXT_OFF = "#5c6578"


def get_archive_stylesheet() -> str:
    """QSS for the archive screens' cards, buttons, and text."""
    return f"""
    QWidget#archiveRows,
    QScrollArea#archiveScroll {{
        background: transparent;
        border: none;
    }}

    QFrame#archiveCard {{
        background-color: {CARD_FILL};
        border: none;
        border-radius: {CARD_RADIUS}px;
    }}

    QPushButton#archiveNavButton {{
        background-color: {NAV_BUTTON_FILL};
        color: #ffffff;
        border: none;
        border-radius: 12px;
        padding: 0px 12px;
        min-height: {NAV_BUTTON_HEIGHT}px;
        font-size: 13px;
    }}

    QPushButton#archiveNavButton:disabled {{
        background-color: {NAV_BUTTON_FILL_OFF};
        color: {NAV_BUTTON_TEXT_OFF};
    }}

    QPushButton#archiveNavButton:focus {{
        border: 2px solid #8FB8D8;
    }}

    QLabel#archiveDatePrimary {{
        color: #ffffff;
        font-size: {DATE_PRIMARY_PX}px;
        font-weight: 700;
        background: transparent;
    }}

    QLabel#archiveDateSecondary {{
        color: {MUTED};
        font-size: {DATE_SECONDARY_PX}px;
        background: transparent;
    }}

    QLabel#archiveProgressTitle {{
        color: #ffffff;
        font-size: {PROGRESS_TITLE_PX}px;
        font-weight: 600;
        background: transparent;
    }}

    QLabel#archiveProgressSub {{
        color: {MUTED};
        font-size: {PROGRESS_SUB_PX}px;
        background: transparent;
    }}

    QLabel#archiveSection {{
        color: {MUTED};
        font-size: 12px;
        font-weight: 600;
        background: transparent;
        padding: 6px 4px 0px 4px;
    }}

    QLabel#archiveMonthTitle {{
        color: #ffffff;
        font-size: {MONTH_TITLE_PX}px;
        font-weight: 700;
        background: transparent;
    }}

    QPushButton#archiveGoButton {{
        background-color: {GO_FILL};
        color: #ffffff;
        border: none;
        border-radius: {GO_RADIUS}px;
        min-height: {GO_HEIGHT}px;
        font-size: 15px;
        font-weight: 600;
    }}

    QPushButton#archiveGoButton:disabled {{
        background-color: {GO_FILL_OFF};
        color: {GO_TEXT_OFF};
    }}

    QPushButton#archiveGoButton:focus {{
        border: 2px solid #8FB8D8;
    }}
    """