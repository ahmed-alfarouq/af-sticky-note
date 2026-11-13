"""Building blocks of the settings screen: sections, groups, and rows."""

from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.icons import icon as vector_icon
from app.ui.styles.settings_style import (
    CHEVRON_SIZE,
    DIVIDER_COLOR,
    GROUP_FILL,
    GROUP_RADIUS,
    MUTED_COLOR,
    PANEL_GAP,
    ROW_GAP,
    ROW_HINT_GAP,
    ROW_MIN_HEIGHT,
    ROW_PAD_H,
    VALUE_GAP,
)

__all__ = ["SettingsRow", "SettingsSection", "ValueWithChevron"]


class ValueWithChevron(QWidget):
    """A muted value followed by a chevron (a row that leads somewhere)."""

    def __init__(self, value: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        text = QLabel(value, self)
        text.setObjectName("settingsRowValue")

        chevron = QLabel(self)
        chevron.setFixedSize(CHEVRON_SIZE, CHEVRON_SIZE)
        chevron.setPixmap(vector_icon("caret_left", MUTED_COLOR).pixmap(CHEVRON_SIZE, CHEVRON_SIZE))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(VALUE_GAP)
        layout.addWidget(text)
        layout.addWidget(chevron)


class SettingsRow(QWidget):
    """A title (with an optional hint under it) and one control.

    In RTL the title is on the right and the control on the left.
    """

    def __init__(
        self,
        title: str,
        control: QWidget,
        hint: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(ROW_MIN_HEIGHT)

        label = QLabel(title, self)
        label.setObjectName("settingsRowTitle")

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(ROW_HINT_GAP)
        text_column.addStretch(1)
        text_column.addWidget(label)
        if hint:
            hint_label = QLabel(hint, self)
            hint_label.setObjectName("settingsRowHint")
            text_column.addWidget(hint_label)
        text_column.addStretch(1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(ROW_PAD_H, 0, ROW_PAD_H, 0)
        layout.setSpacing(ROW_GAP)
        layout.addLayout(text_column, 1)
        layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)


class _SettingsGroup(QWidget):
    """Rounded card of rows separated by hairline dividers."""

    def __init__(self, rows: Sequence[SettingsRow], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._rows: List[SettingsRow] = list(rows)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for row in self._rows:
            layout.addWidget(row)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(GROUP_FILL))
            painter.drawRoundedRect(QRectF(self.rect()), GROUP_RADIUS, GROUP_RADIUS)

            painter.setPen(QPen(QColor(DIVIDER_COLOR), 1))
            for row in self._rows[1:]:
                y = row.y()
                painter.drawLine(0, y, self.width(), y)
        finally:
            painter.end()


class SettingsSection(QWidget):
    """A small heading above a group of rows."""

    def __init__(
        self,
        title: str,
        rows: Sequence[SettingsRow],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        heading = QLabel(title, self)
        heading.setObjectName("settingsSection")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PANEL_GAP)
        layout.addWidget(heading)
        layout.addWidget(_SettingsGroup(rows, self))