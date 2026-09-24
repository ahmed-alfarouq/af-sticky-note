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
    """Windows-specific desktop layer window controller."""

    def __init__(self) -> None:
        self._attached: bool = False
        self._target_hwnd: Optional[int] = None
        self._desktop_workerw: Optional[int] = None

    def attach_to_desktop(self, window_handle: int) -> bool:
        """Attach window to the Windows desktop shell layer.

        1. Configure extended styles: add WS_EX_TOOLWINDOW to exclude from Alt+Tab,
           remove WS_EX_APPWINDOW to exclude from taskbar.
        2. Resolve desktop WorkerW shell window.
        3. SetParent to the WorkerW host behind desktop icons.
        4. Lower to HWND_BOTTOM within that shell layer.
        """
        if not window_handle:
            logger.error("Cannot attach to desktop: invalid window handle (%r)", window_handle)
            return False

        try:
            self._target_hwnd = window_handle

            # 1. Update extended styles for Taskbar / Alt+Tab suppression
            # Adding WS_EX_TOOLWINDOW hides from Alt+Tab.
            # Removing WS_EX_APPWINDOW hides from the Taskbar.
            set_window_ex_style(
                window_handle,
                add_flags=WS_EX_TOOLWINDOW,
                remove_flags=WS_EX_APPWINDOW,
            )

            # 2. Find desktop WorkerW window
            workerw = find_desktop_workerw()
            if not workerw:
                logger.warning("Could not find WorkerW or Progman window on Windows; falling back to HWND_BOTTOM")
                set_window_bottom(window_handle)
                self._attached = True
                return True

            self._desktop_workerw = workerw

            # 3. Re-parent to WorkerW
            set_window_parent(window_handle, workerw)

            # 4. Position at the bottom of the WorkerW layer
            set_window_bottom(window_handle)

            self._attached = True
            logger.info("Successfully attached window %d to desktop shell WorkerW %d", window_handle, workerw)
            return True

        except Exception as exc:
            logger.error("Failed to attach window to Windows desktop: %s", exc, exc_info=True)
            self._attached = False
            return False

    def detach_from_desktop(self, window_handle: int) -> bool:
        """Detach window from desktop WorkerW back to standard desktop root."""
        if not window_handle:
            return False

        try:
            # Reparent back to 0 (top-level desktop)
            set_window_parent(window_handle, 0)
            self._attached = False
            self._target_hwnd = None
            self._desktop_workerw = None
            logger.info("Detached window %d from desktop shell", window_handle)
            return True
        except Exception as exc:
            logger.error("Failed to detach window from desktop: %s", exc)
            return False

    def is_attached(self) -> bool:
        return self._attached
