"""Windows DesktopWindowController implementation.

Pins the application window to the desktop wallpaper layer beneath normal applications
and removes taskbar/Alt+Tab representation.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.platform.interfaces import DesktopWindowController
from app.platform.windows.native import (
    WS_EX_APPWINDOW,
    WS_EX_TOOLWINDOW,
    find_desktop_workerw,
    set_window_bottom,
    set_window_ex_style,
    set_window_parent,
)

logger = logging.getLogger(__name__)


class WindowsDesktopWindowController(DesktopWindowController):
    """Windows-specific desktop layer window controller.

    Keeps MainWindow as a top-level HWND.
    Configures extended window styles (WS_EX_TOOLWINDOW) and lowers to HWND_BOTTOM
    without reparenting to Explorer or WorkerW.
    """

    def __init__(self) -> None:
        self._attached: bool = False
        self._target_hwnd: Optional[int] = None

    def attach_to_desktop(self, window_handle: int) -> bool:
        """Configure top-level desktop sticky note behavior.

        1. Ensures the window remains a top-level HWND (no SetParent).
        2. Configures extended window styles:
           - Adds WS_EX_TOOLWINDOW to remove from Alt+Tab and taskbar.
        3. Lowers to HWND_BOTTOM so normal applications naturally sit above it.
        """
        if not window_handle:
            logger.error("Cannot attach to desktop: invalid window handle (%r)", window_handle)
            return False

        try:
            self._target_hwnd = window_handle

            # 1. Update extended styles for Taskbar / Alt+Tab suppression as top-level tool window
            set_window_ex_style(
                window_handle,
                add_flags=WS_EX_TOOLWINDOW,
                remove_flags=WS_EX_APPWINDOW,
            )

            # 2. Lower to HWND_BOTTOM in top-level Z-order
            set_window_bottom(window_handle)

            self._attached = True
            logger.info("Successfully configured top-level desktop window %d at HWND_BOTTOM", window_handle)
            return True

        except Exception as exc:
            logger.error("Failed to configure top-level desktop window: %s", exc, exc_info=True)
            self._attached = False
            return False

    def detach_from_desktop(self, window_handle: int) -> bool:
        """Restore standard window styles if detached."""
        if not window_handle:
            return False

        try:
            set_window_ex_style(
                window_handle,
                add_flags=WS_EX_APPWINDOW,
                remove_flags=WS_EX_TOOLWINDOW,
            )
            self._attached = False
            self._target_hwnd = None
            logger.info("Restored standard styles for window %d", window_handle)
            return True
        except Exception as exc:
            logger.error("Failed to restore window styles: %s", exc)
            return False

    def is_attached(self) -> bool:
        return self._attached
