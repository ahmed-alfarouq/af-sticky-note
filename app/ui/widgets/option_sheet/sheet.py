"""Bottom sheet that lets the user pick one option.

A modal overlay on top of its host (the paper surface): the content behind
is dimmed and a rounded sheet sits at the bottom with a grabber, a title and
the options. The dim fades in while the sheet slides up; closing plays the
same motion in reverse. Choosing a row, clicking the dimmed area, or pressing
Escape closes it. The sheet knows nothing about categories or priorities:
callers pass :class:`SheetOption` rows and a callback.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtGui import QColor, QContextMenuEvent, QKeyEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.sheet_presentation import SheetOption
from app.ui.styles.app_style import COLOR_STICKY_PAPER
from app.ui.styles.option_sheet_style import (
    DIM_OPACITY,
    GRABBER_GAP_BELOW,
    GRABBER_HEIGHT,
    GRABBER_WIDTH,
    OPTION_MIN_HEIGHT,
    OVERLAY_INSET,
    SHEET_CLOSE_MS,
    SHEET_OPEN_MS,
    SHEET_PAD_BOTTOM,
    SHEET_PAD_SIDE,
    SHEET_PAD_TOP,
    SHEET_SHADOW_ALPHA,
    SHEET_SHADOW_BLUR,
    SHEET_SHADOW_OFFSET_Y,
    SHEET_SPACING,
    TITLE_MARGINS,
)
from app.ui.widgets.option_sheet.option_button import IconSource, OptionButton

__all__ = ["OptionSheet"]


class OptionSheet(QWidget):
    """Modal bottom sheet covering its host widget."""

    def __init__(self, host: QWidget, icon_source: IconSource) -> None:
        super().__init__(host)
        self._icon_source = icon_source
        self.setObjectName("optionSheetOverlay")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._buttons: List[OptionButton] = []
        self._on_chosen: Optional[Callable[[str], None]] = None
        self._on_closed: Optional[Callable[[], None]] = None
        self._return_focus: Optional[QWidget] = None

        self._dim_progress = 0.0  # 0 = no dim, 1 = full dim
        self._animation: Optional[QParallelAnimationGroup] = None
        self._closing = False

        self._build()
        host.installEventFilter(self)  # keep covering the host when it resizes
        self.hide()

    # -- Construction -------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(*(OVERLAY_INSET,) * 4)
        root.setSpacing(0)
        root.addStretch(1)  # keeps the sheet at the bottom

        self._sheet = QFrame(self)
        self._sheet.setObjectName("optionSheet")
        shadow = QGraphicsDropShadowEffect(self._sheet)
        shadow.setBlurRadius(SHEET_SHADOW_BLUR)
        shadow.setOffset(0, SHEET_SHADOW_OFFSET_Y)
        shadow.setColor(QColor(0, 0, 0, SHEET_SHADOW_ALPHA))
        self._sheet.setGraphicsEffect(shadow)
        root.addWidget(self._sheet)

        layout = QVBoxLayout(self._sheet)
        layout.setContentsMargins(
            SHEET_PAD_SIDE, SHEET_PAD_TOP, SHEET_PAD_SIDE, SHEET_PAD_BOTTOM
        )
        layout.setSpacing(SHEET_SPACING)

        grabber = QFrame(self._sheet)
        grabber.setObjectName("optionSheetGrabber")
        grabber.setFixedSize(GRABBER_WIDTH, GRABBER_HEIGHT)
        layout.addWidget(grabber, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(GRABBER_GAP_BELOW)

        self._title = QLabel(self._sheet)
        self._title.setObjectName("optionSheetTitle")
        self._title.setContentsMargins(*TITLE_MARGINS)
        layout.addWidget(self._title)

        self._options_host = QWidget()
        self._options_host.setObjectName("optionSheetOptions")
        self._options_layout = QVBoxLayout(self._options_host)
        self._options_layout.setContentsMargins(0, 0, 0, 0)
        self._options_layout.setSpacing(SHEET_SPACING)

        self._scroll = QScrollArea(self._sheet)
        self._scroll.setObjectName("optionSheetScroll")
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.setWidget(self._options_host)
        layout.addWidget(self._scroll)

    # -- Public API ---------------------------------------------------------

    def is_open(self) -> bool:
        return self.isVisible() and not self._closing

    def present(
        self,
        title: str,
        options: Sequence[SheetOption],
        selected_key: str,
        *,
        on_chosen: Callable[[str], None],
        on_closed: Optional[Callable[[], None]] = None,
        return_focus: Optional[QWidget] = None,
    ) -> None:
        """Show the sheet; ``on_chosen(key)`` runs when a row is picked.

        ``on_closed`` runs on every close (picked or dismissed), and focus
        returns to ``return_focus`` afterwards.
        """
        if self.isVisible():
            self._finish_hide()  # drop any previous session without motion

        self._on_chosen = on_chosen
        self._on_closed = on_closed
        self._return_focus = return_focus

        self._title.setText(title)
        self.setAccessibleName(title)
        self._rebuild_options(options, selected_key)

        self._cover_host()
        self._fit_options_height()
        self.raise_()
        self.show()
        self._fit_options_height()  # again: fonts are only resolved once shown
        self._focus_initial()
        self._animate(opening=True)

    def close_sheet(self) -> None:
        """Dismiss without choosing."""
        self._close(restore_focus=True)

    # -- Options ------------------------------------------------------------

    def _rebuild_options(
        self, options: Sequence[SheetOption], selected_key: str
    ) -> None:
        for button in self._buttons:
            self._options_layout.removeWidget(button)
            button.deleteLater()
        self._buttons = []

        for option in options:
            button = OptionButton(
                option, option.key == selected_key, self._icon_source, self._options_host
            )
            button.clicked.connect(lambda _checked=False, key=option.key: self._choose(key))
            button.navigate.connect(self._navigate)
            self._options_layout.addWidget(button)
            self._buttons.append(button)

    def _fit_options_height(self) -> None:
        """Give the options exactly the height they need, up to what is free.

        All rows are always laid out at full height; when the host is too
        short to show them all, the options scroll instead of shrinking.
        """
        if not self._buttons:
            self._scroll.setFixedHeight(0)
            return

        rows = sum(max(b.sizeHint().height(), OPTION_MIN_HEIGHT) for b in self._buttons)
        gaps = SHEET_SPACING * (len(self._buttons) - 1)
        content_height = rows + gaps
        self._options_host.setMinimumHeight(content_height)

        free_height = self.height() - 2 * OVERLAY_INSET - self._chrome_height()
        self._scroll.setFixedHeight(max(OPTION_MIN_HEIGHT, min(content_height, free_height)))

    def _chrome_height(self) -> int:
        """Height of everything in the sheet except the options."""
        margins = self._sheet.layout().contentsMargins()
        fixed = GRABBER_HEIGHT + GRABBER_GAP_BELOW + self._title.sizeHint().height()
        gaps = 3 * SHEET_SPACING  # grabber-spacer, spacer-title, title-options
        return margins.top() + margins.bottom() + fixed + gaps

    def _focus_initial(self) -> None:
        target = next((b for b in self._buttons if b.is_selected()), None)
        if target is None and self._buttons:
            target = self._buttons[0]
        if target is not None:
            target.setFocus()
            self._scroll.ensureWidgetVisible(target)

    def _navigate(self, key: Qt.Key) -> None:
        if not self._buttons:
            return
        buttons = self._buttons
        current = next((i for i, b in enumerate(buttons) if b.hasFocus()), 0)

        if key == Qt.Key.Key_Home:
            index = 0
        elif key == Qt.Key.Key_End:
            index = len(buttons) - 1
        elif key == Qt.Key.Key_Up:
            index = (current - 1) % len(buttons)
        else:
            index = (current + 1) % len(buttons)

        buttons[index].setFocus()
        self._scroll.ensureWidgetVisible(buttons[index])

    # -- Choosing / closing -------------------------------------------------

    def _choose(self, key: str) -> None:
        on_chosen = self._on_chosen
        self._close(restore_focus=True)
        if on_chosen is not None:
            on_chosen(key)

    def _close(self, *, restore_focus: bool) -> None:
        """Run close callbacks now, then slide the sheet away and hide."""
        if self._closing or not self.isVisible():
            return

        on_closed, self._on_closed = self._on_closed, None
        focus, self._return_focus = self._return_focus, None
        self._on_chosen = None

        if restore_focus and focus is not None:
            try:
                focus.setFocus()
            except RuntimeError:
                pass  # the trigger went away with its window
        if on_closed is not None:
            on_closed()

        self._animate(opening=False)

    def _finish_hide(self) -> None:
        self._stop_animation()
        self._closing = False
        self.hide()

    # -- Motion -------------------------------------------------------------

    def _get_dim_progress(self) -> float:
        return self._dim_progress

    def _set_dim_progress(self, value: float) -> None:
        self._dim_progress = value
        self.update()

    dimProgress = Property(float, _get_dim_progress, _set_dim_progress)

    def _stop_animation(self) -> None:
        if self._animation is not None:
            self._animation.stop()
            self._animation.deleteLater()
            self._animation = None

    def _animate(self, *, opening: bool) -> None:
        """Fade the dim and slide the sheet between 'below the host' and rest."""
        self._stop_animation()
        # Force a layout pass so the sheet is at its resting position (a
        # previous close left it below the overlay).
        self.layout().invalidate()
        self.layout().activate()

        rest = self._sheet.pos()
        hidden = QPoint(rest.x(), self.height())  # just below the overlay
        start, end = (hidden, rest) if opening else (rest, hidden)
        dim_start, dim_end = (0.0, 1.0) if opening else (self._dim_progress, 0.0)
        duration = SHEET_OPEN_MS if opening else SHEET_CLOSE_MS
        curve = QEasingCurve.Type.OutCubic if opening else QEasingCurve.Type.InCubic

        slide = QPropertyAnimation(self._sheet, b"pos")
        slide.setStartValue(start)
        slide.setEndValue(end)

        fade = QPropertyAnimation(self, b"dimProgress")
        fade.setStartValue(dim_start)
        fade.setEndValue(dim_end)

        group = QParallelAnimationGroup(self)
        for animation in (slide, fade):
            animation.setDuration(duration)
            animation.setEasingCurve(curve)
            group.addAnimation(animation)

        self._closing = not opening
        if not opening:
            group.finished.connect(self._finish_hide)

        self._sheet.move(start)
        self._set_dim_progress(dim_start)
        self._animation = group
        group.start()

    # -- Covering the host --------------------------------------------------

    def _cover_host(self) -> None:
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._cover_host()
            if self.isVisible() and not self._closing:
                self._fit_options_height()
        return super().eventFilter(watched, event)

    # -- Painting and input -------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        dim = QColor(COLOR_STICKY_PAPER)
        dim.setAlphaF(DIM_OPACITY * self._dim_progress)
        painter = QPainter(self)
        try:
            painter.fillRect(self.rect(), dim)
        finally:
            painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        # The overlay is modal: every press is consumed; one outside the
        # sheet dismisses it.
        if not self._closing and not self._sheet.geometry().contains(
            event.position().toPoint()
        ):
            self.close_sheet()
        event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        event.accept()  # no window menu behind a modal sheet

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt naming
        if event.key() == Qt.Key.Key_Escape and not self._closing:
            self.close_sheet()
        event.accept()