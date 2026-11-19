"""The settings screen: sections of rows inside a scroll area."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from app.ui.styles.settings_style import PANEL_GAP
from app.ui.widgets.option_sheet import OptionSheet
from app.ui.widgets.screens import ScreenPanel
from app.ui.widgets.settings.content import SettingsContent
from app.ui.widgets.settings.context import SettingsContext

__all__ = ["SettingsPanel"]


class SettingsPanel(ScreenPanel):
    """Settings screen covering ``host``; swaps with the ``home`` page."""

    def __init__(
        self,
        host: QWidget,
        home: QWidget,
        option_sheet: OptionSheet,
        context: SettingsContext,
    ) -> None:
        super().__init__(host, home, "الإعدادات")
        self._content = SettingsContent(context, option_sheet, self)
        self.set_body(self._build_scroll())

    def _build_scroll(self) -> QScrollArea:
        content = QWidget()
        content.setObjectName("settingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PANEL_GAP)
        for section in self._content.sections:
            layout.addWidget(section)
        layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setObjectName("settingsScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setWidget(content)
        return scroll

    def _prepare_open(self) -> None:
        self._content.sync()

    def sync_pin(self) -> None:
        """The window's pin state changed elsewhere (e.g. by shortcut)."""
        self._content.sync_pin(animate=self.isVisible())