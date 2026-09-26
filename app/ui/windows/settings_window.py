"""Settings dialog for configuring user-facing options (Phase 5L).

Exposes Start with Windows toggle via StartupManager protocol in Arabic RTL.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import APP_NAME
from app.infrastructure.paths import get_logo_path
from app.platform.interfaces import StartupManager
from app.ui.styles.app_style import get_application_stylesheet

logger = logging.getLogger(__name__)


class SettingsWindow(QDialog):
    """Modal dialog for Daily Sticky application settings."""

    def __init__(
        self,
        startup_manager: StartupManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._startup_manager = startup_manager

        self.setWindowTitle("الإعدادات")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(360, 240)
        self.setMinimumSize(320, 200)

        # Set dialog window icon from bundled logo if present
        try:
            from PySide6.QtGui import QIcon
            logo_path = get_logo_path()
            if logo_path.exists() and logo_path.is_file():
                self.setWindowIcon(QIcon(str(logo_path)))
        except Exception:
            pass

        self._init_ui()
        self.setStyleSheet(get_application_stylesheet())
        self._load_current_settings()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # 1. Branding Header: Logo + App Name
        branding_row = QHBoxLayout()
        branding_row.setSpacing(10)

        # Attempt to load logo image
        try:
            from PySide6.QtGui import QPixmap
            logo_path = get_logo_path()
            if logo_path.exists() and logo_path.is_file():
                logo_label = QLabel(self)
                logo_label.setObjectName("settingsAppLogo")
                logo_label.setAccessibleName("شعار الملاحظة اليومية")
                pixmap = QPixmap(str(logo_path))
                if not pixmap.isNull():
                    # Scale cleanly maintaining aspect ratio to compact header size (36x36)
                    scaled_pix = pixmap.scaled(
                        36, 36,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    logo_label.setPixmap(scaled_pix)
                    branding_row.addWidget(logo_label)
        except Exception:
            pass

        title_label = QLabel(APP_NAME, self)
        title_label.setObjectName("dateLabel")
        title_label.setAccessibleName("اسم التطبيق")
        branding_row.addWidget(title_label)
        branding_row.addStretch(1)

        main_layout.addLayout(branding_row)

        # 2. General Settings Card Container
        settings_card = QFrame(self)
        settings_card.setObjectName("quoteCard")
        card_layout = QVBoxLayout(settings_card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        # Startup checkbox
        self._startup_checkbox = QCheckBox("تشغيل مع بدء تشغيل Windows", settings_card)
        self._startup_checkbox.setObjectName("startupCheckbox")
        self._startup_checkbox.setAccessibleName("تشغيل مع بدء تشغيل Windows")
        self._startup_checkbox.setAccessibleDescription(
            "تشغيل تطبيق الملاحظة اليومية تلقائياً عند تسجيل الدخول إلى Windows"
        )
        self._startup_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self._startup_checkbox.toggled.connect(self._on_startup_toggled)

        card_layout.addWidget(self._startup_checkbox)
        main_layout.addWidget(settings_card)

        main_layout.addStretch(1)

        # 3. Bottom Close Button Row
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self._close_btn = QPushButton("إغلاق", self)
        self._close_btn.setObjectName("historyCloseButton")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)

        main_layout.addLayout(btn_row)

    def _load_current_settings(self) -> None:
        """Query current startup state and update checkbox silently."""
        try:
            enabled = self._startup_manager.is_enabled()
        except Exception as exc:
            logger.error("Failed to query startup manager state: %s", exc)
            enabled = False

        self._startup_checkbox.blockSignals(True)
        self._startup_checkbox.setChecked(enabled)
        self._startup_checkbox.blockSignals(False)

    def _on_startup_toggled(self, checked: bool) -> None:
        """Handle user toggling of the startup setting."""
        try:
            if checked:
                success = self._startup_manager.enable()
            else:
                success = self._startup_manager.disable()

            if not success:
                self._revert_checkbox(not checked)
                QMessageBox.warning(
                    self,
                    "خطأ في الإعدادات",
                    "تعذر تعديل إعداد بدء التشغيل التلقائي مع Windows.",
                )
        except Exception as exc:
            logger.error("Error setting startup to %s: %s", checked, exc)
            self._revert_checkbox(not checked)
            QMessageBox.warning(
                self,
                "خطأ في الإعدادات",
                f"حدث خطأ أثناء حفظ الإعداد:\n{exc}",
            )

    def _revert_checkbox(self, target_state: bool) -> None:
        """Revert checkbox state without re-triggering toggle signals."""
        self._startup_checkbox.blockSignals(True)
        self._startup_checkbox.setChecked(target_state)
        self._startup_checkbox.blockSignals(False)
