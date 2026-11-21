"""The archive's date picker: a month calendar of the days that can be opened."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.infrastructure.clock import ARABIC_GREGORIAN_MONTHS
from app.ui.archive_calendar import (
    ArchiveDates,
    iso_date,
    month_of,
    month_title,
    shift_month,
)
from app.ui.styles.archive_style import BLOCK_GAP, CARD_PAD, CELL_TEXT_OFF
from app.ui.widgets.archive.day_grid import DayGrid
from app.ui.widgets.icon_button import IconButton

__all__ = ["DatePicker"]

_ICON_IDLE = "#a3aec2"
_ICON_HOVER = "#ffffff"
_MONTH_BUTTON = 44
_MONTH_ICON = 20


def _month_button(icon_key: str, label: str) -> IconButton:
    button = IconButton(
        icon_key,
        idle=_ICON_IDLE,
        hover=_ICON_HOVER,
        disabled=CELL_TEXT_OFF,
        size=_MONTH_ICON,
        button_size=_MONTH_BUTTON,
    )
    button.setAccessibleName(label)
    button.setToolTip(label)
    return button


class DatePicker(QWidget):
    """Pick one of the openable past days; "عرض" opens it."""

    #: The user confirmed a day (ISO date).
    day_chosen = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dates = ArchiveDates([])
        self._today = ""
        self._week_start = 5
        self._year = 1970
        self._month = 1
        self._selected: Optional[str] = None

        self._previous = _month_button("caret_right", "الشهر السابق")
        self._previous.clicked.connect(lambda: self._shift(-1))
        self._next = _month_button("caret_left", "الشهر التالي")
        self._next.clicked.connect(lambda: self._shift(1))

        self._title = QLabel(self)
        self._title.setObjectName("archiveMonthTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._grid = DayGrid(self)
        self._grid.day_selected.connect(self._on_day_selected)

        self._go = QPushButton(self)
        self._go.setObjectName("archiveGoButton")
        self._go.setCursor(Qt.CursorShape.PointingHandCursor)
        self._go.clicked.connect(self._confirm)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BLOCK_GAP)
        layout.addWidget(self._build_card())
        layout.addStretch(1)
        layout.addWidget(self._go)

        QWidget.setTabOrder(self._previous, self._next)
        QWidget.setTabOrder(self._next, self._grid)
        QWidget.setTabOrder(self._grid, self._go)

    def _build_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("archiveCard")

        month_row = QHBoxLayout()
        month_row.setContentsMargins(0, 0, 0, 0)
        month_row.addWidget(self._previous)
        month_row.addWidget(self._title, 1)
        month_row.addWidget(self._next)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(CARD_PAD, CARD_PAD, CARD_PAD, CARD_PAD)
        layout.setSpacing(0)
        layout.addLayout(month_row)
        layout.addWidget(self._grid)
        return card

    # -- Showing a month ------------------------------------------------------

    def open_month(
        self,
        selected_iso: Optional[str],
        dates: ArchiveDates,
        today_iso: str,
        week_start: int,
    ) -> None:
        """Show the month of ``selected_iso`` (or the newest openable day)."""
        self._dates = dates
        self._today = today_iso
        self._week_start = week_start
        self._selected = selected_iso

        anchor = selected_iso or dates.newest() or today_iso
        self._year, self._month = month_of(anchor)
        self._refresh()

    def _shift(self, delta: int) -> None:
        self._year, self._month = shift_month(self._year, self._month, delta)
        self._refresh()

    def _refresh(self) -> None:
        year, month = self._year, self._month
        today_year, today_month = month_of(self._today)

        self._title.setText(month_title(year, month))
        self._previous.setEnabled(self._dates.has_before_month(year, month))
        self._next.setEnabled((year, month) < (today_year, today_month))

        today_day = int(self._today[8:10]) if (year, month) == (today_year, today_month) else None
        self._grid.set_month(
            year,
            month,
            self._week_start,
            self._dates.days_in_month(year, month),
            today_day,
            self._selected_day(),
        )
        self._update_go_button()

    def _selected_day(self) -> Optional[int]:
        if self._selected and month_of(self._selected) == (self._year, self._month):
            return int(self._selected[8:10])
        return None

    # -- Choosing -----------------------------------------------------------------

    def _on_day_selected(self, day: int) -> None:
        self._selected = iso_date(self._year, self._month, day)
        self._grid.set_selected(day)
        self._update_go_button()

    def _update_go_button(self) -> None:
        if self._selected is None:
            self._go.setText("اختر يوماً")
            self._go.setEnabled(False)
            return

        year, month = month_of(self._selected)
        day = int(self._selected[8:10])
        self._go.setText(f"عرض {day} {ARABIC_GREGORIAN_MONTHS[month - 1]}")
        self._go.setEnabled(True)

    def _confirm(self) -> None:
        if self._selected is not None:
            self.day_chosen.emit(self._selected)