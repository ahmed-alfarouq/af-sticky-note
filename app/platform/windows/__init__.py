"""Windows platform adapter implementation.

Assembles Windows-specific desktop window controllers, startup managers,
and tray controllers under the PlatformAdapter protocol.
"""
from __future__ import annotations

from app.platform.interfaces import (
    DesktopWindowController,
    PlatformAdapter,
    StartupManager,
    SystemTrayController,
)
from app.platform.unsupported import NoOpStartupManager, NoOpSystemTrayController
from app.platform.windows.desktop_window import WindowsDesktopWindowController


class WindowsPlatformAdapter(PlatformAdapter):
    """PlatformAdapter implementation for Microsoft Windows."""

    def __init__(self) -> None:
        self._name = "windows"
        self._window_controller = WindowsDesktopWindowController()
        # Startup and Tray managers belong to Phase 5G & 5H; use safe fallbacks until implemented
        self._startup_manager = NoOpStartupManager()
        self._tray_controller = NoOpSystemTrayController()

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_supported(self) -> bool:
        return True

    @property
    def window_controller(self) -> DesktopWindowController:
        return self._window_controller

    @property
    def startup_manager(self) -> StartupManager:
        return self._startup_manager

    @property
    def tray_controller(self) -> SystemTrayController:
        return self._tray_controller
