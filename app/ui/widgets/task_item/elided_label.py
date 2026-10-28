"""Single-line label that elides overlong text instead of wrapping."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

__all__ = ["ElidedLabel"]


class ElidedLabel(QLabel):
    """One-line label that shrinks to any width and elides at the end.

    The full text is kept separately (``full_text``) so the stored value is
    never altered by display elision. A zero minimum width lets long titles
    shrink with the row instead of forcing the whole list wider.
    """

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._full_text = ""
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.set_full_text(text)

    def full_text(self) -> str:
        return self._full_text

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self._elide()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        return QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 - Qt naming
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._elide()

    def _elide(self) -> None:
        elided = self.fontMetrics().elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            max(self.width(), 0),
        )
        if elided != self.text():
            self.setText(elided)