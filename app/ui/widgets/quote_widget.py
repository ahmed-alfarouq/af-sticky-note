"""Read-only quote and date presentation widget with accessibility support."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.infrastructure.clock import format_dual_calendar_date


class QuoteWidget(QFrame):
    """Presents the centered dual date (Gregorian & Hijri) and centered daily quote."""

    def __init__(
        self,
        date_text: str,
        quote_text: Optional[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("quoteCard")
        self.setAccessibleName("بطاقة الحكمة اليومية")
        self.setAccessibleDescription("تحتوي على تاريخ اليوم الميلادي والهجري والحكمة المختارة")
        self._init_ui(date_text, quote_text or "لا توجد حكمة متاحة لهذا اليوم")

    def _init_ui(self, date_text: str, quote_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Dual Gregorian + Hijri date formatted in Arabic
        formatted_date = format_dual_calendar_date(date_text)

        self._date_label = QLabel(formatted_date, self)
        self._date_label.setObjectName("dateLabel")
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._date_label.setWordWrap(True)
        self._date_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._date_label.setAccessibleName("التاريخ الميلادي والهجري لليوم")

        self._quote_label = QLabel(f"« {quote_text} »", self)
        self._quote_label.setObjectName("quoteTextLabel")
        self._quote_label.setWordWrap(True)
        self._quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._quote_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._quote_label.setAccessibleName("نص الحكمة اليومية")

        layout.addWidget(self._date_label)
        layout.addWidget(self._quote_label)

    def set_quote_text(self, text: str) -> None:
        self._quote_label.setText(f"« {text} »")

    def set_date_and_quote(self, date_text: str, quote_text: Optional[str]) -> None:
        """Update both the dual calendar date and quote text."""
        formatted_date = format_dual_calendar_date(date_text)
        self._date_label.setText(formatted_date)
        self.set_quote_text(quote_text or "لا توجد حكمة متاحة لهذا اليوم")
