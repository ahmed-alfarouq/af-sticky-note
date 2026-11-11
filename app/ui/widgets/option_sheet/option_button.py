"""One selectable row of the bottom option sheet."""

from __future__ import annotations

from typing import Optional, Protocol

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import icon as vector_icon
from app.ui.sheet_presentation import MarkerShape, SheetOption
from app.ui.styles.option_sheet_style import (
    CHECK_COLOR,
    CHECK_SIZE,
    MARKER_SIZE,
    MARKER_SQUARE_RADIUS,
    OPTION_BORDER,
    OPTION_FILL,
    OPTION_FOCUS_BORDER,
    OPTION_GAP,
    OPTION_HINT_GAP,
    OPTION_ICON_SIZE,
    OPTION_MIN_HEIGHT,
    OPTION_PAD_H,
    OPTION_RADIUS,
    OPTION_SELECTED_BORDER,
    OPTION_SELECTED_FILL,
)

__all__ = ["OptionButton"]

_NAVIGATION_KEYS = (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Home, Qt.Key.Key_End)
_ACTIVATE_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter)


class IconSource(Protocol):
    """Anything that resolves an icon key to an icon (e.g. the category icons)."""

    def icon_for_key(self, icon_key: str) -> QIcon: ...


class _IconMarker(QLabel):
    """A row's icon marker."""

    def __init__(self, icon: QIcon, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(QSize(OPTION_ICON_SIZE, OPTION_ICON_SIZE))
        self.setPixmap(icon.pixmap(OPTION_ICON_SIZE, OPTION_ICON_SIZE))


class _Marker(QWidget):
    """Small colored square or circle, painted directly."""

    def __init__(
        self, color: str, shape: MarkerShape, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._shape = shape
        self.setFixedSize(QSize(MARKER_SIZE, MARKER_SIZE))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._color)
            area = QRectF(self.rect())
            if self._shape is MarkerShape.CIRCLE:
                painter.drawEllipse(area)
            else:
                painter.drawRoundedRect(area, MARKER_SQUARE_RADIUS, MARKER_SQUARE_RADIUS)
        finally:
            painter.end()


class OptionButton(QAbstractButton):
    """Marker, label, optional hint, and a check mark when selected.

    The row paints its own rounded background: blue border and fill when
    selected, a soft border while it holds keyboard focus.
    """

    #: Arrow/Home/End/Tab pressed: the sheet moves focus between rows.
    navigate = Signal(object)  # Qt.Key

    def __init__(
        self,
        option: SheetOption,
        selected: bool,
        icon_source: IconSource,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._key = option.key
        self._selected = selected

        self._row = QHBoxLayout(self)
        self.setObjectName("optionButton")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName(option.label)
        if option.hint:
            self.setAccessibleDescription(option.hint)

        self._build(option, icon_source)

    @property
    def key(self) -> str:
        return self._key

    def is_selected(self) -> bool:
        return self._selected

    # -- Construction -------------------------------------------------------

    def _build(self, option: SheetOption, icon_source: IconSource) -> None:
        layout = self._row
        layout.setContentsMargins(OPTION_PAD_H, 0, OPTION_PAD_H, 0)
        layout.setSpacing(OPTION_GAP)

        layout.addWidget(
            self._make_marker(option, icon_source), 0, Qt.AlignmentFlag.AlignVCenter
        )
        layout.addLayout(self._build_text(option), 1)

        if self._selected:
            check = QLabel(self)
            check.setFixedSize(CHECK_SIZE, CHECK_SIZE)
            check.setPixmap(vector_icon("check", CHECK_COLOR).pixmap(CHECK_SIZE, CHECK_SIZE))
            layout.addWidget(check, 0, Qt.AlignmentFlag.AlignVCenter)

        # Clicks belong to the row, never to its inner labels.
        for child in self.findChildren(QWidget):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def _make_marker(self, option: SheetOption, icon_source: IconSource) -> QWidget:
        if option.icon_key:
            return _IconMarker(icon_source.icon_for_key(option.icon_key), self)
        return _Marker(option.marker_color, option.marker_shape, self)

    def _build_text(self, option: SheetOption) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(OPTION_HINT_GAP)
        column.addStretch(1)

        label = QLabel(option.label, self)
        label.setObjectName("optionLabel")
        column.addWidget(label)

        if option.hint:
            hint = QLabel(option.hint, self)
            hint.setObjectName("optionHint")
            column.addWidget(hint)

        column.addStretch(1)
        return column

    # -- Sizing (a QAbstractButton ignores its layout, so forward it) -------

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        hint = self._row.sizeHint()
        return QSize(hint.width(), max(hint.height(), OPTION_MIN_HEIGHT))

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        hint = self._row.minimumSize()
        return QSize(hint.width(), max(hint.height(), OPTION_MIN_HEIGHT))

    # -- Keyboard -----------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        key = event.key()
        if key in _NAVIGATION_KEYS:
            self.navigate.emit(key)
            event.accept()
        elif key in _ACTIVATE_KEYS:
            self.click()
            event.accept()
        else:
            super().keyPressEvent(event)

    def focusNextPrevChild(self, forward: bool) -> bool:  # noqa: N802 - Qt naming
        # Tab / Shift+Tab stay inside the sheet.
        self.navigate.emit(Qt.Key.Key_Down if forward else Qt.Key.Key_Up)
        return True

    # -- Painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            border = self._border_color()
            painter.setPen(QPen(border, OPTION_BORDER) if border else Qt.PenStyle.NoPen)
            painter.setBrush(QColor(OPTION_SELECTED_FILL if self._selected else OPTION_FILL))

            inset = OPTION_BORDER / 2
            area = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
            painter.drawRoundedRect(area, OPTION_RADIUS, OPTION_RADIUS)
        finally:
            painter.end()

    def _border_color(self) -> Optional[QColor]:
        if self.hasFocus():
            return QColor(OPTION_FOCUS_BORDER)
        if self._selected:
            return QColor(OPTION_SELECTED_BORDER)
        return None
    