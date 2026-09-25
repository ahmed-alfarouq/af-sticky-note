"""Windows system tray controller implementation using PySide6 (Phase 5H-A).

Provides minimal system tray integration with Show/Hide Sticky and Exit actions.
Preserves existing MainWindow instance, desktop-layer attachment, and position/size.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

try:
    from PySide6.QtCore import QObject
    from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget
except ImportError:
    QObject = object  # type: ignore
    QSystemTrayIcon = None  # type: ignore
    QMenu = None  # type: ignore
    QAction = None  # type: ignore
    QIcon = None  # type: ignore
    QPixmap = None  # type: ignore
    QPainter = None  # type: ignore
    QColor = None  # type: ignore
    QApplication = None  # type: ignore
    QWidget = None  # type: ignore

from app.config.settings import APP_NAME
from app.platform.interfaces import SystemTrayController

logger = logging.getLogger(__name__)


def _create_fallback_tray_icon() -> Optional[QIcon]:
    """Generate a clean, high-contrast sticky-note fallback icon."""
    if QIcon is None or QPixmap is None or QPainter is None:
        return None
    try:
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw a warm golden/amber sticky note surface
        painter.setBrush(QColor(230, 180, 50))
        painter.setPen(QColor(180, 130, 20))
        painter.drawRoundedRect(3, 3, 26, 26, 4, 4)

        # Draw decorative pin dot at the top center
        painter.setBrush(QColor(190, 45, 45))
        painter.setPen(QColor(140, 25, 25))
        painter.drawEllipse(13, 5, 6, 6)

        painter.end()
        return QIcon(pixmap)
    except Exception as exc:
        logger.warning("Failed to synthesize fallback tray icon: %s", exc)
        return None


class WindowsSystemTrayController(SystemTrayController):
    """System tray integration for Windows platforms using QSystemTrayIcon."""

    def __init__(
        self,
        main_window: Optional[QWidget] = None,
        on_exit_requested: Optional[Callable[[], None]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        self._main_window = main_window
        self._on_exit_requested = on_exit_requested
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._tray_menu: Optional[QMenu] = None
        self._toggle_action: Optional[QAction] = None
        self._exit_action: Optional[QAction] = None

        self._init_tray()

    def _init_tray(self) -> None:
        """Initialize QSystemTrayIcon and context menu."""
        if QSystemTrayIcon is None or not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("QSystemTrayIcon is not available in the current environment.")
            return

        icon = _create_fallback_tray_icon()
        if icon is None:
            icon = QIcon()

        self._tray_icon = QSystemTrayIcon(icon)
        self._tray_icon.setToolTip(APP_NAME)

        # Setup minimal context menu
        self._tray_menu = QMenu()
        self._toggle_action = QAction("إخفاء الملاحظة", self._tray_menu)
        self._toggle_action.triggered.connect(self.toggle_window_visibility)
        self._tray_menu.addAction(self._toggle_action)

        self._tray_menu.addSeparator()

        self._exit_action = QAction("خروج", self._tray_menu)
        self._exit_action.triggered.connect(self.request_exit)
        self._tray_menu.addAction(self._exit_action)

        self._tray_icon.setContextMenu(self._tray_menu)

        # Left-click on tray icon toggles window visibility
        self._tray_icon.activated.connect(self._on_tray_activated)

        # Update action text before menu shows
        self._tray_menu.aboutToShow.connect(self._update_action_labels)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon click activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single left click
            self.toggle_window_visibility()

    def _update_action_labels(self) -> None:
        """Update toggle action text based on current window visibility."""
        if self._toggle_action is None:
            return
        if self._main_window is not None and self._main_window.isVisible():
            self._toggle_action.setText("إخفاء الملاحظة")
        else:
            self._toggle_action.setText("إظهار الملاحظة")

    def toggle_window_visibility(self) -> None:
        """Toggle between showing and hiding the sticky window."""
        if self._main_window is None:
            return

        if self._main_window.isVisible():
            self.hide_window()
        else:
            self.show_window()

    def show_window(self) -> None:
        """Show the sticky window without altering its geometry or Z-order."""
        if self._main_window is None:
            return
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()
        self._update_action_labels()
        logger.debug("MainWindow shown from system tray.")

    def hide_window(self) -> None:
        """Hide the sticky window while keeping the application running in the tray."""
        if self._main_window is None:
            return
        self._main_window.hide()
        self._update_action_labels()
        logger.debug("MainWindow hidden to system tray.")

    def request_exit(self) -> None:
        """Perform clean application exit."""
        logger.info("Application exit requested via system tray.")
        self.hide()
        if self._on_exit_requested is not None:
            self._on_exit_requested()
        elif QApplication is not None:
            app = QApplication.instance()
            if app is not None:
                app.quit()

    def is_available(self) -> bool:
        """Check if system tray is supported in the current environment."""
        if QSystemTrayIcon is None:
            return False
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        """Display the system tray icon."""
        if self._tray_icon is not None:
            self._update_action_labels()
            self._tray_icon.show()
            logger.debug("System tray icon displayed.")

    def hide(self) -> None:
        """Hide and cleanly release the system tray icon."""
        if self._tray_icon is not None:
            self._tray_icon.hide()
            logger.debug("System tray icon hidden.")

    def show_message(self, title: str, message: str) -> None:
        """Display a system notification from the tray."""
        if self._tray_icon is not None and self._tray_icon.isVisible():
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
