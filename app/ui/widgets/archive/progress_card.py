"""The archive's progress card: a ring and "N من M مكتملة"."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.styles.archive_style import CARD_PAD, PROGRESS_GAP, RING_SIZE
from app.ui.widgets.progress_ring import RingGraphic
from app.ui.widgets.progress_ring_state import create_progress_snapshot

__all__ = ["DayProgressCard"]


class DayProgressCard(QFrame):
    """How much of a past day's list was completed."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("archiveCard")

        self._ring = RingGraphic(RING_SIZE, self)

        self._title = QLabel(self)
        self._title.setObjectName("archiveProgressTitle")
        self._subtitle = QLabel(self)
        self._subtitle.setObjectName("archiveProgressSub")

        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(2)
        texts.addWidget(self._title)
        texts.addWidget(self._subtitle)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(CARD_PAD, CARD_PAD, CARD_PAD, CARD_PAD)
        layout.setSpacing(PROGRESS_GAP)
        layout.addWidget(self._ring, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(texts, 1)

    def show_progress(self, completed: int, total: int) -> None:
        snapshot = create_progress_snapshot(completed, total, past_day=True)
        self._ring.set_state(snapshot, snapshot.fraction)

        if snapshot.is_empty:
            self._title.setText("لا توجد مهام")
            self._subtitle.setText("")
            self._subtitle.hide()
            self.setAccessibleName("لا توجد مهام في هذا اليوم")
            return

        percent = round(snapshot.fraction * 100)
        self._title.setText(f"{snapshot.completed} من {snapshot.total} مكتملة")
        self._subtitle.setText(f"{percent}% من مهام هذا اليوم")
        self._subtitle.show()
        self.setAccessibleName(f"{snapshot.completed} من {snapshot.total}")