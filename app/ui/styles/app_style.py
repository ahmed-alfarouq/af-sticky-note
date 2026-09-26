"""Centralized styling system and visual palette for Daily Sticky (Phase 5M).

Implements the project constitution palette:
- Navy:           #172033
- Trust Blue:      #4F7CAC
- Soft Blue:       #8FB8D8
- Background:      #0F141D
- Surface (Dark):  #171E29
- Sticky Paper:    #1E2636 (tactile physical paper contrast)
- Text Primary:    #F2F5F8
- Text Secondary:  #98A2B3
- Text Completed:  #616F85
- Border:          #283241
- Success:         #6FAF8F
- Warning / Pin:   #D9A441
"""
from __future__ import annotations

from app.infrastructure.fonts import get_default_font_family

# Palette tokens
COLOR_NAVY = "#172033"
COLOR_TRUST = "#4F7CAC"
COLOR_SOFT = "#8FB8D8"
COLOR_BACKGROUND = "#0F141D"
COLOR_SURFACE = "#171E29"
COLOR_STICKY_PAPER = "#1E2636"
COLOR_STICKY_BORDER = "#2E3A4E"
COLOR_CARD_SURFACE = "#161E2B"
COLOR_CARD_BORDER = "#242F42"
COLOR_TEXT_PRIMARY = "#F2F5F8"
COLOR_TEXT_SECONDARY = "#98A2B3"
COLOR_TEXT_COMPLETED = "#616F85"
COLOR_BORDER = "#283241"
COLOR_SUCCESS = "#6FAF8F"
COLOR_WARNING_PIN = "#D9A441"
COLOR_INPUT_BG = "#131924"
COLOR_FOCUS_RING = "#4F7CAC"


def get_application_stylesheet() -> str:
    """Return the global QSS stylesheet for the Sticky Note window and widgets."""
    font_family = get_default_font_family()

    return f"""
    /* Global Base */
    QWidget {{
        font-family: {font_family};
        color: {COLOR_TEXT_PRIMARY};
    }}

    /* Main Window background acts as the desktop/board */
    QMainWindow {{
        background-color: {COLOR_BACKGROUND};
    }}

    /* The Sticky Note paper container - tactile rounded paper surface */
    QFrame#stickyNoteFrame {{
        background-color: {COLOR_STICKY_PAPER};
        border: 1px solid {COLOR_STICKY_BORDER};
        border-radius: 14px;
    }}

    /* Decorative Pin Element - refined physical metallic pin */
    QLabel#pinWidget {{
        background: qradialgradient(cx:0.4, cy:0.4, radius:0.8, fx:0.3, fy:0.3, stop:0 #F0C466, stop:0.6 {COLOR_WARNING_PIN}, stop:1 #A36B15);
        border: 1.5px solid #82530C;
        border-radius: 8px;
        min-width: 16px;
        max-width: 16px;
        min-height: 16px;
        max-height: 16px;
    }}

    /* Top-Left Exit Button */
    QPushButton#exitButton {{
        background-color: transparent;
        color: {COLOR_TEXT_SECONDARY};
        border: none;
        border-radius: 4px;
        font-family: Arial, sans-serif;
        font-size: 13px;
        font-weight: bold;
        min-width: 22px;
        max-width: 22px;
        min-height: 22px;
        max-height: 22px;
        padding: 0px;
    }}

    QPushButton#exitButton:hover {{
        background-color: rgba(235, 87, 87, 0.22);
        color: #FF7575;
    }}

    QPushButton#exitButton:pressed {{
        background-color: rgba(235, 87, 87, 0.42);
        color: #FFA8A8;
    }}

    /* Header / Date Card */
    QLabel#dateLabel {{
        color: #8EBCE6;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.3px;
        line-height: 1.4;
        background: transparent;
    }}

    /* Daily Quote Card */
    QFrame#quoteCard {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 10px;
    }}

    QLabel#quoteTextLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 13.5px;
        font-weight: 500;
        line-height: 1.55;
        font-style: italic;
        background: transparent;
    }}

    /* Task List Scroll Area */
    QScrollArea#taskListScroll {{
        background-color: transparent;
        border: none;
    }}

    QWidget#taskListContainer {{
        background-color: transparent;
    }}

    /* Individual Task Row Frame */
    QFrame#taskItemFrame {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 8px;
        margin-top: 1px;
        margin-bottom: 1px;
    }}

    QFrame#taskItemFrame:hover {{
        border: 1px solid #334259;
        background-color: #1A2332;
    }}

    QLabel#taskTextLabel {{
        qproperty-alignment: AlignRight | AlignVCenter;
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
        font-weight: 500;
        line-height: 1.4;
    }}

    QLabel#taskTextLabelCompleted {{
        qproperty-alignment: AlignRight | AlignVCenter;
        color: {COLOR_TEXT_COMPLETED};
        font-size: 14px;
        text-decoration: line-through;
        line-height: 1.4;
    }}

    /* Priority Badges */
    QLabel#priorityBadgeHigh {{
        color: #E57373;
        background-color: rgba(229, 115, 115, 0.12);
        border: 1px solid rgba(229, 115, 115, 0.28);
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
    }}

    QLabel#priorityBadgeLow {{
        color: #81C784;
        background-color: rgba(129, 199, 132, 0.12);
        border: 1px solid rgba(129, 199, 132, 0.28);
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
    }}

    /* Checkbox Styling with clear accessible states */
    QCheckBox {{
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1.5px solid {COLOR_TEXT_SECONDARY};
        background-color: {COLOR_INPUT_BG};
    }}

    QCheckBox::indicator:hover {{
        border-color: {COLOR_SOFT};
        background-color: #18202F;
    }}

    QCheckBox::indicator:focus {{
        border: 2px solid {COLOR_FOCUS_RING};
    }}

    QCheckBox::indicator:checked {{
        background-color: {COLOR_SUCCESS};
        border-color: {COLOR_SUCCESS};
    }}

    /* Task Input Field */
    QLineEdit#taskInputField {{
        qproperty-alignment: AlignRight | AlignVCenter;
        background-color: {COLOR_INPUT_BG};
        color: {COLOR_TEXT_PRIMARY};
        border: 1.5px solid {COLOR_CARD_BORDER};
        border-radius: 8px;
        padding: 9px 14px;
        font-size: 13.5px;
    }}

    QLineEdit#taskInputField:hover {{
        border-color: #384860;
    }}

    QLineEdit#taskInputField:focus {{
        border: 2px solid {COLOR_FOCUS_RING};
        background-color: #151C28;
    }}

    /* Common Close & Action Buttons (History & Settings) */
    QPushButton#historyCloseButton {{
        background-color: {COLOR_CARD_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 6px;
        padding: 6px 18px;
        font-size: 13px;
        font-weight: 500;
    }}

    QPushButton#historyCloseButton:hover {{
        background-color: #1E2738;
        border-color: {COLOR_FOCUS_RING};
    }}

    QPushButton#historyCloseButton:pressed {{
        background-color: #141B26;
    }}

    QPushButton#historyNavButton {{
        background-color: transparent;
        color: {COLOR_TEXT_SECONDARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 5px;
        padding: 4px 10px;
        font-size: 12px;
    }}

    QPushButton#historyNavButton:hover {{
        background-color: #1E2738;
        color: {COLOR_TEXT_PRIMARY};
        border-color: {COLOR_SOFT};
    }}

    QPushButton#historyNavButton:disabled {{
        color: #4D5768;
        border-color: #1E2533;
    }}

    /* Context Menus */
    QMenu {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        background-color: transparent;
        color: {COLOR_TEXT_PRIMARY};
        padding: 6px 20px 6px 12px;
        border-radius: 4px;
        font-size: 13px;
    }}

    QMenu::item:selected {{
        background-color: #232C3D;
        color: #FFFFFF;
    }}

    QMenu::separator {{
        height: 1px;
        background: {COLOR_CARD_BORDER};
        margin: 4px 6px;
    }}

    /* Subtle scrollbar */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0px 0px 0px 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {COLOR_BORDER};
        min-height: 20px;
        border-radius: 3px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {COLOR_TEXT_SECONDARY};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """

