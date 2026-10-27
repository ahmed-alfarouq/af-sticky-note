"""Date header block: prominent Hijri day with the date text beside it.

The row inherits the application's RTL layout direction: the Hijri day
appears on the right and the date text container beside it.

The date text container stacks the Hijri month/year above the Gregorian
weekday and date. Daily progress is shown by a separate ``ProgressRing``
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

__all__ = ["DateHeaderWidget"]


class DateHeaderWidget(QFrame):
    """Date block with a large Hijri day and stacked date text."""

    def __init__(
        self,
        date_text: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("dateHeader")
        self.setAccessibleName("تاريخ اليوم")

        self._day_number = QLabel(self)
        self._day_number.setObjectName("dayNumber")
        self._day_number.setWordWrap(False)
        self._day_number.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self._hijri_label = self._make_date_label("hijriDateLabel")
        self._hijri_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._gregorian_label = self._make_date_label("gregorianDateLabel")

        date_text_container = QWidget(self)
        date_text_container.setObjectName("dateTextContainer")
        text_layout = QVBoxLayout(date_text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_layout.addWidget(self._hijri_label)
        text_layout.addWidget(self._gregorian_label)

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

    def set_date(self, date_text: str) -> None:
        """Update the displayed date using the shared date utilities."""
        display = date_display(date_text)

        if display is None:
            day_number, weekday_ar, month_year, hijri = get_date_parts(date_text)

            hijri_text = hijri or ""
            gregorian_text = " · ".join(
                part for part in (weekday_ar, month_year) if part
            )
            secondary = month_year or hijri or ""
        else:
            day_number = str(display.hijri_day)

            hijri_text = f"{display.hijri_month_name} {display.hijri_year} هـ"
            gregorian_month_year = (
                f"{display.gregorian_month_name} {display.gregorian_year}"
            )
            gregorian_text = (
                f"{display.weekday_ar} · "
                f"{display.gregorian_day} {gregorian_month_year}"
            )
            secondary = (
                f"{gregorian_month_year}  •  {display.hijri_day} {hijri_text}"
            )

        self._day_number.setText(day_number)
        self._hijri_label.setText(hijri_text)
        self._gregorian_label.setText(gregorian_text)
        self.setAccessibleDescription(f"تاريخ اليوم: {day_number} {secondary}")