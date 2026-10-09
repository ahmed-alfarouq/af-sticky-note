"""Category summary card for the weekly dashboard (Phase 7F).

Presentation only: icon (shared cached provider), Arabic name, counts, and
a thin progress bar. Built from a :class:`CategoryReport`, never from SQL.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.core.daily_reports import CategoryReport
from app.ui.category_icons import CategoryIconProvider

__all__ = ["CategoryCard"]


class CategoryCard(QFrame):
    """One category's totals for the selected range."""

    def __init__(
        self,
        report: CategoryReport,
        icon_provider: Optional[CategoryIconProvider] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("categoryCard")
        self._report = report

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)

        self._icon_label = QLabel(self)
        self._icon_label.setObjectName("categoryCardIcon")
        self._icon_label.setFixedSize(30, 30)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_provider is not None:
            self._icon_label.setPixmap(
                icon_provider.icon_for_key(report.icon_key).pixmap(24, 24)
            )
        self._icon_label.setToolTip(report.category_name_ar)
        row.addWidget(self._icon_label)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        self._name_label = QLabel(report.category_name_ar, self)
        self._name_label.setObjectName("categoryCardName")
        self._stats_label = QLabel(
            f"مكتملة {report.completed} من {report.total} • {report.completion_percentage}٪",
            self,
        )
        self._stats_label.setObjectName("categoryCardStats")
        text_col.addWidget(self._name_label)
        text_col.addWidget(self._stats_label)
        row.addLayout(text_col, 1)

        self._bar = QProgressBar(self)
        self._bar.setObjectName("categoryCardBar")
        self._bar.setRange(0, 100)
        self._bar.setValue(report.completion_percentage)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setToolTip(f"{report.completion_percentage}٪")
        row.addWidget(self._bar)

        self.setAccessibleName(f"فئة {report.category_name_ar}: {report.completed} من {report.total}")

    def category_id(self) -> str:
        """Stable category id shown by this card."""
        return self._report.category_id
