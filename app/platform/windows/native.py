"""Win32 API constants, type signatures, and shell integration helpers.

Encapsulates all ctypes / Win32 declarations.
Keeps raw win32 definitions strictly isolated within app/platform/windows/.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

# Window Styles
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
WS_EX_NOACTIVATE = 0x08000000

# GetWindowLongPtr / SetWindowLongPtr index
GWL_EXSTYLE = -20
GWL_STYLE = -16
GWLP_HWNDPARENT = -8

# SetWindowPos Flags
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOZORDER = 0x0004
HWND_BOTTOM = 1

# Window Messages
WM_SPAWN_WORKER = 0x052C

# Windows type declarations for 32-bit & 64-bit safety
LRESULT = getattr(wintypes, "LPARAM", ctypes.c_long)
BOOL = getattr(wintypes, "BOOL", ctypes.c_int)
HWND = getattr(wintypes, "HWND", ctypes.c_void_p)
DWORD = getattr(wintypes, "DWORD", ctypes.c_ulong)
LPARAM = getattr(wintypes, "LPARAM", ctypes.c_long)

# ctypes.WINFUNCTYPE exists on Windows; fallback to CFUNCTYPE on non-Windows for cross-platform imports
WINFUNCTYPE = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
WNDENUMPROC = WINFUNCTYPE(BOOL, HWND, LPARAM)


def _get_user32() -> Optional[ctypes.WinDLL]:
    """Safely obtain user32.dll on Windows. Returns None on other platforms."""
    try:
        return ctypes.windll.user32
    except (AttributeError, OSError):
        return None


def find_progman_window() -> int:
    """Locate the top-level Program Manager (Progman) shell window."""
    user32 = _get_user32()
    if not user32:
        return 0
    return user32.FindWindowW("Progman", None)


def spawn_worker_windows(progman_hwnd: int) -> None:
    """Send message 0x052C to Progman to ensure WorkerW wallpaper windows are spawned by Windows shell."""
    user32 = _get_user32()
    if not user32 or not progman_hwnd:
        return
    # SendMessageTimeoutW(hwnd, msg, wParam, lParam, flags, timeout, out_result)
    result = DWORD()
    # SMTO_NORMAL = 0x0000
    user32.SendMessageTimeoutW(
        progman_hwnd,
        WM_SPAWN_WORKER,
        0x0000000D,
        0,
        0,
        1000,
        ctypes.byref(result),
    )


def find_desktop_workerw() -> int:
    """Find the WorkerW window that sits directly behind the desktop icon view (SHELLDLL_DefView).

    In Windows shell architecture:
    Progman spawns a WorkerW window. SHELLDLL_DefView (which hosts the desktop icons)
    is hosted inside Progman or a WorkerW.
    The WorkerW that sits directly behind desktop icons is the WorkerW created as a sibling
    to the WorkerW containing SHELLDLL_DefView, or directly behind Progman.
    """
    user32 = _get_user32()
    if not user32:
        return 0

    progman = find_progman_window()
    if not progman:
        return 0

    # Ensure worker windows exist
    spawn_worker_windows(progman)

    target_workerw = HWND(0)

    def _enum_windows_callback(top_hwnd: int, lparam: int) -> bool:
        # Check if this window contains SHELLDLL_DefView as a child
        def_view = user32.FindWindowExW(top_hwnd, 0, "SHELLDLL_DefView", None)
        if def_view:
            # The WorkerW behind desktop icons is the WorkerW directly following this window
            worker = user32.FindWindowExW(0, top_hwnd, "WorkerW", None)
            if worker:
                target_workerw.value = worker
                return False  # stop enumeration
        return True  # continue enumeration

    callback = WNDENUMPROC(_enum_windows_callback)
    user32.EnumWindows(callback, 0)

    if target_workerw.value:
        return target_workerw.value

    # Fallback to Progman if WorkerW enumeration did not find a separate instance
    return progman


def set_window_ex_style(hwnd: int, add_flags: int, remove_flags: int = 0) -> int:
    """Update extended window styles using SetWindowLongPtrW."""
    user32 = _get_user32()
    if not user32 or not hwnd:
        return 0

    # Handle 64-bit vs 32-bit entry point
    get_long = getattr(user32, "GetWindowLongPtrW", getattr(user32, "GetWindowLongW", None))
    set_long = getattr(user32, "SetWindowLongPtrW", getattr(user32, "SetWindowLongW", None))
    if not get_long or not set_long:
        return 0

    current_style = get_long(hwnd, GWL_EXSTYLE)
    new_style = (current_style | add_flags) & ~remove_flags
    if new_style != current_style:
        set_long(hwnd, GWL_EXSTYLE, new_style)
    return new_style


def set_window_parent(child_hwnd: int, parent_hwnd: int) -> int:
    """Reparent child_hwnd under parent_hwnd using SetParent."""
    user32 = _get_user32()
    if not user32 or not child_hwnd:
        return 0
    res = user32.SetParent(child_hwnd, parent_hwnd)
    # When a top-level window becomes a child window in Win32, WS_CHILD must be added
    # and the window must be made visible explicitly in its new parent coordinates
    user32.ShowWindow(child_hwnd, 5)  # SW_SHOW = 5
    user32.UpdateWindow(child_hwnd)
    return res


def set_window_bottom(hwnd: int) -> bool:
    """Place window at the bottom of its Z-order layer (HWND_BOTTOM) without moving or resizing."""
    user32 = _get_user32()
    if not user32 or not hwnd:
        return False
    return bool(
        user32.SetWindowPos(
            hwnd,
            HWND_BOTTOM,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )
    )
