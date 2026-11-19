"""A full screen (settings, archive) that replaces the home page.

The screen slides in from the left while the home page slides out to the
right, and "back" plays it in reverse. Nothing fades. The motion is a
snapshot transition (see :mod:`transition`), so no live widget is moved.

A subclass supplies its content with :meth:`set_body` and may refresh it in
:meth:`_prepare_open`, which runs just before the screen appears.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.styles.screen_style import (
    BACK_BUTTON_SIZE,
    BACK_ICON_COLOR,
    BACK_ICON_HOVER,
    BACK_ICON_SIZE,
    CLOSE_SLIDE_MS,
    NAV_GAP,
    OPEN_SLIDE_MS,
    PANEL_GAP,
    PANEL_MARGINS,
)
from app.ui.widgets.icon_button import IconButton
from app.ui.widgets.screens.transition import PageTransition, Sprite

__all__ = ["ScreenPanel"]

_AT_REST = QPoint(0, 0)


class ScreenPanel(QWidget):
    """Frame of a full screen: a nav row (back, title, optional extra) and a body."""

    def __init__(
        self,
        host: QWidget,
        home: QWidget,
        title: str,
        nav_trailing: Optional[QWidget] = None,
    ) -> None:
        super().__init__(host)
        self.setObjectName("screenPanel")
        self.setAccessibleName(title)

        self._host = host
        self._home = home
        self._return_focus: Optional[QWidget] = None
        self._busy = False
        self._entering = False

        self._transition = PageTransition(host)
        self._transition.finished.connect(self._on_transition_finished)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(*PANEL_MARGINS)
        self._layout.setSpacing(PANEL_GAP)
        self._layout.addWidget(self._build_nav(title, nav_trailing))

        host.installEventFilter(self)  # keep covering the host when it resizes
        self.hide()

    # -- Construction -------------------------------------------------------

    def _build_nav(self, title: str, trailing: Optional[QWidget]) -> QWidget:
        nav = QWidget(self)

        self._back = IconButton(
            "arrow_right",
            idle=BACK_ICON_COLOR,
            hover=BACK_ICON_HOVER,
            size=BACK_ICON_SIZE,
            button_size=BACK_BUTTON_SIZE,
            parent=nav,
        )
        self._back.setObjectName("screenBackButton")
        self._back.setAccessibleName("رجوع")
        self._back.setToolTip("رجوع")
        self._back.clicked.connect(self.close_panel)

        heading = QLabel(title, nav)
        heading.setObjectName("screenTitle")

        layout = QHBoxLayout(nav)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(NAV_GAP)
        layout.addWidget(self._back)
        layout.addWidget(heading)
        layout.addStretch(1)
        if trailing is not None:
            layout.addWidget(trailing)
        return nav

    def set_body(self, body: QWidget) -> None:
        """Put the screen's content under the nav row."""
        self._layout.addWidget(body, 1)

    def _prepare_open(self) -> None:
        """Refresh the content just before the screen appears."""

    # -- Opening and closing ------------------------------------------------

    def is_open(self) -> bool:
        return self.isVisible() or (self._busy and self._entering)

    def open(self, return_focus: Optional[QWidget] = None) -> None:
        """Replace the home page with this screen."""
        if self.isVisible() or self._busy:
            return

        self._return_focus = return_focus
        self._prepare_open()

        self._cover_host()
        self._layout.activate()  # the content needs its final places to be captured
        self.show()
        sprites = self._opening_sprites()
        self.hide()
        self._home.hide()  # the transition now stands in for both screens

        self._play(sprites, entering=True)

    def close_panel(self) -> None:
        """Bring the home page back."""
        if not self.isVisible() or self._busy:
            return

        sprites = self._closing_sprites()
        self.hide()  # the transition now stands in for both screens

        self._play(sprites, entering=False)

    def _play(self, sprites: List[Sprite], *, entering: bool) -> None:
        self._busy = True
        self._entering = entering
        self._transition.play(sprites)

    def _on_transition_finished(self) -> None:
        self._busy = False
        if self._entering:
            self.show()
            self._back.setFocus()
        else:
            self._home.show()
            focus, self._return_focus = self._return_focus, None
            if focus is not None:
                focus.setFocus()

    # -- Snapshots ----------------------------------------------------------

    def _origin_of(self, widget: QWidget) -> QPoint:
        """Where ``widget`` sits in the host's coordinates."""
        return widget.mapTo(self._host, QPoint(0, 0))

    @staticmethod
    def _slide(
        widget: QWidget,
        origin: QPoint,
        start: QPoint,
        end: QPoint,
        duration_ms: int,
    ) -> Sprite:
        """A snapshot of ``widget`` that slides from ``start`` to ``end`` offset."""
        return Sprite(
            pixmap=widget.grab(),
            origin=origin,
            offset=(start, end),
            duration_ms=duration_ms,
            curve=QEasingCurve.Type.InOutCubic,
        )

    def _opening_sprites(self) -> List[Sprite]:
        """This screen slides in from the left; home slides out to the right."""
        width = QPoint(self._host.width(), 0)
        return [
            self._slide(self._home, self._origin_of(self._home), _AT_REST, width, OPEN_SLIDE_MS),
            self._slide(self, QPoint(0, 0), -width, _AT_REST, OPEN_SLIDE_MS),
        ]

    def _closing_sprites(self) -> List[Sprite]:
        """This screen slides out to the left; home slides back in from the right."""
        width = QPoint(self._host.width(), 0)

        # The home page was hidden while this screen was open: lay it out again
        # (the window may have been resized meanwhile) before capturing it.
        self._home.show()
        layout = self._host.layout()
        if layout is not None:
            layout.activate()
        home = self._slide(self._home, self._origin_of(self._home), width, _AT_REST, CLOSE_SLIDE_MS)
        self._home.hide()

        panel = self._slide(self, QPoint(0, 0), _AT_REST, -width, CLOSE_SLIDE_MS)
        return [home, panel]

    # -- Covering the host --------------------------------------------------

    def _cover_host(self) -> None:
        self.setGeometry(self._host.rect())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self._host and event.type() == QEvent.Type.Resize:
            self._cover_host()
        return super().eventFilter(watched, event)

    # -- Input --------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        if event.key() == Qt.Key.Key_Escape:
            self.close_panel()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 - Qt naming
        event.accept()  # no window menu over a full screen