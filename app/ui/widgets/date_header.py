
"""Date header block: prominent Hijri day + daily progress.

The hero row inherits the application's RTL layout direction:
the Hijri day appears on the right, the date text container is beside it,
and the progress ring is toward the left.

The date text container stacks the Hijri date above the Gregorian date.
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
from app.ui.widgets.progress_ring import ProgressRing

__all__ = ["DateHeaderWidget"]


class DateHeaderWidget(QFrame):
    """Date block with a large Hijri day and daily progress."""

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
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        self._hijri_label = QLabel(self)
        self._hijri_label.setObjectName("hijriDateLabel")
        self._hijri_label.setWordWrap(True)
        self._hijri_label.setMinimumWidth(0)
        self._hijri_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        self._gregorian_label = QLabel(self)
        self._gregorian_label.setObjectName("gregorianDateLabel")
        self._gregorian_label.setWordWrap(True)
        self._gregorian_label.setMinimumWidth(0)

        # Group both date labels in a single vertical container.
        self._date_text_container = QWidget(self)
        self._date_text_container.setObjectName("dateTextContainer")

        date_text_layout = QVBoxLayout(self._date_text_container)
        date_text_layout.setContentsMargins(0, 0, 0, 0)
        date_text_layout.setSpacing(0)
        date_text_layout.addWidget(self._hijri_label)
        date_text_layout.addWidget(self._gregorian_label)

        # Retained for compatibility with existing code that reads this label.
        self._secondary_label = QLabel(self)
        self._secondary_label.setVisible(False)

        self._ring = ProgressRing(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 0)
        layout.setSpacing(0)

        # Inherit the application's RTL direction; do not override it here.
        hero_row = QHBoxLayout()
        hero_row.setContentsMargins(0, 0, 0, 0)
        hero_row.setSpacing(10)

        hero_row.addWidget(self._day_number)
        hero_row.addWidget(self._date_text_container, 1)
        hero_row.addWidget(self._ring)

        layout.addLayout(hero_row)

        self.set_date(date_text)

    def set_date(self, date_text: str) -> None:
        """Update the displayed date using the shared date utilities."""
        display = date_display(date_text)

        if display is None:
            day_number, weekday_ar, month_year, hijri = get_date_parts(
                date_text
            )

            self._day_number.setText(day_number)
            self._hijri_label.setText(hijri or "")
            self._gregorian_label.setText(
                " · ".join(
                    part for part in (weekday_ar, month_year) if part
                )
            )
            secondary = month_year or hijri or ""
        else:
            self._day_number.setText(str(display.hijri_day))

            hijri_month_year = (
                f"{display.hijri_month_name} "
                f"{display.hijri_year} هـ"
            )
            self._hijri_label.setText(hijri_month_year)

            gregorian_month_year = (
                f"{display.gregorian_month_name} "
                f"{display.gregorian_year}"
            )
            gregorian_row = (
                f"{display.weekday_ar} · "
                f"{display.gregorian_day} "
                f"{gregorian_month_year}"
            )
            self._gregorian_label.setText(gregorian_row)

            secondary = (
                f"{gregorian_month_year}  •  "
                f"{display.hijri_day} {hijri_month_year}"
            )

        self._secondary_label.setText(secondary)
        self.setAccessibleDescription(
            f"تاريخ اليوم: {self._day_number.text()} {secondary}"
        )

    def set_progress(self, completed: int, total: int) -> None:
        """Forward daily progress counts to the progress ring."""
        self._ring.set_progress(completed, total)

    def progress_value(self) -> tuple:
        """Return the completed and total values shown by the ring."""
        return self._ring.progress_value()
