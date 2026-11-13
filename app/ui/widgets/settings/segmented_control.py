"""Segmented control: a pill of labels with an animated sliding highlight."""

from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtCore import QEasingCurve, QEvent, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui.styles.settings_style import (
    FOCUS_COLOR,
    FOCUS_WIDTH,
    SEG_ACTIVE,
    SEG_GAP,
    SEG_HEIGHT,
    SEG_MS,
    SEG_PAD,
    SEG_PAD_H,
    SEG_RADIUS,
    SEG_TEXT_ACTIVE,
    SEG_TEXT_IDLE,
    SEG_TEXT_PX,
    SEG_TRACK,
    SEG_TRACK_RADIUS,
)
from app.ui.widgets.settings.blend import blend

__all__ = ["SegmentedControl"]


class SegmentedControl(QWidget):
    """Pick one of a few labels; the highlight glides to the chosen one.

    Segments follow the layout direction (in RTL the first label is the
    rightmost). Arrow keys move the selection; a click selects directly.
    """

    selection_changed = Signal(int)

    def __init__(
        self,
        labels: Sequence[str],
        current: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._labels = list(labels)
        self._current = max(0, min(current, len(self._labels) - 1))
        self._widths: List[int] = []
        self._font = QFont(self.font())
        self._highlight = QRectF()

        self._animation = QVariantAnimation(self)
        self._animation.setDuration(SEG_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._on_highlight_changed)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._measure()

    def current_index(self) -> int:
        return self._current

    # -- Geometry -----------------------------------------------------------

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        content = sum(self._widths) + SEG_GAP * max(0, len(self._widths) - 1)
        return QSize(content + 2 * SEG_PAD, SEG_HEIGHT + 2 * SEG_PAD)

    def _measure(self) -> None:
        """Size every segment from its label (fonts resolve after polish)."""
        self._font = QFont(self.font())
        self._font.setPixelSize(SEG_TEXT_PX)
        metrics = QFontMetrics(self._font)
        self._widths = [metrics.horizontalAdvance(label) + 2 * SEG_PAD_H for label in self._labels]

        self.setFixedSize(self.sizeHint())
        self._animation.stop()
        self._highlight = self._segment_rect(self._current)
        self.update()

    def _segment_rect(self, index: int) -> QRectF:
        left = SEG_PAD + sum(self._widths[:index]) + SEG_GAP * index
        rect = QRectF(left, SEG_PAD, self._widths[index], SEG_HEIGHT)
        if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            rect.moveLeft(self.width() - rect.right())
        return rect

    def _on_highlight_changed(self, value) -> None:
        self._highlight = value
        self.update()

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt naming
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._measure()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().showEvent(event)
        self._measure()

    # -- Selection ----------------------------------------------------------

    def _select(self, index: int) -> None:
        if index == self._current or not 0 <= index < len(self._labels):
            return
        self._current = index
        self._animation.stop()
        self._animation.setStartValue(self._highlight)
        self._animation.setEndValue(self._segment_rect(index))
        self._animation.start()
        self.selection_changed.emit(index)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        point = event.position()
        for index in range(len(self._labels)):
            if self._segment_rect(index).contains(point):
                self._select(index)
                break
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        key = event.key()
        if key not in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            super().keyPressEvent(event)
            return

        # Visual left is the next segment in RTL and the previous one in LTR.
        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        step = 1 if (key == Qt.Key.Key_Left) == rtl else -1
        self._select(self._current + step)
        event.accept()

    # -- Painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            track = QRectF(self.rect())

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(SEG_TRACK))
            painter.drawRoundedRect(track, SEG_TRACK_RADIUS, SEG_TRACK_RADIUS)

            painter.setBrush(QColor(SEG_ACTIVE))
            painter.drawRoundedRect(self._highlight, SEG_RADIUS, SEG_RADIUS)

            self._paint_labels(painter)

            if self.hasFocus():
                painter.setPen(QPen(QColor(FOCUS_COLOR), FOCUS_WIDTH))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                inset = FOCUS_WIDTH / 2
                painter.drawRoundedRect(
                    track.adjusted(inset, inset, -inset, -inset),
                    SEG_TRACK_RADIUS,
                    SEG_TRACK_RADIUS,
                )
        finally:
            painter.end()

    def _paint_labels(self, painter: QPainter) -> None:
        """Each label fades to white as the highlight covers its segment."""
        painter.setFont(self._font)
        idle, active = QColor(SEG_TEXT_IDLE), QColor(SEG_TEXT_ACTIVE)

        for index, label in enumerate(self._labels):
            rect = self._segment_rect(index)
            covered = rect.intersected(self._highlight).width() / rect.width()
            painter.setPen(blend(idle, active, covered))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)