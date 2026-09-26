"""Arabic task text with its priority badge kept beside the glyphs.

Short text stays content-sized, so leftover space remains on the physical
left. Long text is capped to the width the row actually has and wraps
there. The cluster never reports a large minimum width, so it cannot
force the task list to scroll horizontally.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLayout, QSizePolicy, QWidget

from app.core.models import TaskPriority
from app.ui.priority_presentation import configure_priority_badge


class ArabicTaskCluster(QWidget):
    """Physical left → right: optional badge, then right-aligned RTL text."""

    def __init__(
        self,
        text: str,
        priority: TaskPriority,
        completed: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._target = 80

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self._badge = QLabel(self)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        configure_priority_badge(self._badge, priority)

        self._text = QLabel(text, self)
        self._text.setWordWrap(True)
        self._text.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._text.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._text.setMinimumWidth(0)
        self._text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._apply_completed_style(completed)

        self._layout.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignVCenter)
        self._layout.addWidget(self._text, 1, Qt.AlignmentFlag.AlignVCenter)

    @property
    def text_label(self) -> QLabel:
        return self._text

    @property
    def badge(self) -> QLabel:
        return self._badge

    def sizeHint(self) -> QSize:  # noqa: N802 — Qt naming
        return QSize(self._target, self._preferred_height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802 — Qt naming
        return QSize(0, self._preferred_height())

    def set_text(self, text: str) -> None:
        self._text.setText(text)

    def set_completed(self, completed: bool) -> None:
        self._apply_completed_style(completed)

    def set_priority(self, priority: TaskPriority) -> None:
        resolved = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
        configure_priority_badge(self._badge, resolved)

    def fit(self, available: int) -> None:
        """Prefer the text width, but never ask for more than ``available``."""
        available = max(48, available)
        badge_w = self._badge_width()
        gap = self._layout.spacing() if badge_w else 0
        natural = self._single_line_width() + badge_w + gap
        self._target = min(available, natural)
        text_w = max(24, self._target - badge_w - gap)
        # Cap only. A minimum width here would widen the scroll area.
        self._text.setMaximumWidth(text_w)
        self.setMaximumWidth(self._target)
        self.updateGeometry()

    def _badge_width(self) -> int:
        if self._badge.isHidden():
            return 0
        return self._badge.sizeHint().width()

    def _preferred_height(self) -> int:
        badge_w = self._badge_width()
        gap = self._layout.spacing() if badge_w else 0
        text_w = max(24, self._target - badge_w - gap)
        text_h = self._text.heightForWidth(text_w)
        badge_h = 0 if self._badge.isHidden() else self._badge.sizeHint().height()
        return max(text_h, badge_h, 22)

    def _single_line_width(self) -> int:
        metrics = QFontMetrics(self._text.font())
        # Padding so Arabic shaping is not clipped when the line just fits.
        return metrics.horizontalAdvance(self._text.text()) + 16

    def _apply_completed_style(self, completed: bool) -> None:
        self._text.setObjectName("taskTextLabelCompleted" if completed else "taskTextLabel")
        style = self._text.style()
        if style is not None:
            style.unpolish(self._text)
            style.polish(self._text)
        self._text.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._text.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
