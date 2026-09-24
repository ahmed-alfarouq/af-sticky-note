"""Standalone Windows diagnostic for Daily Sticky Win+D behavior.

Captures Win32 window metrics, Z-order neighbors, class names,
and Qt window states across initial launch, after Win+D, and after restore.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import sys

# Ensure repository root is on sys.path regardless of how the script is invoked
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.main import bootstrap_application

# Win32 definitions
user32 = getattr(ctypes.windll, "user32", None)

GWL_STYLE = -16
GWL_EXSTYLE = -20
GW_HWNDNEXT = 2
GW_HWNDPREV = 3
GW_OWNER = 4


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


def _get_window_rect(hwnd: int) -> str:
    if not user32 or not hwnd:
        return "N/A"
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return f"({rect.left}, {rect.top}, {rect.right}, {rect.bottom}) [w={rect.right-rect.left}, h={rect.bottom-rect.top}]"


def _describe_hwnd(hwnd: int) -> str:
    if not user32 or not hwnd:
        return "None"
    title = _get_window_text(hwnd)
    cls = _get_class_name(hwnd)
    visible = bool(user32.IsWindowVisible(hwnd))
    rect = _get_window_rect(hwnd)
    return f"HWND=0x{hwnd:X} ({hwnd}) | Class='{cls}' | Title='{title}' | Visible={visible} | Rect={rect}"


def inspect_state(label: str, window, hwnd: int) -> None:
    print(f"\n{'='*25} {label} {'='*25}")

    # 1. Qt State
    print("\n--- [Qt State] ---")
    print(f"window.winId():      {int(window.winId())}")
    print(f"window.isVisible():  {window.isVisible()}")
    print(f"window.isHidden():   {window.isHidden()}")
    print(f"window.isMinimized():{window.isMinimized()}")
    print(f"window.windowState():{window.windowState()}")
    print(f"window.windowFlags():{window.windowFlags()}")

    if not user32:
        print("\n[Win32]: user32 not available on this platform.")
        print(f"{'='*60}\n")
        return

    # 2. Win32 Direct State
    print("\n--- [Win32 Direct State] ---")
    get_long = getattr(user32, "GetWindowLongPtrW", getattr(user32, "GetWindowLongW", None))
    style = get_long(hwnd, GWL_STYLE) if get_long else 0
    exstyle = get_long(hwnd, GWL_EXSTYLE) if get_long else 0

    print(f"HWND:                0x{hwnd:X} ({hwnd})")
    print(f"IsWindow:            {bool(user32.IsWindow(hwnd))}")
    print(f"IsWindowVisible:     {bool(user32.IsWindowVisible(hwnd))}")
    print(f"IsIconic(minimized): {bool(user32.IsIconic(hwnd))}")
    print(f"GWL_STYLE:           0x{style:08X}")
    print(f"GWL_EXSTYLE:         0x{exstyle:08X}")
    print(f"  WS_EX_TOOLWINDOW:  {bool(exstyle & 0x00000080)}")
    print(f"  WS_EX_APPWINDOW:   {bool(exstyle & 0x00040000)}")
    print(f"  WS_EX_TOPMOST:     {bool(exstyle & 0x00000008)}")
    print(f"Parent HWND:         0x{user32.GetParent(hwnd):X}")
    print(f"Owner HWND:          0x{user32.GetWindow(hwnd, GW_OWNER):X}")
    print(f"WindowRect:          {_get_window_rect(hwnd)}")

    fg_hwnd = user32.GetForegroundWindow()
    print(f"Foreground HWND:     {_describe_hwnd(fg_hwnd)}")

    # 3. Z-Order Inspection (Above and Below in Top-Level Stack)
    print("\n--- [Z-Order Neighborhood] ---")
    hwnd_prev = user32.GetWindow(hwnd, GW_HWNDPREV)  # Window immediately above in Z-order
    hwnd_next = user32.GetWindow(hwnd, GW_HWNDNEXT)  # Window immediately below in Z-order

    print(f"Window ABOVE (HWNDPREV): {_describe_hwnd(hwnd_prev)}")
    print(f"TARGET WINDOW (DailySticky): {_describe_hwnd(hwnd)}")
    print(f"Window BELOW (HWNDNEXT): {_describe_hwnd(hwnd_next)}")

    print(f"{'='*60}\n")


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)

    # Use the real production bootstrap composition root
    window = bootstrap_application(app)
    hwnd = int(window.winId())

    print("\n[DIAGNOSTIC STARTED] Real Daily Sticky application bootstrapped.")
    inspect_state("STAGE 1: INITIAL (Before Win+D)", window, hwnd)

    print(">>> INSTRUCTIONS FOR STAGE 2:")
    print(">>> 1. Switch to another app (e.g. Chrome, Notepad, or File Explorer).")
    print(">>> 2. Press Win + D ONCE.")
    print(">>> Recording STAGE 2 in 10 seconds...\n")

    def run_stage_2() -> None:
        inspect_state("STAGE 2: AFTER WIN+D (First Press)", window, hwnd)
        print(">>> INSTRUCTIONS FOR STAGE 3:")
        print(">>> Press Win + D AGAIN to restore normal desktop windows.")
        print(">>> Recording STAGE 3 in 10 seconds...\n")
        QTimer.singleShot(10000, run_stage_3)

    def run_stage_3() -> None:
        inspect_state("STAGE 3: AFTER RESTORE (Second Win+D)", window, hwnd)
        print("[DIAGNOSTIC COMPLETE] Exiting in 3 seconds...")
        QTimer.singleShot(3000, app.quit)

    QTimer.singleShot(10000, run_stage_2)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
