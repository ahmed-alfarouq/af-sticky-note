"""State-driven icon buttons for the top bar (v3 §4, §13.2).

An :class:`IconButton` is a fixed 36x36 tool button whose glyph comes from
the cached :mod:`app.ui.icons` provider; the color for each widget state is
picked here while backgrounds stay in QSS. No timers, no paint-path work:
the icon refreshes on hover enter/leave and enabled changes only.
"""
from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import QToolButton, QWidget

from app.ui.icons import icon


class IconButton(QToolButton):
    """36x36 icon button; the color per state is picked here, the background by QSS."""

    def __init__(
        self,
        key: str,
        idle: str = "#98A2B3",
        hover: str = "#F2F5F8",
        disabled: str = "#4A586B",
        size: int = 18,
        parent: Optional[QWidget] = None,
        button_size: int = 36,
    ) -> None:
        super().__init__(parent)
        self._key = key
        self._colors: Tuple[str, str, str] = (idle, hover, disabled)
        self._icon_size = size
        self.setFixedSize(button_size, button_size)
        self.setIconSize(QSize(size, size))
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._refresh()

    @property
    def icon_key(self) -> str:
        """The glyph key this button currently shows."""
        return self._key

    def set_icon_key(self, key: str) -> None:
        """Swap the shown glyph (e.g. pin outline <-> filled) and refresh."""
        self._key = key
        self._refresh()

    def set_state_colors(self, idle: str, hover: str, disabled: str) -> None:
        """Replace the per-state colors (e.g. amber pin states) and refresh."""
        self._colors = (idle, hover, disabled)
        self._refresh()

    def _refresh(self) -> None:
        idle, hover, disabled = self._colors
        if not self.isEnabled():
            color = disabled
        else:
            color = hover if self.underMouse() else idle
        self.setIcon(icon(self._key, color))

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._refresh()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._refresh()
        super().leaveEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.type() == QEvent.Type.EnabledChange:
            self._refresh()
        super().changeEvent(event)
