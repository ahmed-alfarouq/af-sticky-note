"""Date header block: strong day hierarchy + daily progress (Phase 7D).

RTL row: [large day number] [weekday + secondary date stack] [stretch]
[daily progress ring]. Data comes from :mod:`app.infrastructure.clock`
(date parts) and :func:`compute_daily_stats` via the coordinator; this
widget formats and draws only.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.infrastructure.clock import get_date_parts
from app.ui.widgets.progress_ring import ProgressRing

__all__ = ["DateHeaderWidget"]


class DateHeaderWidget(QFrame):
    """Coherent date block with big day number, weekday, Hijri line, ring."""

    def __init__(
        self,
        date_text: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dateHeader")
        self.setAccessibleName("ترويسة التاريخ وتقدم اليوم")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(10)

        self._day_number = QLabel(self)
        self._day_number.setObjectName("dayNumber")
        self._day_number.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._day_number)

        stack = QVBoxLayout()
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(1)
        self._weekday_label = QLabel(self)
        self._weekday_label.setObjectName("weekdayLabel")
        self._weekday_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._secondary_label = QLabel(self)
        self._secondary_label.setObjectName("secondaryDateLabel")
        self._secondary_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._secondary_label.setWordWrap(True)
        stack.addWidget(self._weekday_label)
        stack.addWidget(self._secondary_label)
        layout.addLayout(stack)

        layout.addStretch(1)

        self._ring = ProgressRing(self)
        layout.addWidget(self._ring)

        self.set_date(date_text)

    def set_date(self, date_text: str) -> None:
        """Load Gregorian/Hijri parts for an ISO date (never raises)."""
        day_number, weekday_ar, month_year, hijri = get_date_parts(date_text)
        self._day_number.setText(day_number)
        self._weekday_label.setText(weekday_ar)
        secondary = f"{month_year}  •  {hijri}" if weekday_ar else month_year or hijri
        self._secondary_label.setText(secondary)
        self.setAccessibleDescription(f"تاريخ اليوم: {day_number} {secondary}")

    def set_progress(self, completed: int, total: int) -> None:
        """Forward daily counts to the ring (repaint only on change)."""
        self._ring.set_progress(completed, total)

    def progress_value(self) -> tuple:
        """Current ``(completed, total)`` shown by the ring."""
        return self._ring.progress_value()
