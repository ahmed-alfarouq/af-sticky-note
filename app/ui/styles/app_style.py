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
from app.ui import theme

# Palette tokens: names matching the v3 spec are aliases of app.ui.theme
# (the single source of truth). The remaining names are pre-v3 legacy
# surfaces kept byte-identical until their owning widget phases reconcile
# them against the spec palette; they live only here, never duplicated.
COLOR_NAVY = "#172033"
COLOR_TRUST = theme.TRUST
COLOR_SOFT = theme.SOFT
COLOR_BACKGROUND = theme.BG
COLOR_SURFACE = theme.SURFACE
COLOR_STICKY_PAPER = "#1E2636"
COLOR_STICKY_BORDER = "#2E3A4E"
COLOR_CARD_SURFACE = "#161E2B"
COLOR_CARD_BORDER = "#242F42"
COLOR_TEXT_PRIMARY = theme.TEXT
COLOR_TEXT_SECONDARY = theme.TEXT_SECONDARY
COLOR_TEXT_COMPLETED = "#616F85"
COLOR_BORDER = theme.BORDER
COLOR_SUCCESS = theme.SUCCESS
COLOR_WARNING_PIN = theme.AMBER
COLOR_URGENT = theme.AMBER_RED
COLOR_INPUT_BG = "#131924"
COLOR_FOCUS_RING = theme.TRUST


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

    /* Top bar (v3 §4): pin toggle, drag grip, archive/settings/close.
       Icon colors are picked in code (IconButton); backgrounds live here. */
    QToolButton#pinButton {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
    }}

    QToolButton#pinButton[active="true"] {{
        background-color: rgba(217, 164, 65, 0.12);
    }}

    QToolButton#pinButton[active="true"]:hover {{
        background-color: rgba(217, 164, 65, 0.18);
    }}

    QToolButton#pinButton[active="true"]:pressed {{
        background-color: rgba(217, 164, 65, 0.24);
    }}

    QToolButton#pinButton:focus {{
        border: 2px solid #8FB8D8;
        border-radius: 8px;
    }}

    QLabel#gripPill {{
        background-color: #283241;
        border-radius: 2px;
        min-width: 32px;
        max-width: 32px;
        min-height: 4px;
        max-height: 4px;
    }}

    QToolButton#headerIconButton {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
    }}

    QToolButton#headerIconButton:hover {{
        background-color: #171E29;
    }}

    QToolButton#headerIconButton:pressed {{
        background-color: #1c2533;
    }}

    QToolButton#headerIconButton:disabled {{
        background-color: transparent;
    }}

    QToolButton#headerIconButton:focus {{
        border: 2px solid #8FB8D8;
        border-radius: 8px;
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

    /* Daily Quote Card (history/settings windows) */
    QFrame#quoteCard {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 10px;
    }}

    /* Date header block (Phase 7D): one coherent visual unit. The Hijri day
    number dominates the hero row, the Hijri month/year steps down beside it,
    and the Gregorian row closes the block. All sizes are integers (see note
    above). */
    QFrame#dateHeader {{
        background-color: transparent;
        border: none;
    }}

    QLabel#dayNumber {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 72px;
        font-weight: bold;
        background: transparent;
    }}

    QLabel#hijriDateLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 20px;
        font-weight: bold;
    }}

    QLabel#gregorianDateLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 15px;
        font-weight: normal;
        background: transparent;
    }}

    QWidget#progressRing {{
        background: transparent;
    }}

    /* Quiet quote section (Phase 7D): no card, secondary text, clearly
    below the date in the hierarchy but still readable. */
    QFrame#quoteSection {{
        background-color: transparent;
        border: none;
    }}

    QLabel#quoteRule {{
        background-color: {COLOR_TRUST};
        border: none;
    }}

    QLabel#quoteTextLabel {{
        /* Keep this value an integer number of pixels: Qt's QSS parser
           silently discards a fractional font-size (13.5px renders at the
           platform default, ~9pt) and emits no warning at all
           (tests/test_app_stylesheet.py). */
        font-size: 14px;
        color: {COLOR_TEXT_SECONDARY};
        font-weight: normal;
        line-height: 27px;
        background: transparent;
    }}

    /* Completed-group header button (v3 §7.7): collapsible, session-only. */
    QPushButton#completedGroupHeader {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 12px;
        font-weight: bold;
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 0px 12px;
        text-align: right;
    }}

    /* Empty-day and all-done states (v3 §7.1). */
    QLabel#emptyStateTitle {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 16px;
        font-weight: bold;
        background: transparent;
    }}

    QLabel#emptyStateBody {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 14px;
        background: transparent;
    }}

    QPushButton#completedGroupHeader:hover {{
        background-color: {COLOR_SURFACE};
    }}

    QPushButton#completedGroupHeader:focus {{
        border: 2px solid {COLOR_SOFT};
        border-radius: 8px;
    }}

    /* Inline title edit field (v3 §7.4). */
    QLineEdit#taskTitleEdit {{
        background-color: {COLOR_BACKGROUND};
        color: {COLOR_TEXT_PRIMARY};
        font-size: 16px;
        border: 1px solid {COLOR_TRUST};
        border-radius: 8px;
        padding: 0px 8px;
    }}

    QLineEdit#taskTitleEdit:focus {{
        border: 2px solid {COLOR_SOFT};
        border-radius: 8px;
    }}

    QLabel#taskTextLabel:focus {{
        border: 2px solid {COLOR_SOFT};
        border-radius: 4px;
    }}

    QLabel#taskTextLabelCompleted:focus {{
        border: 2px solid {COLOR_SOFT};
        border-radius: 4px;
    }}

    /* Hover-revealed row delete control (v3 §7.6). */
    QToolButton#rowDeleteButton {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
    }}

    QToolButton#rowDeleteButton:hover {{
        background-color: #1c2533;
    }}

    QToolButton#rowDeleteButton:focus {{
        border: 2px solid {COLOR_SOFT};
        border-radius: 8px;
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
        text-align: right;
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
        font-size: 16px;
        font-weight: normal;
        line-height: 1.4;
    }}

    QLabel#taskTextLabelCompleted {{
        /* Keep this value quoted: an unquoted pipe makes Qt's QSS parser
           discard this entire stylesheet (tests/test_app_stylesheet.py). */
        qproperty-alignment: 'AlignRight | AlignVCenter';
        color: {COLOR_TEXT_COMPLETED};
        font-size: 16px;
        font-weight: normal;
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

    /* Task-row metadata (Phase 7C): icon-only, secondary to the text.
    The row is: [completion] [expanding text] [category icon] [priority dot]
    in RTL order. Both indicators live in fixed-size boxes set in code so
    rows never resize between priorities, categories, or states. */
    QLabel#taskCategoryIcon {{
        background-color: transparent;
        border: none;
    }}

    /* Priority dots (approved R-rows-c mapping): HIGH is a solid
    amber-red dot, LOW a hollow amber ring, MEDIUM paints nothing (the
    fixed 12px box is kept so rows never shift). Completed rows mute every
    dot to the quiet gray. */
    QLabel#priorityDotHigh {{
        background-color: {COLOR_URGENT};
        border-radius: 6px;
    }}

    QLabel#priorityDotMedium {{
        background-color: transparent;
        border: none;
    }}

    QLabel#priorityDotLow {{
        background-color: transparent;
        border: 2px solid {COLOR_WARNING_PIN};
        border-radius: 6px;
    }}

    /* Completed rows mute every dot to the quiet gray. */
    QLabel#priorityDotHigh[completed="true"],
    QLabel#priorityDotMedium[completed="true"],
    QLabel#priorityDotLow[completed="true"] {{
        background-color: {COLOR_TEXT_COMPLETED};
        border: none;
        border-radius: 6px;
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

    /* Category selector: same compact quiet combo as the priority selector,
    slightly wider bounds for icon + Arabic name. No new colours. */
    QComboBox#categorySelector {{
        background-color: {COLOR_INPUT_BG};
        color: {COLOR_TEXT_SECONDARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 5px;
        padding: 4px 8px;
        font-size: 12px;
        min-width: 84px;
        max-width: 130px;
    }}

    QComboBox#categorySelector:hover {{
        border-color: {COLOR_BORDER};
        color: {COLOR_TEXT_PRIMARY};
    }}

    QComboBox#categorySelector:focus {{
        border: 2px solid {COLOR_FOCUS_RING};
    }}

    QComboBox#categorySelector::drop-down {{
        border: none;
        width: 14px;
        subcontrol-origin: padding;
        subcontrol-position: center left;
    }}

    QComboBox#categorySelector::down-arrow {{
        image: none;
        width: 0px;
        height: 0px;
    }}

    QComboBox#categorySelector QAbstractItemView {{
        background-color: {COLOR_CARD_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 5px;
        padding: 4px;
        outline: none;
    }}

    QComboBox#categorySelector QAbstractItemView::item {{
        padding: 5px 8px;
        border-radius: 4px;
        min-height: 22px;
    }}

    QComboBox#categorySelector QAbstractItemView::item:selected {{
        background-color: rgba(79, 124, 172, 0.28);
        color: {COLOR_TEXT_PRIMARY};
    }}

    /* Dock category chip (v3 §8.2): tag + label + caret, opens the custom
    dropdown (§9). State backgrounds mirror the chip table; the open/hover
    states are code-driven properties (see CategoryChip). */
    QWidget#categoryChip {{
        background-color: transparent;
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
    }}

    QWidget#categoryChip[hover="true"] {{
        background-color: {COLOR_SURFACE};
    }}

    QWidget#categoryChip[open="true"] {{
        background-color: {COLOR_SURFACE};
    }}

    QWidget#categoryChip[focused="true"] {{
        border: 2px solid {COLOR_SOFT};
        border-radius: 8px;
    }}

    /* Custom category popup (v3 §9): transparent shadow margin + panel. */
    QWidget#categoryPopup {{
        background: transparent;
        border: none;
    }}

    QFrame#categoryPopupPanel {{
        background-color: #1c2533;
        border: 1px solid {COLOR_BORDER};
        border-radius: 12px;
    }}

    QListWidget#categoryPopupList {{
        background: transparent;
        border: none;
        outline: none;
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
    }}

    QListWidget#categoryPopupList::item {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 0px 12px;
        color: {COLOR_TEXT_PRIMARY};
    }}

    QListWidget#categoryPopupList::item:hover {{
        background-color: {COLOR_BORDER};
    }}

    QListWidget#categoryPopupList::item:selected {{
        background-color: {COLOR_BORDER};
    }}

    /* Bottom input dock (Phase 7C): one cohesive card holding the priority
    selector, category selector, text field, and add button. Children drop
    their individual card chrome inside the dock only (contextual rules);
    elsewhere they keep the standalone styling above. */
    QFrame#taskInputDock {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 10px;
    }}

    /* Bottom input dock (Phase 7H): a transparent wrapper holding the
    input card plus the two standalone selectors. The card carries the
    dock chrome; selectors keep compact stock-like styling with a modest
    gap and no wrapper container. The top divider (v3 §8) separates the
    dock from the task list. */
    QFrame#taskInputDock {{
        background-color: transparent;
        border: none;
        border-top: 1px solid {COLOR_BORDER};
    }}

    QFrame#taskInputCard {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 10px;
    }}

    QFrame#taskInputDock QComboBox#prioritySelector,
    QFrame#taskInputDock QComboBox#categorySelector {{
        background-color: {COLOR_INPUT_BG};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 6px;
        min-width: 0px;
        padding: 2px 6px;
    }}

    QFrame#taskInputDock QLineEdit#taskInputField {{
        background-color: transparent;
        border: none;
        padding: 6px 4px;
    }}

    QFrame#taskInputDock QLineEdit#taskInputField:focus {{
        border: none;
    }}

    QPushButton#taskAddButton {{
        background-color: {COLOR_FOCUS_RING};
        color: #FFFFFF;
        border: none;
        border-radius: 11px;
        font-size: 16px;
        font-weight: 700;
        min-width: 22px;
        max-width: 22px;
        min-height: 22px;
        max-height: 22px;
        padding: 0px;
    }}

    QPushButton#taskAddButton:hover {{
        background-color: #5D8DBE;
    }}

    QPushButton#taskAddButton:pressed {{
        background-color: #436E9B;
    }}

    QPushButton#taskAddButton:disabled {{
        background-color: #283241;
        color: #6b778a;
    }}

    QPushButton#taskAddButton:focus {{
        border: 2px solid {COLOR_SOFT};
        border-radius: 11px;
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

    /* Completion must not recolor the row border (Issue 7): checked and
    unchecked indicators share border/background; only the artwork differs
    (per-checkbox override in TaskItem from the real right-icon asset). */
    QCheckBox::indicator:checked {{
        background-color: {COLOR_INPUT_BG};
        border-color: {COLOR_TEXT_SECONDARY};
        image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path fill='white' d='M3 6l2 2 4-4'/></svg>");
    }}

    QCheckBox::indicator:checked:hover {{
        background-color: #18202F;
        border-color: {COLOR_TEXT_SECONDARY};
    }}

    QCheckBox::indicator:checked:focus {{
        border: 2px solid {COLOR_FOCUS_RING};
    }}

    /* Task-row completion control (Issue 7): the native indicator box is
    collapsed to zero and the real 16px asset is shown as the button icon
    instead (see TaskItem). The border therefore cannot change color on
    check; only keyboard focus draws a ring. Other checkboxes (settings)
    keep the standard indicator styling above. */
    QCheckBox#taskCheckBox {{
        spacing: 0px;
        padding-left: 8px;
    }}

    QCheckBox#taskCheckBox::indicator {{
        width: 0px;
        height: 0px;
        border: none;
        background: transparent;
        image: none;
    }}

    QCheckBox#taskCheckBox:focus {{
        border: 2px solid {COLOR_SOFT};
        border-radius: 8px;
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

    /* Weekly dashboard (Phase 7F): same dark-compact language as the rest. */
    QDialog#dashboardWindow {{
        background-color: {COLOR_BACKGROUND};
    }}

    QScrollArea#dashboardScroll, QWidget#dashboardContent {{
        background-color: transparent;
        border: none;
    }}

    QLabel#dashboardTitle {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 17px;
        font-weight: 700;
        background: transparent;
    }}

    QLabel#dashboardRangeLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 500;
        background: transparent;
    }}

    QPushButton#dashboardPresetButton {{
        background-color: {COLOR_CARD_SURFACE};
        color: {COLOR_TEXT_SECONDARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 500;
    }}

    QPushButton#dashboardPresetButton:hover {{
        border-color: {COLOR_FOCUS_RING};
        color: {COLOR_TEXT_PRIMARY};
    }}

    QPushButton#dashboardPresetButton:checked {{
        background-color: rgba(79, 124, 172, 0.30);
        border-color: {COLOR_FOCUS_RING};
        color: {COLOR_TEXT_PRIMARY};
    }}

    QDateEdit#dashboardDateEdit {{
        background-color: {COLOR_INPUT_BG};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 6px;
        padding: 4px 6px;
        font-size: 12px;
    }}

    QDateEdit#dashboardDateEdit:focus {{
        border: 2px solid {COLOR_FOCUS_RING};
    }}

    QDateEdit#dashboardDateEdit::drop-down {{
        border: none;
        width: 14px;
    }}

    QCalendarWidget QWidget {{
        background-color: {COLOR_CARD_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
    }}

    QCalendarWidget QAbstractItemView {{
        background-color: {COLOR_CARD_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        selection-background-color: rgba(79, 124, 172, 0.40);
        selection-color: {COLOR_TEXT_PRIMARY};
    }}

    QPushButton#dashboardApplyButton {{
        background-color: {COLOR_FOCUS_RING};
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 600;
    }}

    QPushButton#dashboardApplyButton:hover {{
        background-color: #5D8DBE;
    }}

    QPushButton#dashboardApplyButton:pressed {{
        background-color: #436E9B;
    }}

    QLabel#dashboardErrorLabel {{
        color: #E57373;
        font-size: 12px;
        font-weight: 500;
        background: transparent;
    }}

    QFrame#dashboardSummary {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 10px;
    }}

    QLabel#dashboardStatValue {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 18px;
        font-weight: 700;
        background: transparent;
    }}

    QLabel#dashboardStatLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 500;
        background: transparent;
    }}

    QFrame#categoryCard {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid {COLOR_CARD_BORDER};
        border-radius: 8px;
    }}

    QLabel#categoryCardIcon {{
        background: transparent;
        border: none;
    }}

    QLabel#categoryCardName {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 13px;
        font-weight: 600;
        background: transparent;
    }}

    QLabel#categoryCardStats {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 500;
        background: transparent;
    }}

    QProgressBar#categoryCardBar {{
        background-color: {COLOR_CARD_BORDER};
        border: none;
        border-radius: 3px;
    }}

    QProgressBar#categoryCardBar::chunk {{
        background-color: {COLOR_FOCUS_RING};
        border-radius: 3px;
    }}

    QLabel#dashboardLegendDone {{
        color: {COLOR_SOFT};
        font-size: 11px;
        font-weight: 600;
        background: transparent;
    }}

    QLabel#dashboardLegendTodo {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 11px;
        font-weight: 500;
        background: transparent;
    }}

    QWidget#dashboardChart {{
        background: transparent;
    }}

    QLabel#dashboardEmptyLabel {{
        color: {COLOR_TEXT_COMPLETED};
        font-size: 13px;
        font-weight: 500;
        background: transparent;
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

    /* Pinned-mode application menu (v3 §10): same panel language. */
    QMenu#appContextMenu {{
        background-color: #1c2533;
        border: 1px solid {COLOR_BORDER};
        border-radius: 12px;
        padding: 4px;
    }}

    QMenu#appContextMenu::item {{
        background-color: transparent;
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
        padding: 8px 12px;
        border-radius: 8px;
    }}

    QMenu#appContextMenu::item:selected {{
        background-color: {COLOR_BORDER};
        color: {COLOR_TEXT_PRIMARY};
    }}

    QMenu#appContextMenu::item:disabled {{
        color: #4A586B;
        background-color: transparent;
    }}

    QMenu#appContextMenu::separator {{
        height: 1px;
        background: {COLOR_BORDER};
        margin: 4px 8px;
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

