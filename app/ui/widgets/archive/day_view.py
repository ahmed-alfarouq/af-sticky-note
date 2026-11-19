"""The archive's day view: a day card, its progress, and its tasks."""

from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.models import Category
from app.core.services.history_service import DayHistoryView
from app.ui.category_icons import CategoryIconProvider
from app.ui.date_presentation import ArchiveDateText
from app.ui.icons import icon as vector_icon
from app.ui.styles.archive_style import (
    BLOCK_GAP,
    CARD_GAP,
    CARD_PAD,
    LIST_GAP,
    NAV_BUTTON_ICON,
)
from app.ui.widgets.archive.archive_row import ArchiveTaskRow
from app.ui.widgets.archive.progress_card import DayProgressCard
from app.ui.widgets.task_list.ordering import view_order_key

__all__ = ["DayView"]

NO_TASKS_TEXT = "لا توجد مهام في هذا اليوم"


def _nav_button(text: str, icon_key: str, *, icon_first: bool) -> QPushButton:
    """A "previous"/"next" button; its arrow sits before or after the text."""
    button = QPushButton(text)
    button.setObjectName("archiveNavButton")
    button.setIcon(vector_icon(icon_key, "#ffffff"))
    button.setIconSize(QSize(NAV_BUTTON_ICON, NAV_BUTTON_ICON))
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    # A button puts its icon at the reading-start side; flip it for "after".
    button.setLayoutDirection(
        Qt.LayoutDirection.RightToLeft if icon_first else Qt.LayoutDirection.LeftToRight
    )
    return button


class DayView(QWidget):
    """One past day, read-only, with previous/next day buttons."""

    previous_requested = Signal()
    next_requested = Signal()

    def __init__(
        self,
        categories: Sequence[Category],
        icon_provider: CategoryIconProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._categories = list(categories)
        self._icon_provider = icon_provider
        self._rows: List[QWidget] = []

        self._previous = _nav_button("السابق", "arrow_right", icon_first=True)
        self._previous.clicked.connect(self.previous_requested)
        self._next = _nav_button("التالي", "arrow_left", icon_first=False)
        self._next.clicked.connect(self.next_requested)

        self._date_primary = QLabel(self)
        self._date_primary.setObjectName("archiveDatePrimary")
        self._date_secondary = QLabel(self)
        self._date_secondary.setObjectName("archiveDateSecondary")
        for label in (self._date_primary, self._date_secondary):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._progress = DayProgressCard(self)

        section = QLabel("مهام اليوم", self)
        section.setObjectName("archiveSection")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BLOCK_GAP)
        layout.addWidget(self._build_day_card())
        layout.addWidget(self._progress)
        layout.addWidget(section)
        layout.addWidget(self._build_list(), 1)

    # -- Construction -------------------------------------------------------

    def _build_day_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("archiveCard")

        names = QVBoxLayout()
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(2)
        names.addWidget(self._date_primary)
        names.addWidget(self._date_secondary)

        row = QHBoxLayout(card)
        row.setContentsMargins(CARD_PAD, CARD_PAD, CARD_PAD, CARD_PAD)
        row.setSpacing(CARD_GAP)
        row.addWidget(self._previous)
        row.addLayout(names, 1)
        row.addWidget(self._next)
        return card

    def _build_list(self) -> QScrollArea:
        host = QWidget()
        host.setObjectName("archiveRows")
        self._rows_layout = QVBoxLayout(host)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(LIST_GAP)
        self._rows_layout.addStretch(1)

        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("archiveScroll")
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.setWidget(host)
        return self._scroll

    # -- Showing a day --------------------------------------------------------

    def show_day(
        self,
        view: DayHistoryView,
        texts: ArchiveDateText,
        *,
        has_older: bool,
        has_newer: bool,
    ) -> None:
        self._date_primary.setText(texts.primary)
        self._date_secondary.setText(texts.secondary)
        self._previous.setEnabled(has_older)
        self._next.setEnabled(has_newer)

        self._progress.show_progress(view.stats.completed, view.stats.total)
        self._fill_rows(view)
        self._scroll.verticalScrollBar().setValue(0)

    def _fill_rows(self, view: DayHistoryView) -> None:
        for row in self._rows:
            self._rows_layout.removeWidget(row)
            row.deleteLater()
        self._rows = []

        host = self._scroll.widget()
        if not view.tasks:
            empty = QLabel(NO_TASKS_TEXT, host)
            empty.setObjectName("emptyStateBody")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._add_row(empty)
            return

        for task in sorted(view.tasks, key=view_order_key):
            self._add_row(ArchiveTaskRow(task, self._categories, self._icon_provider, host))

    def _add_row(self, row: QWidget) -> None:
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
        self._rows.append(row)