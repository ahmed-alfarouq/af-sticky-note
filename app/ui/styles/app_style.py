"""Centralized styling system and visual palette for Daily Sticky (Phase 4B).

Implements the project constitution palette:
- Navy:           #172033
- Trust Blue:      #4F7CAC
- Soft Blue:       #8FB8D8
- Background:      #0F141D
- Surface (Dark):  #171E29
- Sticky Paper:    #1F2838 (subtle physical paper contrast against background)
- Text Primary:    #F2F5F8
- Text Secondary:  #98A2B3
- Text Completed:  #5D6B82
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
COLOR_STICKY_PAPER = "#1B2332"
COLOR_STICKY_BORDER = "#2B374A"
COLOR_CARD_SURFACE = "#151C27"
COLOR_CARD_BORDER = "#242E3E"
COLOR_TEXT_PRIMARY = "#F2F5F8"
COLOR_TEXT_SECONDARY = "#98A2B3"
COLOR_TEXT_COMPLETED = "#5D6B82"
COLOR_BORDER = "#283241"
COLOR_SUCCESS = "#6FAF8F"
COLOR_WARNING_PIN = "#D9A441"
COLOR_INPUT_BG = "#111622"
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

    /* The Sticky Note paper container */
    QFrame#stickyNoteFrame {{
        background-color: {COLOR_STICKY_PAPER};
        border: 1px solid {COLOR_STICKY_BORDER};
        border-radius: 12px;
    }}

    /* Decorative Pin Element */
    QLabel#pinWidget {{
        background-color: {COLOR_WARNING_PIN};
        border: 2px solid #B88528;
        border-radius: 8px;
        min-width: 16px;
        max-width: 16px;
        min-height: 16px;
        max-height: 16px;
    }}

    /* Header / Date */
    QLabel#dateLabel {{
        color: {COLOR_SOFT};
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}

    /* Daily Quote Card */
    QFrame#quoteCard {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 8px;
        padding: 10px 14px;
    }}

    QLabel#quoteTextLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
        line-height: 1.5;
        font-style: italic;
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
        border: 1px solid {COLOR_BORDER};
        background-color: #18202D;
    }}

    QLabel#taskTextLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
        font-weight: 500;
    }}

    QLabel#taskTextLabelCompleted {{
        color: {COLOR_TEXT_COMPLETED};
        font-size: 14px;
        text-decoration: line-through;
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
        background-color: {COLOR_INPUT_BG};
        color: {COLOR_TEXT_PRIMARY};
        border: 1.5px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
    }}

    QLineEdit#taskInputField:hover {{
        border-color: {COLOR_STICKY_BORDER};
    }}

    QLineEdit#taskInputField:focus {{
        border: 2px solid {COLOR_FOCUS_RING};
        background-color: #141A26;
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
