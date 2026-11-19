"""The "اختيار يوم" chip: a calendar icon and a label that can be switched on."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from app.ui.icons import icon as vector_icon
from app.ui.styles.archive_style import (
    CHIP_BORDER_ON,
    CHIP_BORDER_WIDTH,
    CHIP_FILL,
    CHIP_FILL_ON,
    CHIP_GAP,
    CHIP_HEIGHT,
    CHIP_ICON,
    CHIP_PAD,
    CHIP_PX,
    CHIP_RADIUS,
    CHIP_TEXT,
    CHIP_TEXT_ON,
)
from app.ui.styles.screen_style import FOCUS_COLOR, FOCUS_WIDTH

__all__ = ["ArchiveChip"]


class ArchiveChip(QAbstractButton):
    """A checkable pill: on while the date picker is showing."""

    def __init__(self, text: str, icon_key: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(text)
        self._icon_key = icon_key
        self.setFixedHeight(CHIP_HEIGHT)

    def _font(self) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(CHIP_PX)
        return font

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        text_width = QFontMetrics(self._font()).horizontalAdvance(self.text())
        return QSize(2 * CHIP_PAD + CHIP_ICON + CHIP_GAP + text_width, CHIP_HEIGHT)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            on = self.isChecked()
            area = QRectF(self.rect())

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(CHIP_FILL_ON if on else CHIP_FILL))
            painter.drawRoundedRect(area, CHIP_RADIUS, CHIP_RADIUS)

            self._paint_border(painter, area, on)
            self._paint_content(painter, on)
        finally:
            painter.end()

    def _paint_border(self, painter: QPainter, area: QRectF, on: bool) -> None:
        if self.hasFocus():
            color, width = QColor(FOCUS_COLOR), FOCUS_WIDTH
        elif on:
            color, width = QColor(CHIP_BORDER_ON), CHIP_BORDER_WIDTH
        else:
            return
        painter.setPen(QPen(color, width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inset = width / 2
        painter.drawRoundedRect(area.adjusted(inset, inset, -inset, -inset), CHIP_RADIUS, CHIP_RADIUS)

    def _paint_content(self, painter: QPainter, on: bool) -> None:
        """Icon, then label (the icon is on the right in RTL, on the left in LTR)."""
        text_color = CHIP_TEXT_ON if on else CHIP_TEXT
        pixmap = vector_icon(self._icon_key, text_color).pixmap(CHIP_ICON, CHIP_ICON)
        text_width = QFontMetrics(self._font()).horizontalAdvance(self.text())
        top = (self.height() - CHIP_ICON) / 2

        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        icon_left = self.width() - CHIP_PAD - CHIP_ICON if rtl else CHIP_PAD
        text_left = icon_left - CHIP_GAP - text_width if rtl else icon_left + CHIP_ICON + CHIP_GAP

        painter.drawPixmap(round(icon_left), round(top), pixmap)
        painter.setFont(self._font())
        painter.setPen(QColor(text_color))
        painter.drawText(
            QRectF(text_left, 0, text_width, self.height()),
            Qt.AlignmentFlag.AlignCenter,
            self.text(),
        )