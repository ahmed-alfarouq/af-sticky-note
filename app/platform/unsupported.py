"""Safe fallback and no-op implementation of platform protocols.

Used on non-Windows platforms (e.g. Linux development environments, macOS)
and in test environments to guarantee the application never crashes
merely because OS-specific desktop integration is unavailable.
"""
from __future__ import annotations

import logging

from app.platform.interfaces import (
    DesktopWindowController,
    PlatformAdapter,
    StartupManager,
    SystemTrayController,
)

logger = logging.getLogger(__name__)


class NoOpDesktopWindowController(DesktopWindowController):
    """No-op desktop window controller for unsupported platforms."""

    def __init__(self) -> None:
        self._attached = False

    def attach_to_desktop(self, window_handle: int) -> bool:
        logger.debug("Desktop layering attach called on unsupported platform (no-op).")
        return False

    def detach_from_desktop(self, window_handle: int) -> bool:
        logger.debug("Desktop layering detach called on unsupported platform (no-op).")
        return False

    def is_attached(self) -> bool:
        return self._attached


class NoOpStartupManager(StartupManager):
    """No-op startup manager for unsupported platforms."""

    def is_enabled(self) -> bool:
        return False

    def enable(self) -> bool:
        logger.debug("Startup enable requested on unsupported platform (no-op).")
        return False

    def disable(self) -> bool:
        logger.debug("Startup disable requested on unsupported platform (no-op).")
        return False


class NoOpSystemTrayController(SystemTrayController):
    """No-op system tray controller for unsupported platforms."""

    def is_available(self) -> bool:
        return False

    def show(self) -> None:
        logger.debug("System tray show requested on unsupported platform (no-op).")

    def hide(self) -> None:
        logger.debug("System tray hide requested on unsupported platform (no-op).")

    def show_message(self, title: str, message: str) -> None:
        logger.debug("Tray notification requested on unsupported platform: %s - %s", title, message)


class UnsupportedPlatformAdapter(PlatformAdapter):
    """Platform adapter instance returned when running on non-Windows systems."""

    def __init__(self, platform_name: str = "unsupported") -> None:
        self._name = platform_name
        self._window_controller = NoOpDesktopWindowController()
        self._startup_manager = NoOpStartupManager()
        self._tray_controller = NoOpSystemTrayController()

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_supported(self) -> bool:
        return False

    @property
    def window_controller(self) -> DesktopWindowController:
        return self._window_controller

    @property
    def startup_manager(self) -> StartupManager:
        return self._startup_manager

    @property
    def tray_controller(self) -> SystemTrayController:
        return self._tray_controller
