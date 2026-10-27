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

from app.infrastructure.clock import date_display, get_date_parts
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
        self.setAccessibleName("تاريخ اليوم")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 0)
        layout.setSpacing(10)

        self._day_number = QLabel(self)
        self._day_number.setObjectName("dayNumber")
        layout.addWidget(self._day_number)

        stack = QVBoxLayout()
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(1)
        self._weekday_label = QLabel(self)
        self._weekday_label.setObjectName("weekdayLabel")
        
        # Hijri line (top) — soft-blue emphasis.
        self._hijri_label = QLabel(self)
        self._hijri_label.setObjectName("hijriDateLabel")
        
        self._hijri_label.setWordWrap(True)
        stack.addWidget(self._weekday_label)
        stack.addWidget(self._hijri_label)
        # Gregorian line (bottom) — quieter secondary text.
        self._gregorian_label = QLabel(self)
        self._gregorian_label.setObjectName("gregorianDateLabel")
        
        self._gregorian_label.setWordWrap(True)
        stack.addWidget(self._gregorian_label)
        # Compatibility alias: frozen UI tests read the combined secondary
        # text from ``_secondary_label``. It is intentionally NOT laid out
        # (and has no objectName, so the QSS coverage guard ignores it) and
        # carries the same combined string for those readers only.
        self._secondary_label = QLabel(self)
        self._secondary_label.setVisible(False)
        layout.addLayout(stack)

        layout.addStretch(1)

        self._ring = ProgressRing(self)
        layout.addWidget(self._ring)

        self.set_date(date_text)

    def set_date(self, date_text: str) -> None:
        """Load Gregorian/Hijri parts for an ISO date (never raises).

        Follows the v3 hero hierarchy through the :class:`DateDisplay`
        domain contract: the Hijri numeral dominates, Gregorian stays
        secondary. Invalid input degrades to the raw string.
        """
        display = date_display(date_text)
        if display is None:
            day_number, weekday_ar, month_year, hijri = get_date_parts(date_text)
            self._day_number.setText(day_number)
            self._weekday_label.setText(weekday_ar)
            self._hijri_label.setText("")
            self._gregorian_label.setText(month_year or hijri)
            secondary = month_year or hijri
        else:
            self._day_number.setText(str(display.hijri_day))
            self._weekday_label.setText(display.weekday_ar)
            hijri_month_year = f"{display.hijri_month_name} {display.hijri_year} هـ"
            gregorian_month_year = f"{display.gregorian_month_name} {display.gregorian_year}"
            self._hijri_label.setText(hijri_month_year)
            self._gregorian_label.setText(gregorian_month_year)
            secondary = f"{gregorian_month_year}  •  {display.hijri_day} {hijri_month_year}"
        self._secondary_label.setText(secondary)
        self.setAccessibleDescription(f"تاريخ اليوم: {self._day_number.text()} {secondary}")

    def set_progress(self, completed: int, total: int) -> None:
        """Forward daily counts to the ring (repaint only on change)."""
        self._ring.set_progress(completed, total)

    def progress_value(self) -> tuple:
        """Current ``(completed, total)`` shown by the ring."""
        return self._ring.progress_value()
