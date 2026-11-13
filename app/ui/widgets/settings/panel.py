"""The settings screen.

A panel that slides in over the home page (which fades out beneath it) and
slides away again on "back". Its sections stagger in as it arrives.

Only the "start with Windows" switch does anything; every other control
animates and keeps its state while the panel is open, but is not connected to
any setting yet.
"""

from __future__ import annotations

import logging
from typing import List, Optional, cast

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QParallelAnimationGroup, QPoint, QPropertyAnimation, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.platform.interfaces import StartupManager
from app.ui.styles.settings_style import (
    BACK_BUTTON_SIZE,
    BACK_ICON_COLOR,
    BACK_ICON_HOVER,
    BACK_ICON_SIZE,
    NAV_GAP,
    PANEL_CLOSE_MS,
    PANEL_GAP,
    PANEL_MARGINS,
    PANEL_OPEN_MS,
    PANEL_SLIDE_OFFSET,
)
from app.ui.widgets.icon_button import IconButton
from app.ui.widgets.settings.reveal import Reveal
from app.ui.widgets.settings.segmented_control import SegmentedControl
from app.ui.widgets.settings.settings_rows import SettingsRow, SettingsSection, ValueWithChevron
from app.ui.widgets.settings.toggle_switch import ToggleSwitch

__all__ = ["SettingsPanel"]

logger = logging.getLogger(__name__)

STARTUP_TITLE = "تشغيل مع بدء تشغيل Windows"
STARTUP_DESCRIPTION = "تشغيل تطبيق الملاحظة اليومية تلقائياً عند تسجيل الدخول إلى Windows"


def _switch_row(title: str, on: bool, hint: str = "") -> tuple[SettingsRow, ToggleSwitch]:
    switch = ToggleSwitch()
    switch.setAccessibleName(title)
    switch.set_checked_silently(on, animate=False)
    return SettingsRow(title, switch, hint), switch


def _segment_row(title: str, labels: List[str]) -> SettingsRow:
    control = SegmentedControl(labels)
    control.setAccessibleName(title)
    return SettingsRow(title, control)


def _value_row(title: str, value: str) -> SettingsRow:
    return SettingsRow(title, ValueWithChevron(value))


class SettingsPanel(QWidget):
    """Settings screen covering ``host``; swaps with the ``home`` page."""

    def __init__(
        self,
        host: QWidget,
        home: QWidget,
        startup_manager: StartupManager,
    ) -> None:
        super().__init__(host)
        self.setObjectName("settingsPanel")
        self.setAccessibleName("الإعدادات")

        self._home = home
        self._startup_manager = startup_manager
        self._return_focus: Optional[QWidget] = None
        self._animation: Optional[QParallelAnimationGroup] = None

        self._build()
        self._reveal = Reveal([self._nav, *self._sections], self)

        host.installEventFilter(self)  # keep covering the host when it resizes
        self.hide()

    # -- Construction -------------------------------------------------------

    def _build(self) -> None:
        self._nav = self._build_nav()
        self._startup_switch: ToggleSwitch
        self._sections = self._build_sections()

        content = QWidget()
        content.setObjectName("settingsContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(PANEL_GAP)
        for section in self._sections:
            content_layout.addWidget(section)
        content_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setObjectName("settingsScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        self._layout = layout
        layout.setContentsMargins(*PANEL_MARGINS)
        layout.setSpacing(PANEL_GAP)
        layout.addWidget(self._nav)
        layout.addWidget(scroll, 1)

    def _build_nav(self) -> QWidget:
        nav = QWidget(self)

        self._back = IconButton(
            "arrow_right",
            idle=BACK_ICON_COLOR,
            hover=BACK_ICON_HOVER,
            size=BACK_ICON_SIZE,
            button_size=BACK_BUTTON_SIZE,
            parent=nav,
        )
        self._back.setObjectName("settingsBackButton")
        self._back.setAccessibleName("رجوع")
        self._back.setToolTip("رجوع")
        self._back.clicked.connect(self.close_panel)

        title = QLabel("الإعدادات", nav)
        title.setObjectName("settingsTitle")

        layout = QHBoxLayout(nav)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(NAV_GAP)
        layout.addWidget(self._back)
        layout.addWidget(title)
        layout.addStretch(1)
        return nav

    def _build_sections(self) -> List[SettingsSection]:
        startup_row, self._startup_switch = _switch_row(STARTUP_TITLE, on=False)
        self._startup_switch.setAccessibleDescription(STARTUP_DESCRIPTION)
        self._startup_switch.toggled.connect(self._on_startup_toggled)

        return [
            SettingsSection(
                "التقويم",
                [
                    _segment_row("التقويم الأساسي", ["هجري", "ميلادي"]),
                    _value_row("أول يوم في الأسبوع", "السبت"),
                ],
            ),
            SettingsSection(
                "المهام",
                [
                    _value_row("التصنيف الافتراضي", "عام"),
                    _value_row("الأولوية الافتراضية", "عادي"),
                    _switch_row("أرشفة المكتملة تلقائياً", on=True, hint="بعد يوم واحد")[0],
                ],
            ),
            SettingsSection(
                "العرض",
                [
                    _segment_row("المظهر", ["داكن", "فاتح", "تلقائي"]),
                    _switch_row("الرسالة اليومية", on=True)[0],
                    _switch_row("تثبيت النافذة", on=True)[0],
                    startup_row,
                ],
            ),
        ]

    # -- Start with Windows (the one working setting) -----------------------

    def _sync_startup(self) -> None:
        """Show the current startup state, without animating or emitting."""
        try:
            enabled = self._startup_manager.is_enabled()
        except Exception as exc:
            logger.error("Failed to query startup manager state: %s", exc)
            enabled = False
        self._startup_switch.set_checked_silently(enabled, animate=False)

    def _on_startup_toggled(self, checked: bool) -> None:
        try:
            success = (
                self._startup_manager.enable() if checked else self._startup_manager.disable()
            )
            if not success:
                self._revert_startup(checked)
                QMessageBox.warning(
                    self,
                    "خطأ في الإعدادات",
                    "تعذر تعديل إعداد بدء التشغيل التلقائي مع Windows.",
                )
        except Exception as exc:
            logger.error("Error setting startup to %s: %s", checked, exc)
            self._revert_startup(checked)
            QMessageBox.warning(
                self,
                "خطأ في الإعدادات",
                f"حدث خطأ أثناء حفظ الإعداد:\n{exc}",
            )

    def _revert_startup(self, attempted: bool) -> None:
        """Slide the switch back to the state before the failed change."""
        self._startup_switch.set_checked_silently(not attempted, animate=True)

    # -- Opening and closing ------------------------------------------------

    def is_open(self) -> bool:
        return self.isVisible()

    def open(self, return_focus: Optional[QWidget] = None) -> None:
        """Slide the panel in over the home page."""
        if self.isVisible() or self._animation is not None:
            return

        self._return_focus = return_focus
        self._sync_startup()

        self._cover_host()
        self._layout.activate()  # sections need their final places first
        self.show()
        self.raise_()
        self._back.setFocus()

        self._animate(opening=True)
        self._reveal.start()

    def close_panel(self) -> None:
        """Slide the panel away and bring the home page back."""
        if not self.isVisible() or self._animation is not None:
            return

        self._reveal.finish()
        self._home.show()
        focus, self._return_focus = self._return_focus, None
        if focus is not None:
            focus.setFocus()
        self._animate(opening=False)

    def _animate(self, *, opening: bool) -> None:
        """Slide + fade this panel while the home page fades the other way."""
        rest = QPoint(0, 0)
        away = QPoint(-PANEL_SLIDE_OFFSET, 0)
        duration = PANEL_OPEN_MS if opening else PANEL_CLOSE_MS
        curve = QEasingCurve.Type.OutCubic if opening else QEasingCurve.Type.InCubic

        panel_fade = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(panel_fade)
        home_fade = QGraphicsOpacityEffect(self._home)
        self._home.setGraphicsEffect(home_fade)

        group = QParallelAnimationGroup(self)
        for target, name, start, end in (
            (self, b"pos", away if opening else rest, rest if opening else away),
            (panel_fade, b"opacity", 0.0 if opening else 1.0, 1.0 if opening else 0.0),
            (home_fade, b"opacity", 1.0 if opening else 0.0, 0.0 if opening else 1.0),
        ):
            animation = QPropertyAnimation(target, name)
            animation.setStartValue(start)
            animation.setEndValue(end)
            animation.setDuration(duration)
            animation.setEasingCurve(curve)
            group.addAnimation(animation)

        group.finished.connect(lambda: self._on_motion_finished(opening))
        self._animation = group
        group.start()

    def _on_motion_finished(self, opening: bool) -> None:
        self.setGraphicsEffect(cast(QGraphicsEffect, None))
        self._home.setGraphicsEffect(cast(QGraphicsEffect, None))
        if self._animation is not None:
            self._animation.deleteLater()
            self._animation = None

        if opening:
            self._home.hide()  # unreachable by keyboard while settings are open
        else:
            self.hide()

    # -- Covering the host --------------------------------------------------

    def _cover_host(self) -> None:
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
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
        event.accept()  # no window menu over the settings screen