"""Read-only quote and date presentation widget with accessibility support."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class QuoteWidget(QFrame):
    """Presents the current date and daily quote text with RTL alignment."""

    def __init__(
        self,
        date_text: str,
        quote_text: Optional[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("quoteCard")
        self.setAccessibleName("بطاقة الحكمة اليومية")
        self.setAccessibleDescription("تحتوي على تاريخ اليوم والحكمة المختارة")
        self._init_ui(date_text, quote_text or "لا توجد حكمة متاحة لهذا اليوم")

    def _init_ui(self, date_text: str, quote_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self._date_label = QLabel(date_text, self)
        self._date_label.setObjectName("dateLabel")
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._date_label.setAccessibleName("تاريخ اليوم")

        self._quote_label = QLabel(f"« {quote_text} »", self)
        self._quote_label.setObjectName("quoteTextLabel")
        self._quote_label.setWordWrap(True)
        self._quote_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._quote_label.setAccessibleName("نص الحكمة اليومية")

        layout.addWidget(self._date_label)
        layout.addWidget(self._quote_label)

    def set_quote_text(self, text: str) -> None:
        self._quote_label.setText(f"« {text} »")
