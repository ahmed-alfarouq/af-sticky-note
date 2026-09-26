"""Prototype: Event-driven non-TOPMOST Z-order coordination via SetWinEventHook.

Tests whether moving Daily Sticky above Progman upon EVENT_SYSTEM_FOREGROUND
(when Progman is foreground) keeps the sticky visible on Show Desktop without
ever using HWND_TOPMOST or WS_EX_TOPMOST.

Zero production application files are modified.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
import sys

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.main import bootstrap_application

user32 = getattr(ctypes.windll, "user32", None)

# WinEvent Constants
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000

# SetWindowPos Flags
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOZORDER = 0x0004
HWND_BOTTOM = 1

GWL_STYLE = -16
GWL_EXSTYLE = -20
GW_HWNDNEXT = 2
GW_HWNDPREV = 3
GW_OWNER = 4

WINEVENTPROC = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD,
)


def _get_window_text(hwnd: int) -> str:
    if not user32 or not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value


def _get_class_name(hwnd: int) -> str:
    if not user32 or not hwnd:
        return ""
    buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buff, 256)
    return buff.value


def _get_z_order_positions(target_hwnd: int, progman_hwnd: int, foreground_hwnd: int) -> tuple[int, int, int]:
    """Calculate the true top-level Z-index of target, progman, and foreground windows."""
    if not user32:
        return (-1, -1, -1)
    curr = user32.GetTopWindow(0)
    actual_z = 0
    target_z = -1
    progman_z = -1
    fg_z = -1

    while curr:
        if curr == target_hwnd:
            target_z = actual_z
        if curr == progman_hwnd:
            progman_z = actual_z
        if curr == foreground_hwnd:
            fg_z = actual_z
        actual_z += 1
        curr = user32.GetWindow(curr, GW_HWNDNEXT)

    return (target_z, progman_z, fg_z)


class PrototypeZOrderCoordinator:
    def __init__(self, sticky_hwnd: int) -> None:
        self.sticky_hwnd = sticky_hwnd
        self.progman_hwnd = user32.FindWindowW("Progman", None) if user32 else 0
        self.hook_handle = None
        self._proc_ref = None

    def start(self) -> bool:
        if not user32:
            print("ERROR: user32.dll not available.")
            return False

        self._proc_ref = WINEVENTPROC(self._win_event_callback)
        self.hook_handle = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            0,
            self._proc_ref,
            0,
            0,
            WINEVENT_OUTOFCONTEXT,
        )

        if not self.hook_handle:
            print("ERROR: SetWinEventHook failed.")
            return False

        print(f"[PROTOTYPE HOOK ACTIVE] Handle: {self.hook_handle}")
        print(f"Target Sticky HWND: 0x{self.sticky_hwnd:X} | Progman HWND: 0x{self.progman_hwnd:X}\n")
        return True

    def stop(self) -> None:
        if user32 and self.hook_handle:
            user32.UnhookWinEvent(self.hook_handle)
            print("\n[PROTOTYPE HOOK UNINSTALLED]")
            self.hook_handle = None

    def _win_event_callback(
        self,
        hHook: int,
        event: int,
        hwnd: int,
        idObject: int,
        idChild: int,
        dwEventThread: int,
        dwmsEventTime: int,
    ) -> None:
        if idObject != 0:  # Only top-level window events
            return

        now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        cls = _get_class_name(hwnd)
        title = _get_window_text(hwnd)
        fg_hwnd = user32.GetForegroundWindow()

        is_progman = (hwnd == self.progman_hwnd) or (cls == "Progman")
        is_sticky = (hwnd == self.sticky_hwnd)

        get_long = getattr(user32, "GetWindowLongPtrW", getattr(user32, "GetWindowLongW", None))
        exstyle = get_long(self.sticky_hwnd, GWL_EXSTYLE) if get_long else 0
        is_topmost = bool(exstyle & 0x00000008)
        is_visible = bool(user32.IsWindowVisible(self.sticky_hwnd))
        is_iconic = bool(user32.IsIconic(self.sticky_hwnd))

        s_z, p_z, f_z = _get_z_order_positions(self.sticky_hwnd, self.progman_hwnd, fg_hwnd)

        tag = " [PROGMAN/DESKTOP]" if is_progman else (" [STICKY]" if is_sticky else "")
        print(f"\n{now_str} EVENT_FOREGROUND: HWND=0x{hwnd:<8X} Class='{cls[:16]}' Title='{title[:25]}'{tag}")
        print(f"    Sticky State: Visible={is_visible} Iconic={is_iconic} TOPMOST={is_topmost}")
        print(f"    Z-Order Before Op: Sticky Z={s_z} | Progman Z={p_z} | Foreground Z={f_z}")

        # Action logic
        if is_progman:
            # 1. Desktop shown (Progman is foreground):
            # Move Daily Sticky immediately in front of Progman without making it TOPMOST.
            # In Win32 SetWindowPos:
            # GetWindow(progman, GW_HWNDPREV) is the window immediately in front of Progman.
            # Inserting after GW_HWNDPREV of Progman (or using Progman logic) places Sticky immediately above Progman.
            # Alternatively: user32.SetWindowPos(self.sticky_hwnd, 0 (HWND_TOP), ..., SWP_NOACTIVATE)
            # would make it top of the non-topmost band (which is currently just the desktop layer).
            # To strictly insert immediately in front of Progman:
            # In Win32 SetWindowPos(hWnd, hWndInsertAfter):
            # If hWndInsertAfter is a window handle, hWnd is placed immediately FOLLOWING (behind) hWndInsertAfter.
            # So to place Sticky in front of Progman, we find Progman's HWNDPREV and insert after it,
            # or if Progman is at the top of non-topmost, place at HWND_TOP without activation.
            progman_prev = user32.GetWindow(self.progman_hwnd, GW_HWNDPREV)
            insert_after = progman_prev if progman_prev else 0  # 0 = HWND_TOP (non-topmost top)

            print(f"    >>> PROTOTYPE ACTION: Placing Sticky above Progman (InsertAfter=0x{insert_after:X})...")
            user32.SetWindowPos(
                self.sticky_hwnd,
                insert_after,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )
        elif not is_sticky and bool(title.strip()):
            # 2. A normal application became foreground:
            # Ensure the sticky does NOT stay above this application.
            # If sticky is above the new foreground application (s_z < f_z),
            # place sticky immediately behind the foreground application.
            if s_z < f_z:
                print(f"    >>> PROTOTYPE ACTION: Placing Sticky behind active app 0x{hwnd:X}...")
                user32.SetWindowPos(
                    self.sticky_hwnd,
                    hwnd,  # inserting after hwnd places sticky behind hwnd
                    0,
                    0,
                    0,
                    0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
                )

        # Re-measure Z-order after operation
        new_s_z, new_p_z, new_f_z = _get_z_order_positions(self.sticky_hwnd, self.progman_hwnd, fg_hwnd)
        new_exstyle = get_long(self.sticky_hwnd, GWL_EXSTYLE) if get_long else 0
        new_topmost = bool(new_exstyle & 0x00000008)

        sticky_above_progman = (new_s_z < new_p_z) and (new_s_z >= 0) and (new_p_z >= 0)
        sticky_above_fg = (new_s_z < new_f_z) and (new_s_z >= 0) and (new_f_z >= 0) and not is_progman and not is_sticky

        print(f"    Z-Order After Op:  Sticky Z={new_s_z} | Progman Z={new_p_z} | Foreground Z={new_f_z}")
        print(f"    Evaluation:")
        print(f"        Sticky above Progman:                   {'YES' if sticky_above_progman else 'NO'}")
        print(f"        Sticky above foreground normal app:     {'YES (OCCLUDING APP)' if sticky_above_fg else 'NO'}")
        print(f"        Sticky TOPMOST:                         {'YES (VIOLATION)' if new_topmost else 'NO'}")
        print("-" * 80)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = bootstrap_application(app)
    hwnd = int(window.winId())

    coord = PrototypeZOrderCoordinator(sticky_hwnd=hwnd)
    if not coord.start():
        sys.exit(1)

    print("=" * 80)
    print("PROTOTYPE TEST INSTRUCTIONS:")
    print("1. Open Chrome and position it overlapping Daily Sticky.")
    print("2. Focus Chrome (confirm Chrome covers Daily Sticky).")
    print("3. Press Win + D (Show Desktop).")
    print("4. Wait 2 seconds. Look at the screen: Is Daily Sticky visible?")
    print("5. Click Daily Sticky (verify it receives click/input).")
    print("6. Press Win + D again (Restore).")
    print("7. Click Chrome (confirm Chrome covers Daily Sticky again).")
    print("8. Close the application or press Ctrl+C to exit.")
    print("=" * 80 + "\n")

    app.aboutToQuit.connect(coord.stop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
