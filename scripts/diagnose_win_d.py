"""Complete top-level Z-order inspection across Win+D stages.

Walks the full top-level Z-order chain from top to bottom using
GetTopWindow(NULL) -> GetWindow(hwnd, GW_HWNDNEXT).

For each top-level window, captures:
- HWND
- Process ID & Name
- Window Title & Class Name
- Visibility, Minimized (IsIconic)
- Window Rect
- Extended Styles (WS_EX_TOPMOST, WS_EX_TOOLWINDOW, WS_EX_APPWINDOW)
- Identifies Shell/Desktop Windows: Progman, WorkerW, SHELLDLL_DefView
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
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

GWL_STYLE = -16
GWL_EXSTYLE = -20
GW_HWNDNEXT = 2


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
    return f"({rect.left},{rect.top})-({rect.right},{rect.bottom}) [{rect.right-rect.left}x{rect.bottom-rect.top}]"


def _get_process_id(hwnd: int) -> int:
    if not user32 or not hwnd:
        return 0
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def walk_full_z_order(target_hwnd: int) -> list[dict]:
    """Walk the complete top-level Z-order chain from front-most to back-most."""
    if not user32:
        return []

    results = []
    # Get top-level window at top of Z-order
    curr = user32.GetTopWindow(0)
    index = 0

    get_long = getattr(user32, "GetWindowLongPtrW", getattr(user32, "GetWindowLongW", None))

    while curr:
        is_visible = bool(user32.IsWindowVisible(curr))
        is_iconic = bool(user32.IsIconic(curr))
        title = _get_window_text(curr)
        cls = _get_class_name(curr)
        rect_str = _get_window_rect(curr)
        pid = _get_process_id(curr)

        style = get_long(curr, GWL_STYLE) if get_long else 0
        exstyle = get_long(curr, GWL_EXSTYLE) if get_long else 0

        is_topmost = bool(exstyle & 0x00000008)
        is_tool = bool(exstyle & 0x00000080)
        is_app = bool(exstyle & 0x00040000)

        # Highlight important window identities
        is_target = (curr == target_hwnd)
        is_progman = (cls == "Progman")
        is_workerw = (cls == "WorkerW")
        has_defview = bool(user32.FindWindowExW(curr, 0, "SHELLDLL_DefView", None))

        # Filter out 0x0 zero-size or non-existent invisible helper message windows to keep output readable,
        # but keep all windows that could participate in visual stacking or shell structure.
        if is_visible or is_target or is_progman or is_workerw or has_defview:
            results.append({
                "z_index": index,
                "hwnd": curr,
                "is_target": is_target,
                "class": cls,
                "title": title,
                "pid": pid,
                "visible": is_visible,
                "iconic": is_iconic,
                "rect": rect_str,
                "topmost": is_topmost,
                "tool": is_tool,
                "app": is_app,
                "is_progman": is_progman,
                "is_workerw": is_workerw,
                "has_defview": has_defview,
            })
            index += 1

        curr = user32.GetWindow(curr, GW_HWNDNEXT)

    return results


def print_stage_z_order(label: str, window, target_hwnd: int) -> None:
    print(f"\n{'='*30} {label} {'='*30}")

    fg_hwnd = user32.GetForegroundWindow() if user32 else 0
    fg_title = _get_window_text(fg_hwnd)
    fg_cls = _get_class_name(fg_hwnd)
    print(f"Foreground Window: 0x{fg_hwnd:X} | Class='{fg_cls}' | Title='{fg_title}'")
    print(f"DailySticky Window: 0x{target_hwnd:X} | Qt isVisible={window.isVisible()}, isMinimized={window.isMinimized()}\n")

    print(f"{'Z':<4} {'HWND':<10} {'FLAG':<14} {'CLASS':<18} {'VIS':<5} {'MIN':<5} {'TM':<4} {'TL':<4} {'RECT':<28} {'TITLE'}")
    print("-" * 115)

    entries = walk_full_z_order(target_hwnd)
    target_pos = None

    for item in entries:
        flag = ""
        if item["is_target"]:
            flag = "[TARGET]"
            target_pos = item["z_index"]
        elif item["is_progman"]:
            flag = "[PROGMAN]"
        elif item["has_defview"]:
            flag = "[DEFVIEW/ICONS]"
        elif item["is_workerw"]:
            flag = "[WORKERW]"

        h_str = f"0x{item['hwnd']:X}"
        v_str = "YES" if item["visible"] else "no"
        m_str = "YES" if item["iconic"] else "no"
        tm_str = "Y" if item["topmost"] else "-"
        tl_str = "Y" if item["tool"] else "-"

        # Truncate title if long
        t_str = (item["title"][:28] + "..") if len(item["title"]) > 30 else item["title"]

        row = (
            f"{item['z_index']:<4} {h_str:<10} {flag:<14} {item['class'][:17]:<18} "
            f"{v_str:<5} {m_str:<5} {tm_str:<4} {tl_str:<4} {item['rect']:<28} {t_str}"
        )
        if item["is_target"]:
            print(f">>> {row}")
        else:
            print(f"    {row}")

    print("-" * 115)
    print(f"Total Participative Windows: {len(entries)} | Target Sticky Z-Index: {target_pos} (0 is front-most)")
    print("=" * 80 + "\n")


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = bootstrap_application(app)
    hwnd = int(window.winId())

    print("\n[DIAGNOSTIC ENGINE ACTIVE] Bootstrap complete.")
    print_stage_z_order("STAGE 1: BEFORE WIN+D", window, hwnd)

    print(">>> INSTRUCTIONS FOR STAGE 2:")
    print(">>> 1. Switch to a normal app (e.g. Chrome, Notepad, File Explorer).")
    print(">>> 2. Press Win + D ONCE.")
    print(">>> Measuring full Z-order in 10 seconds...\n")

    def run_stage_2() -> None:
        print_stage_z_order("STAGE 2: AFTER WIN+D (First Press)", window, hwnd)
        print(">>> INSTRUCTIONS FOR STAGE 3:")
        print(">>> Press Win + D AGAIN to restore normal desktop windows.")
        print(">>> Measuring full Z-order in 10 seconds...\n")
        QTimer.singleShot(10000, run_stage_3)

    def run_stage_3() -> None:
        print_stage_z_order("STAGE 3: AFTER RESTORE (Second Win+D)", window, hwnd)
        print("[DIAGNOSTIC COMPLETE] Exiting in 3 seconds...")
        QTimer.singleShot(3000, app.quit)

    QTimer.singleShot(10000, run_stage_2)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
