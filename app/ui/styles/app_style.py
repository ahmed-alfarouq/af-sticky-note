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

    /* The window itself must stay fully transparent: the paper silhouette
       (rounded top corners + organic bottom edge) is painted by PaperSurface
       along a shared path, and the window mask is derived from that same
       path. Any background painted here would show up as a rectangle
       outside the paper and would defeat both the mask and the
       anti-aliased edge. */
    QMainWindow {{
        background: transparent;
    }}

    /* The Sticky Note paper surface. Its silhouette and border are painted
       by PaperSurface from app/ui/note_shape.py, so no rectangular
       background, border or border-radius belongs here. */
    QFrame#stickyNoteFrame {{
        background: transparent;
        border: none;
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

    /* Top-Left Action Buttons (Settings, History, Exit) */
    QPushButton#headerIconButton {{
        background-color: transparent;
        color: {COLOR_TEXT_SECONDARY};
        border: none;
        border-radius: 4px;
        font-family: Arial, "Segoe UI", sans-serif;
        font-size: 13px;
        font-weight: normal;
        min-width: 22px;
        max-width: 22px;
        min-height: 22px;
        max-height: 22px;
        padding: 0px;
    }}

    QPushButton#headerIconButton:hover {{
        background-color: rgba(79, 124, 172, 0.22);
        color: {COLOR_SOFT};
    }}

    QPushButton#headerIconButton:pressed {{
        background-color: rgba(79, 124, 172, 0.42);
        color: #FFFFFF;
    }}

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
        /* Keep this value an integer number of pixels: Qt's QSS parser
           silently discards a fractional font-size (13.5px renders at the
           platform default, ~9pt) and emits no warning at all
           (tests/test_app_stylesheet.py). */
        font-size: 13px;
        color: {COLOR_TEXT_PRIMARY};
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
        /* Keep this value quoted: an unquoted pipe makes Qt's QSS parser
           discard this entire stylesheet (tests/test_app_stylesheet.py). */
        qproperty-alignment: 'AlignRight | AlignVCenter';
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
        font-weight: 500;
        line-height: 1.4;
    }}

    QLabel#taskTextLabelCompleted {{
        /* Keep this value quoted: an unquoted pipe makes Qt's QSS parser
           discard this entire stylesheet (tests/test_app_stylesheet.py). */
        qproperty-alignment: 'AlignRight | AlignVCenter';
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

    /* Priority Selector (new-task row + edit dialog).
       Deliberately compact and quiet: it must not compete with the task text.
       The drop-down arrow is hidden because the combo is small and the value
       is short; the whole control is still clickable and keyboard reachable. */
    QComboBox#prioritySelector {{
        background-color: {COLOR_INPUT_BG};
        color: {COLOR_TEXT_SECONDARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 5px;
        padding: 4px 8px;
        font-size: 12px;
        /* Qt reads min-width / max-width as the *content* width and then adds
           this rule's padding and border, so the laid-out control is ~18px
           wider than the numbers below. The QSizePolicy.Maximum +
           AdjustToContents set in PrioritySelector are what actually keep the
           control compact; these are only outer bounds. */
        min-width: 68px;
        max-width: 92px;
    }}

    QComboBox#prioritySelector:hover {{
        border-color: {COLOR_BORDER};
        color: {COLOR_TEXT_PRIMARY};
    }}

    QComboBox#prioritySelector:focus {{
        border: 2px solid {COLOR_FOCUS_RING};
    }}

    QComboBox#prioritySelector::drop-down {{
        border: none;
        width: 14px;
        subcontrol-origin: padding;
        subcontrol-position: center left;
    }}

    QComboBox#prioritySelector::down-arrow {{
        image: none;
        width: 0px;
        height: 0px;
    }}

    /* The popup is a separate top-level window, so it needs its own
       rules; the context-menu priority submenu inherits the global QMenu
       styling below. */
    QComboBox#prioritySelector QAbstractItemView {{
        background-color: {COLOR_CARD_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 5px;
        padding: 4px;
        outline: none;
    }}

    QComboBox#prioritySelector QAbstractItemView::item {{
        padding: 5px 8px;
        border-radius: 4px;
        min-height: 22px;
    }}

    QComboBox#prioritySelector QAbstractItemView::item:selected {{
        background-color: rgba(79, 124, 172, 0.28);
        color: {COLOR_TEXT_PRIMARY};
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
        /* Keep this value quoted: an unquoted pipe makes Qt's QSS parser
           discard this entire stylesheet (tests/test_app_stylesheet.py). */
        qproperty-alignment: 'AlignRight | AlignVCenter';
        /* Keep this value an integer number of pixels: Qt's QSS parser
           silently discards a fractional font-size (13.5px renders at the
           platform default, ~9pt) and emits no warning at all
           (tests/test_app_stylesheet.py). The typed task text must not be
           smaller than the same text once it becomes a task row. */
        font-size: 13px;
        background-color: {COLOR_INPUT_BG};
        color: {COLOR_TEXT_PRIMARY};
        border: 1.5px solid {COLOR_CARD_BORDER};
        border-radius: 8px;
        padding: 9px 14px;
    }}

    QLineEdit#taskInputField:hover {{
        border-color: {COLOR_BORDER};
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

    /* History window: the dual-calendar date and the progress summary are the
       two most informative lines in the window. They carry object names but
       had no rules, so they rendered at the platform default size while every
       neighbouring control used 12-13px. */
    QLabel#historyDualDate {{
        color: {COLOR_SOFT};
        font-size: 13px;
        font-weight: 600;
        background: transparent;
    }}

    QLabel#historyStatsLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 500;
        background: transparent;
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

    /* Task edit dialog (Phase 6E). These three object names were set in code
       but had no rules, so the dialog's field labels and both action buttons
       fell back to platform-default Qt widgets. Save is the primary action
       and uses the palette's trust blue; Cancel stays neutral like the other
       dialog close buttons. */
    QLabel#taskEditLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 13px;
        font-weight: 500;
        background: transparent;
    }}

    QPushButton#saveButton {{
        background-color: {COLOR_TRUST};
        color: #FFFFFF;
        border: 1px solid {COLOR_TRUST};
        border-radius: 6px;
        padding: 6px 18px;
        font-size: 13px;
        font-weight: 600;
    }}

    QPushButton#saveButton:hover {{
        background-color: #5D8DBE;
        border-color: #5D8DBE;
    }}

    QPushButton#saveButton:pressed {{
        background-color: #436E9B;
        border-color: #436E9B;
    }}

    QPushButton#cancelButton {{
        background-color: {COLOR_CARD_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 6px;
        padding: 6px 18px;
        font-size: 13px;
        font-weight: 500;
    }}

    QPushButton#cancelButton:hover {{
        background-color: #1E2738;
        border-color: {COLOR_FOCUS_RING};
    }}

    QPushButton#cancelButton:pressed {{
        background-color: #141B26;
    }}

    /* Settings window: the startup checkbox text had no rule, so it rendered
       at the platform default size next to a 13px app title. The indicator
       itself is already covered by the generic QCheckBox rules above. */
    QCheckBox#startupCheckbox {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 13px;
        font-weight: 500;
    }}
    """

