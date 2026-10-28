from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from app.ui.icons import icon as vector_icon
from app.ui.styles.task_list_style import (
    FOCUS_COLOR,
    HEADER_CHEVRON_SIZE,
    HEADER_COLOR,
    HEADER_GAP,
    HEADER_PAD_H,
    HEADER_PAD_V,
)

__all__ = ["CompletedGroupHeader"]


class CompletedGroupHeader(QAbstractButton):
    """Flat, focusable header that toggles the completed group.

    A down chevron means expanded; a left chevron (RTL "collapsed") means
    collapsed. In RTL the chevron is rightmost, then 6 px, then the text.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("completedGroupHeader")
        self.setAccessibleName("مجموعة المهام المكتملة")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._chevron = QLabel(self)
        self._chevron.setFixedSize(HEADER_CHEVRON_SIZE, HEADER_CHEVRON_SIZE)
        self._chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._text = QLabel(self)
        self._text.setObjectName("completedGroupText")
        self._text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(HEADER_PAD_H, HEADER_PAD_V, HEADER_PAD_H, HEADER_PAD_V)
        layout.setSpacing(HEADER_GAP)
        layout.addWidget(self._chevron, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

    def set_state(self, count: int, expanded: bool) -> None:
        """Show "مكتملة · count" with the matching chevron."""
        self._text.setText(f"مكتملة · {count}")

        key = "caret_down" if expanded else "caret_left"
        pixmap = vector_icon(key, HEADER_COLOR).pixmap(
            HEADER_CHEVRON_SIZE, HEADER_CHEVRON_SIZE
        )
        self._chevron.setPixmap(pixmap)

        self.setAccessibleDescription(
            f"{count} مكتملة، {'موسّعة' if expanded else 'مطوية'}"
        )

    # A QAbstractButton ignores its layout for sizing, so forward it.
    def sizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        layout = self.layout()
        if layout is not None:
            return layout.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        layout = self.layout()
        if layout is not None:
            return layout.minimumSize()
        return super().minimumSizeHint()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        # Flat by design: only a keyboard focus ring is ever drawn.
        if not self.hasFocus():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QPen(QColor(FOCUS_COLOR), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 6, 6)
        finally:
            painter.end()
