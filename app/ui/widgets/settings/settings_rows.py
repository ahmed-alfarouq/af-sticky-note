"""Building blocks of the settings screen: sections, groups, and rows."""

from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.icons import icon as vector_icon
from app.ui.styles.settings_style import (
    CHEVRON_SIZE,
    DIVIDER_COLOR,
    FOCUS_COLOR,
    FOCUS_WIDTH,
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

__all__ = ["ChoiceRow", "SettingsRow", "SettingsSection"]

_ACTIVATE_KEYS = (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)


class _ValueWithChevron(QWidget):
    """A muted value followed by a chevron (a row that leads somewhere)."""

    def __init__(self, value: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._text = QLabel(value, self)
        self._text.setObjectName("settingsRowValue")

        chevron = QLabel(self)
        chevron.setFixedSize(CHEVRON_SIZE, CHEVRON_SIZE)
        chevron.setPixmap(vector_icon("caret_left", MUTED_COLOR).pixmap(CHEVRON_SIZE, CHEVRON_SIZE))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(VALUE_GAP)
        layout.addWidget(self._text)
        layout.addWidget(chevron)

    def set_value(self, value: str) -> None:
        self._text.setText(value)

    def set_pressed(self, pressed: bool) -> None:
        """Brighten the value while its row is pressed."""
        self._text.setProperty("pressed", pressed)
        style = self._text.style()
        style.unpolish(self._text)
        style.polish(self._text)


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


class ChoiceRow(SettingsRow):
    """A row showing the current choice; pressing it asks to pick another."""

    clicked = Signal()

    def __init__(self, title: str, value: str = "", parent: Optional[QWidget] = None) -> None:
        shown = _ValueWithChevron(value)
        super().__init__(title, shown, parent=parent)
        self._shown = shown

        self.setAccessibleName(title)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Presses belong to the row, never to its inner labels.
        for child in self.findChildren(QWidget):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_value(self, value: str) -> None:
        self._shown.set_value(value)
        self.setAccessibleDescription(value)

    # -- Interaction --------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            self._shown.set_pressed(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            self._shown.set_pressed(False)
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        if event.key() in _ACTIVATE_KEYS:
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    # -- Focus ring ---------------------------------------------------------

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if not self.hasFocus():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QPen(QColor(FOCUS_COLOR), FOCUS_WIDTH))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            inset = FOCUS_WIDTH + 2
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(inset, inset, -inset, -inset), 10, 10)
        finally:
            painter.end()


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