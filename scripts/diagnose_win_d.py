"""Diagnostic script to inspect exact HWND and Qt state before and after Win+D.

Run on the target Windows workstation:
    python scripts/diagnose_win_d.py
"""
import ctypes
from ctypes import wintypes
import time
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from app.core.models import Day
from app.core.services.task_service import TaskService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.task_repository import TaskRepository
from app.infrastructure.clock import local_today_iso, utc_now_iso
from app.platform.windows.desktop_window import WindowsDesktopWindowController
from app.ui.windows.main_window import MainWindow

user32 = ctypes.windll.user32

GWL_STYLE = -16
GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8


def get_hwnd_state(hwnd: int) -> dict:
    is_window = bool(user32.IsWindow(hwnd))
    is_visible = bool(user32.IsWindowVisible(hwnd))
    is_iconic = bool(user32.IsIconic(hwnd))
    is_zoomed = bool(user32.IsZoomed(hwnd))
    
    get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    style = get_long(hwnd, GWL_STYLE)
    exstyle = get_long(hwnd, GWL_EXSTYLE)
    owner = user32.GetWindow(hwnd, 4)  # GW_OWNER = 4
    parent = user32.GetParent(hwnd)

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

    return {
        "hwnd": hwnd,
        "IsWindow": is_window,
        "IsWindowVisible": is_visible,
        "IsIconic (minimized)": is_iconic,
        "IsZoomed (maximized)": is_zoomed,
        "Parent HWND": parent,
        "Owner HWND": owner,
        "GWL_STYLE": hex(style),
        "GWL_EXSTYLE": hex(exstyle),
        "WS_EX_TOOLWINDOW": bool(exstyle & 0x00000080),
        "WS_EX_APPWINDOW": bool(exstyle & 0x00040000),
        "WS_EX_TOPMOST": bool(exstyle & 0x00000008),
        "Rect": f"({rect.left}, {rect.top}, {rect.right}, {rect.bottom})",
    }


def print_state(label: str, window: MainWindow, hwnd: int):
    print(f"\n{'='*20} {label} {'='*20}")
    print(f"Qt isVisible:   {window.isVisible()}")
    print(f"Qt isMinimized: {window.isMinimized()}")
    print(f"Qt isHidden:    {window.isHidden()}")
    print(f"Qt windowState: {window.windowState()}")
    
    native = get_hwnd_state(hwnd)
    for k, v in native.items():
        print(f"Native {k:<22}: {v}")
    print('='*50)


def main():
    app = QApplication(sys.argv)
    
    # In-memory test setup
    now = utc_now_iso()
    today_str = local_today_iso()
    day = Day(id=1, date=today_str, quote_text="حكمة تشخيصية", created_at=now, updated_at=now)
    
    conn = create_connection(":memory:")
    apply_migrations(conn)
    task_repo = TaskRepository(conn)
    task_service = TaskService(task_repo)

    window = MainWindow(
        day=day,
        quote_text="حكمة تشخيصية",
        task_service=task_service,
        initial_tasks=(),
    )
    window.setGeometry(100, 100, 380, 560)
    window.show()

    hwnd = int(window.winId())
    ctrl = WindowsDesktopWindowController()
    ctrl.attach_to_desktop(hwnd)

    print("\n[DIAGNOSTIC] Window initialized and attached.")
    print_state("STAGE 1: INITIAL STATE (Before Win+D)", window, hwnd)

    print("\n>>> PLEASE SWITCH TO ANOTHER APP (e.g. Chrome, Notepad) and PRESS Win + D NOW! <<<")
    print("Waiting 10 seconds for user to press Win + D...")

    def check_stage_2():
        print_state("STAGE 2: AFTER WIN+D (First Press)", window, hwnd)
        print("\n>>> PLEASE PRESS Win + D AGAIN TO RESTORE APPS! <<<")
        print("Waiting 10 seconds for user to press Win + D again...")
        QTimer.singleShot(10000, check_stage_3)

    def check_stage_3():
        print_state("STAGE 3: AFTER SECOND WIN+D (Restored)", window, hwnd)
        print("\n[DIAGNOSTIC] Finished test sequence. Exiting in 3 seconds...")
        QTimer.singleShot(3000, app.quit)

    QTimer.singleShot(10000, check_stage_2)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
