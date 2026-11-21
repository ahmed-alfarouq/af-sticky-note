"""Quote block: upright Arabic typography with a start-edge rule (v3 §6).

The date lives in :class:`DateHeaderWidget`; this widget shows only the
daily quote text: 14 px secondary, never italic, no decorative quotation
marks, a 2 px trust-colored rule along the start (right) edge, at most three
visible lines (elided with tooltip carrying the full text). Quote
selection/rotation behavior is untouched (owned by the quote services); this
widget only displays text it is given.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget

#: Maximum visible lines before elision (v3 §6).
MAX_VISIBLE_LINES = 3


class QuoteWidget(QFrame):
    """Presents the daily quote text with its accent rule."""

    def __init__(
        self,
        quote_text: Optional[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("quoteSection")
        self.setAccessibleName("قسم الحكمة اليومية")
        self.setAccessibleDescription("يعرض الحكمة المختارة لهذا اليوم")
        self._raw_text = quote_text or "لا توجد حكمة متاحة لهذا اليوم"
        self._init_ui()
        self.set_quote_text(self._raw_text)

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Start-edge (right in RTL) vertical accent rule.
        self._rule = QLabel(self)
        self._rule.setObjectName("quoteRule")
        self._rule.setFixedWidth(2)
        self._rule.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._rule.setAccessibleName("")
        layout.addWidget(self._rule)

        self._quote_label = QLabel(self)
        self._quote_label.setObjectName("quoteTextLabel")
        self._quote_label.setWordWrap(True)
        self._quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._quote_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._quote_label.setAccessibleName("نص الحكمة اليومية")
        layout.addWidget(self._quote_label, 1)

    def set_quote_text(self, text: str) -> None:
        self._raw_text = text
        self._quote_label.setToolTip(text)
        self._quote_label.setAccessibleDescription(text)
        self._apply_visible_text()

    def quote_text(self) -> str:
        """The full stored quote (tooltips/diagnostics), never elided."""
        return self._raw_text

    def _apply_visible_text(self) -> None:
        """Show up to three lines; elide with … when taller allows."""
        metrics = QFontMetrics(self._quote_label.font())
        width = max(1, self._quote_label.width() or self.width() or 1)
        line_height = max(1, metrics.lineSpacing())
        full = self._raw_text
        if metrics.boundingRect(0, 0, width, 10**6, Qt.TextWordWrap, full).height() <= line_height * MAX_VISIBLE_LINES:
            self._quote_label.setText(full)
            return
        words = full.split()
        visible = full
        while words:
            candidate = " ".join(words)
            height = metrics.boundingRect(0, 0, width, 10**6, Qt.TextWordWrap, candidate + " …").height()
            if height <= line_height * MAX_VISIBLE_LINES:
                visible = candidate + " …"
                break
            words.pop()
        else:
            visible = full[:1] + " …" if full else ""
        self._quote_label.setText(visible)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._apply_visible_text()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().showEvent(event)
        self._apply_visible_text()
