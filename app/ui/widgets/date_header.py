"""Date header block: prominent day number with the date text beside it.

The row inherits the application's RTL layout direction: the day number
appears on the right and the date text container beside it.

The date text container stacks the month and year of the leading calendar
(Hijri or Gregorian, as the user chose) above the weekday and the other
calendar's date. Daily progress is shown by a separate ``ProgressRing``
placed under this header.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.infrastructure.clock import date_display, get_date_parts
from app.ui.date_presentation import CalendarKind, DateHeaderText, date_header_text

__all__ = ["DateHeaderWidget"]


class DateHeaderWidget(QFrame):
    """Date block with a large day number and stacked date text."""

    def __init__(
        self,
        date_text: str,
        parent: Optional[QWidget] = None,
        calendar: CalendarKind = CalendarKind.HIJRI,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("dateHeader")
        self.setAccessibleName("تاريخ اليوم")

        self._date_text = date_text
        self._calendar = calendar

        self._day_number = QLabel(self)
        self._day_number.setObjectName("dayNumber")
        self._day_number.setWordWrap(False)
        self._day_number.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        # Object names are the QSS hooks: bold month/year line, then the quiet line.
        self._primary_label = self._make_date_label("hijriDateLabel")
        self._primary_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._secondary_label = self._make_date_label("gregorianDateLabel")

        date_text_container = QWidget(self)
        date_text_container.setObjectName("dateTextContainer")
        text_layout = QVBoxLayout(date_text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_layout.addWidget(self._primary_label)
        text_layout.addWidget(self._secondary_label)

        # Inherit the application's RTL direction; do not override it here.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 0)
        layout.setSpacing(10)
        layout.addWidget(self._day_number)
        layout.addWidget(date_text_container, 1)

        self.set_date(date_text)

    def _make_date_label(self, object_name: str) -> QLabel:
        label = QLabel(self)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setMinimumWidth(0)
        return label

    def set_calendar(self, calendar: CalendarKind) -> None:
        """Lead with ``calendar`` and redraw the current date."""
        if calendar is self._calendar:
            return
        self._calendar = calendar
        self.set_date(self._date_text)

    def set_date(self, date_text: str) -> None:
        """Update the displayed date using the shared date utilities."""
        self._date_text = date_text
        self._show(self._texts_for(date_text))

    def _texts_for(self, date_text: str) -> DateHeaderText:
        display = date_display(date_text)
        if display is not None:
            return date_header_text(display, self._calendar)

        # Unparseable date: show what can be shown, whichever calendar leads.
        day_number, weekday_ar, month_year, hijri = get_date_parts(date_text)
        return DateHeaderText(
            day_number=day_number,
            primary_line=hijri or "",
            secondary_line=" · ".join(part for part in (weekday_ar, month_year) if part),
        )

    def _show(self, texts: DateHeaderText) -> None:
        self._day_number.setText(texts.day_number)
        self._primary_label.setText(texts.primary_line)
        self._secondary_label.setText(texts.secondary_line)
        self.setAccessibleDescription(
            f"تاريخ اليوم: {texts.day_number} {texts.primary_line}  •  {texts.secondary_line}"
        )