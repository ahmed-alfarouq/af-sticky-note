"""Quiet quote section: readable Arabic typography, no card nesting (Phase 7D).

The date moved to :class:`DateHeaderWidget`; this widget shows only the
daily quote text. Quote selection/rotation behavior is untouched (owned by
the quote services); this widget only displays text it is given.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


class QuoteWidget(QFrame):
    """Presents the centered daily quote text."""

    def __init__(
        self,
        quote_text: Optional[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("quoteSection")
        self.setAccessibleName("قسم الحكمة اليومية")
        self.setAccessibleDescription("يعرض الحكمة المختارة لهذا اليوم")
        self._init_ui(quote_text or "لا توجد حكمة متاحة لهذا اليوم")

    def _init_ui(self, quote_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._quote_label = QLabel(f"« {quote_text} »", self)
        self._quote_label.setObjectName("quoteTextLabel")
        self._quote_label.setWordWrap(True)
        self._quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._quote_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._quote_label.setAccessibleName("نص الحكمة اليومية")

        layout.addWidget(self._quote_label)

    def set_quote_text(self, text: str) -> None:
        self._quote_label.setText(f"« {text} »")
