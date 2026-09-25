"""Targeted Win+D diagnostic capturing complete Z-order and shell window relationships.

Calculates exact relative Z-indices between Daily Sticky, Progman, WorkerW,
SHELLDLL_DefView, and normal applications across:
  Stage 1: Before Win+D
  Stage 2: After 1st Win+D (Show Desktop)
  Stage 3: After 2nd Win+D (Restore)
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import sys

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


def _get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    if not user32 or not hwnd:
        return (0, 0, 0, 0)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def capture_snapshot(target_hwnd: int) -> dict:
    if not user32:
        return {}

    curr = user32.GetTopWindow(0)
    actual_z = 0
    chain = []

    target_data = {}
    progman_data = None
    workerw_list = []
    defview_parent = None

    get_long = getattr(user32, "GetWindowLongPtrW", getattr(user32, "GetWindowLongW", None))

    while curr:
        cls = _get_class_name(curr)
        title = _get_window_text(curr)
        vis = bool(user32.IsWindowVisible(curr))
        iconic = bool(user32.IsIconic(curr))
        rect = _get_window_rect(curr)
        style = get_long(curr, GWL_STYLE) if get_long else 0
        exstyle = get_long(curr, GWL_EXSTYLE) if get_long else 0
        parent = user32.GetParent(curr)
        owner = user32.GetWindow(curr, GW_OWNER)

        has_defview = bool(user32.FindWindowExW(curr, 0, "SHELLDLL_DefView", None))

        entry = {
            "z": actual_z,
            "hwnd": curr,
            "class": cls,
            "title": title,
            "visible": vis,
            "iconic": iconic,
            "rect": rect,
            "style": hex(style),
            "exstyle": hex(exstyle),
            "parent": parent,
            "owner": owner,
            "has_defview": has_defview,
            "topmost": bool(exstyle & 0x00000008),
            "tool": bool(exstyle & 0x00000080),
            "app": bool(exstyle & 0x00040000),
        }

        if curr == target_hwnd:
            target_data = entry
        if cls == "Progman":
            progman_data = entry
        if cls == "WorkerW":
            workerw_list.append(entry)
        if has_defview:
            defview_parent = entry

        chain.append(entry)
        actual_z += 1
        curr = user32.GetWindow(curr, GW_HWNDNEXT)

    fg = user32.GetForegroundWindow()
    fg_title = _get_window_text(fg)
    fg_cls = _get_class_name(fg)

    return {
        "target": target_data,
        "progman": progman_data,
        "workerw": workerw_list,
        "defview": defview_parent,
        "foreground": {"hwnd": fg, "title": fg_title, "class": fg_cls},
        "total_top_level": actual_z,
        "chain": chain,
    }


def print_comparative_stage(label: str, snap: dict) -> None:
    print(f"\n{'='*25} {label} {'='*25}")
    fg = snap["foreground"]
    print(f"Foreground Window: 0x{fg['hwnd']:X} | Class='{fg['class']}' | Title='{fg['title']}'")
    print(f"Total Top-Level HWNDs scanned: {snap['total_top_level']}")

    tgt = snap["target"]
    if not tgt:
        print("ERROR: Target Daily Sticky HWND not found in top-level chain!")
        print("="*70 + "\n")
        return

    print(f"\n[Daily Sticky Window State]")
    print(f"  HWND:             0x{tgt['hwnd']:X} ({tgt['hwnd']})")
    print(f"  True Z-Index:     {tgt['z']} (0 is front-most)")
    print(f"  IsWindowVisible:  {tgt['visible']}")
    print(f"  IsIconic:         {tgt['iconic']}")
    print(f"  Parent HWND:      0x{tgt['parent']:X}")
    print(f"  Owner HWND:       0x{tgt['owner']:X}")
    print(f"  GWL_STYLE:        {tgt['style']}")
    print(f"  GWL_EXSTYLE:      {tgt['exstyle']} (WS_EX_TOOLWINDOW={tgt['tool']}, WS_EX_TOPMOST={tgt['topmost']})")
    print(f"  Rectangle:        {tgt['rect']}")

    prog = snap["progman"]
    if prog:
        print(f"\n[Progman]")
        print(f"  HWND:             0x{prog['hwnd']:X}")
        print(f"  True Z-Index:     {prog['z']}")
        print(f"  Visible:          {prog['visible']}")
        print(f"  Rect:             {prog['rect']}")
        print(f"  Is Above Sticky?  {'YES (Occluding)' if prog['z'] < tgt['z'] else 'NO (Below Sticky)'}")

    if snap["workerw"]:
        print(f"\n[WorkerW Windows] (Count: {len(snap['workerw'])})")
        for idx, w in enumerate(snap['workerw']):
            has_dv = " [Hosts SHELLDLL_DefView]" if w['has_defview'] else ""
            above = "YES (Above Sticky)" if w['z'] < tgt['z'] else "NO (Below Sticky)"
            print(f"  WorkerW #{idx+1}: HWND=0x{w['hwnd']:X} | Z={w['z']} | Visible={w['visible']} | Rect={w['rect']} | Above Sticky={above}{has_dv}")

    if snap["defview"]:
        dv = snap["defview"]
        print(f"\n[Desktop Icons Host (SHELLDLL_DefView Parent)]")
        print(f"  Host Class:       '{dv['class']}' | HWND=0x{dv['hwnd']:X} | Z={dv['z']}")
        print(f"  Is Above Sticky?  {'YES' if dv['z'] < tgt['z'] else 'NO'}")

    # Inspect windows directly above Daily Sticky in the physical Z stack
    chain = snap["chain"]
    tgt_z = tgt["z"]
    windows_above = [w for w in chain if w["z"] < tgt_z and w["visible"]]
    print(f"\n[Visible Windows Physically Above Sticky] (Count: {len(windows_above)})")
    # Show the 5 windows immediately above
    for w in windows_above[-5:]:
        print(f"  Z={w['z']:<4} HWND=0x{w['hwnd']:<8X} Class={w['class'][:18]:<18} Min={str(w['iconic']):<5} Title={w['title'][:30]}")

    print("="*70 + "\n")


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = bootstrap_application(app)
    hwnd = int(window.winId())

    print("\n[DIAGNOSTIC ENGINE READY] Capturing baseline state...")
    s1 = capture_snapshot(hwnd)
    print_comparative_stage("STAGE 1: BEFORE WIN+D", s1)

    print(">>> INSTRUCTIONS FOR STAGE 2:")
    print(">>> 1. Switch to another app (e.g. Chrome, Notepad, File Explorer) that covers the sticky note.")
    print(">>> 2. Press Win + D ONCE.")
    print(">>> Measuring Stage 2 in 10 seconds...\n")

    def run_stage_2() -> None:
        s2 = capture_snapshot(hwnd)
        print_comparative_stage("STAGE 2: AFTER FIRST WIN+D (Show Desktop)", s2)
        print(">>> INSTRUCTIONS FOR STAGE 3:")
        print(">>> Press Win + D AGAIN to restore normal desktop windows.")
        print(">>> Measuring Stage 3 in 10 seconds...\n")
        QTimer.singleShot(10000, run_stage_3)

    def run_stage_3() -> None:
        s3 = capture_snapshot(hwnd)
        print_comparative_stage("STAGE 3: AFTER SECOND WIN+D (Restore)", s3)
        print("[DIAGNOSTIC COMPLETE] Exiting in 3 seconds...")
        QTimer.singleShot(3000, app.quit)

    QTimer.singleShot(10000, run_stage_2)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
