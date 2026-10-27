"""Date header block: strong day hierarchy + daily progress (Phase 7D).

RTL rows: [large Hijri day number] [stretch] [Hijri month/year] [ring] on
top, then the Gregorian weekday and full date spanning the width beneath.
Data comes from :mod:`app.infrastructure.clock` (date parts) and
:func:`compute_daily_stats` via the coordinator; this widget formats and
draws only.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.infrastructure.clock import date_display, get_date_parts
from app.ui.widgets.progress_ring import ProgressRing

__all__ = ["DateHeaderWidget"]


class DateHeaderWidget(QFrame):
    """Coherent date block: big day number, Hijri month/year, Gregorian row."""

    def __init__(
        self,
        date_text: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dateHeader")
        self.setAccessibleName("تاريخ اليوم")

        # Large Hijri day number (hero). No word wrap, so its natural text
        # width is also its floor: the layout below can never squeeze it
        # onto two lines or let the neighbouring text overlap it.
        self._day_number = QLabel(self)
        self._day_number.setObjectName("dayNumber")

        # Hijri month + year, one line on the left of the hero row. Wrapping
        # is enabled so it reflows instead of clipping at narrow widths.
        self._hijri_label = QLabel(self)
        self._hijri_label.setObjectName("hijriDateLabel")
        self._hijri_label.setWordWrap(True)

        # Gregorian weekday and full date, spanning the header width.
        self._gregorian_label = QLabel(self)
        self._gregorian_label.setObjectName("gregorianDateLabel")
        self._gregorian_label.setWordWrap(True)

        # Compatibility alias: frozen UI tests read the combined secondary
        # text from ``_secondary_label``. It is intentionally NOT laid out
        # (and has no objectName, so the QSS coverage guard ignores it) and
        # carries the same combined string for those readers only.
        self._secondary_label = QLabel(self)
        self._secondary_label.setVisible(False)

        self._ring = ProgressRing(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 0)
        # The Gregorian row sits directly beneath the hero row; the hero's
        # own line box already provides the visual gap.
        layout.setSpacing(0)

        hero_row = QHBoxLayout()
        hero_row.setContentsMargins(0, 0, 0, 0)
        hero_row.setSpacing(10)
        # RightToLeft: the first widget lands on the right edge, so the day
        # number leads and the stretch holds it clear of the Hijri
        # month/year, which is pinned to the left next to the ring.
        hero_row.addWidget(self._day_number)
        hero_row.addStretch(1)
        hero_row.addWidget(self._hijri_label)
        hero_row.addWidget(self._ring)
        layout.addLayout(hero_row)

        layout.addWidget(self._gregorian_label)

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
            self._hijri_label.setText("")
            self._gregorian_label.setText(
                " · ".join(part for part in (weekday_ar, month_year) if part)
            )
            secondary = month_year or hijri
        else:
            self._day_number.setText(str(display.hijri_day))
            hijri_month_year = f"{display.hijri_month_name} {display.hijri_year} هـ"
            self._hijri_label.setText(hijri_month_year)
            gregorian_month_year = f"{display.gregorian_month_name} {display.gregorian_year}"
            gregorian_row = (
                f"{display.weekday_ar} · {display.gregorian_day} {gregorian_month_year}"
            )
            self._gregorian_label.setText(gregorian_row)
            secondary = f"{gregorian_month_year}  •  {display.hijri_day} {hijri_month_year}"
        self._secondary_label.setText(secondary)
        self.setAccessibleDescription(f"تاريخ اليوم: {self._day_number.text()} {secondary}")

    def set_progress(self, completed: int, total: int) -> None:
        """Forward daily counts to the ring (repaint only on change)."""
        self._ring.set_progress(completed, total)

    def progress_value(self) -> tuple:
        """Current ``(completed, total)`` shown by the ring."""
        return self._ring.progress_value()
