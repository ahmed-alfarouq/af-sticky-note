"""Diagnostic-only WinEventHook experiment for Win+D / Show Desktop.

Monitors EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_MINIMIZESTART, and
EVENT_SYSTEM_MINIMIZEEND to evaluate whether Windows reliably emits
foreground events when Show Desktop raises Progman.

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
EVENT_SYSTEM_MINIMIZESTART = 0x0016
EVENT_SYSTEM_MINIMIZEEND = 0x0017
WINEVENT_OUTOFCONTEXT = 0x0000

# Function pointer prototype for WinEventProc
# void CALLBACK WinEventProc(HWINEVENTHOOK hWinEventHook, DWORD event, HWND hwnd, LONG idObject, LONG idChild, DWORD idEventThread, DWORD dwmsEventTime)
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

GWL_STYLE = -16
GWL_EXSTYLE = -20
GW_HWNDNEXT = 2
GW_OWNER = 4

EVENT_NAMES = {
    EVENT_SYSTEM_FOREGROUND: "EVENT_SYSTEM_FOREGROUND",
    EVENT_SYSTEM_MINIMIZESTART: "EVENT_SYSTEM_MINIMIZESTART",
    EVENT_SYSTEM_MINIMIZEEND: "EVENT_SYSTEM_MINIMIZEEND",
}


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


def _get_z_order_positions(target_hwnd: int, progman_hwnd: int) -> tuple[int, int]:
    """Calculate the true top-level Z-index of target_hwnd and progman_hwnd."""
    if not user32:
        return (-1, -1)
    curr = user32.GetTopWindow(0)
    actual_z = 0
    target_z = -1
    progman_z = -1

    while curr:
        if curr == target_hwnd:
            target_z = actual_z
        elif curr == progman_hwnd:
            progman_z = actual_z
        actual_z += 1
        curr = user32.GetWindow(curr, GW_HWNDNEXT)

    return (target_z, progman_z)


class WinEventDiagnostic:
    def __init__(self, sticky_hwnd: int) -> None:
        self.sticky_hwnd = sticky_hwnd
        self.progman_hwnd = user32.FindWindowW("Progman", None) if user32 else 0
        self.hook_handle = None
        self._proc_ref = None  # prevent GC of ctypes callback

    def start(self) -> bool:
        if not user32:
            print("ERROR: user32.dll not available.")
            return False

        self._proc_ref = WINEVENTPROC(self._win_event_callback)

        # Set hook for EVENT_SYSTEM_FOREGROUND up to EVENT_SYSTEM_MINIMIZEEND
        # Covers 0x0003 (FOREGROUND) and 0x0016-0x0017 (MINIMIZESTART/END)
        self.hook_handle = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_MINIMIZEEND,
            0,
            self._proc_ref,
            0,
            0,
            WINEVENT_OUTOFCONTEXT,
        )

        if not self.hook_handle:
            print("ERROR: SetWinEventHook failed.")
            return False

        print(f"[HOOK ACTIVE] Hook handle = {self.hook_handle}")
        print(f"Target Sticky HWND = 0x{self.sticky_hwnd:X} ({self.sticky_hwnd})")
        print(f"Progman HWND       = 0x{self.progman_hwnd:X} ({self.progman_hwnd})")
        print("Monitoring: EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_MINIMIZESTART, EVENT_SYSTEM_MINIMIZEEND\n")
        return True

    def stop(self) -> None:
        if user32 and self.hook_handle:
            user32.UnhookWinEvent(self.hook_handle)
            print(f"\n[HOOK UNINSTALLED] Clean shutdown.")
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
        # We only care about top-level window events (idObject == 0, OBJID_WINDOW)
        if idObject != 0:
            return

        ev_name = EVENT_NAMES.get(event, f"EVENT_0x{event:04X}")
        now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        cls = _get_class_name(hwnd)
        title = _get_window_text(hwnd)
        fg_hwnd = user32.GetForegroundWindow()

        is_prog = (hwnd == self.progman_hwnd) or (cls == "Progman")
        is_sticky = (hwnd == self.sticky_hwnd)

        # Calculate live relative Z-orders
        sticky_z, progman_z = _get_z_order_positions(self.sticky_hwnd, self.progman_hwnd)

        sticky_vis = bool(user32.IsWindowVisible(self.sticky_hwnd))
        sticky_min = bool(user32.IsIconic(self.sticky_hwnd))
        sticky_parent = user32.GetParent(self.sticky_hwnd)
        sticky_owner = user32.GetWindow(self.sticky_hwnd, GW_OWNER)

        tag = ""
        if is_sticky:
            tag = " [TARGET STICKY]"
        elif is_prog:
            tag = " [PROGMAN/DESKTOP]"

        print(f"{now_str} {ev_name:<26} HWND=0x{hwnd:<8X} Class='{cls[:16]}' Title='{title[:25]}'{tag}")
        print(f"         Foreground=0x{fg_hwnd:<8X} | Sticky: Z={sticky_z:<3} Vis={sticky_vis} Min={sticky_min} Parent=0x{sticky_parent:X} Owner=0x{sticky_owner:X}")
        print(f"         Progman:  Z={progman_z:<3} | Progman Above Sticky? {'YES (OCCLUDING)' if progman_z < sticky_z and progman_z >= 0 else 'NO'}")
        print("-" * 90)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = bootstrap_application(app)
    hwnd = int(window.winId())

    diag = WinEventDiagnostic(sticky_hwnd=hwnd)
    if not diag.start():
        sys.exit(1)

    print("=" * 90)
    print("TEST PROCEDURE:")
    print("1. Make sure Daily Sticky is visible on your screen.")
    print("2. Open Chrome or another app over/near Daily Sticky.")
    print("3. Click and focus Chrome.")
    print("4. Press Win + D once. (Show Desktop)")
    print("5. Wait 2-3 seconds.")
    print("6. Press Win + D again. (Restore Desktop)")
    print("7. Click Chrome.")
    print("8. Click Daily Sticky.")
    print("9. Close the Daily Sticky window or press Ctrl+C in terminal when finished.")
    print("=" * 90 + "\n")

    app.aboutToQuit.connect(diag.stop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
