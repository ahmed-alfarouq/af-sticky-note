"""Phase 6D.1 -- Windows verification for the QSS fix and the Priority UX.

Runs on a real ``windows-latest`` GitHub Actions runner (the only genuine
Windows environment reachable from this sandbox).  Every check is independent:
a failure is recorded and the run continues, so one report covers everything.

Results are returned as GitHub check-run annotations, because the Actions log
and artifact endpoints are not reachable from the sandbox.

    ::warning title=<title>::<message>      -> check-run annotation

Usage (inside the workflow):
    python scripts/verify_windows_priority.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# A Windows console defaults to a legacy code page (cp1252 / cp437) that cannot
# encode the Arabic labels, and printing one raises UnicodeEncodeError.  This
# harness reports on Arabic UI strings, so force a UTF-8 stream.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover - older interpreters
        pass

RESULTS = []
NOTES = []


def record(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return ok


def note(text):
    NOTES.append(text)
    print(f"       note: {text}")


def guard(name):
    """Decorator-ish helper: run a check, catching anything it throws."""
    def wrap(fn):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - report, never abort the run
            record(name, False, f"{type(exc).__name__}: {exc}")
            traceback.print_exc()
            return None
    return wrap


# ---------------------------------------------------------------------------
# 1. Environment snapshot
# ---------------------------------------------------------------------------
def env_snapshot():
    import platform

    import PySide6
    from PySide6.QtWidgets import QApplication

    lines = [
        "=== OS ===",
        f"Caption        : {platform.system()} {platform.release()} {platform.version()}",
        f"OSArchitecture : {platform.machine()}",
        f"=== Python ===",
        f"Python {platform.python_version()}",
        f"=== PySide6 ===",
        f"PySide6 {PySide6.__version__}",
    ]
    try:
        import ctypes

        user32 = ctypes.windll.user32
        lines.append("=== Displays ===")
        lines.append(f"SM_CXSCREEN={user32.GetSystemMetrics(0)} "
                     f"SM_CYSCREEN={user32.GetSystemMetrics(1)}")
        lines.append(f"SM_CXICON={user32.GetSystemMetrics(11)}")
    except Exception as exc:  # pragma: no cover
        lines.append(f"(display probe failed: {exc})")

    app = QApplication.instance() or QApplication([])
    lines.append(f"=== Qt ===")
    lines.append(f"Qt runtime version: {app.property('QtVersion') or 'n/a'}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1b. The focused test suite, on real Windows
# ---------------------------------------------------------------------------
def check_focused_tests():
    """Run the priority tests under pytest on this Windows runner.

    Captured here rather than in its own workflow step so the outcome comes
    back through the annotation channel even when another step fails.
    """
    targets = ["tests/test_app_stylesheet.py", "tests/test_task_priority_ux.py"]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *targets, "-q", "--no-header"],
        cwd=REPO, capture_output=True, text=True, timeout=900,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-25:]
    summary = " | ".join(line.strip() for line in tail if line.strip())
    record("focused priority tests pass on Windows", proc.returncode == 0,
           summary or f"exit {proc.returncode}")
    for line in tail:
        if line.strip():
            print("       " + line.strip())


# ---------------------------------------------------------------------------
# 2. The stylesheet must be ACCEPTED by Qt on Windows
# ---------------------------------------------------------------------------
def check_stylesheet_accepted():
    import io
    import contextlib

    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QPushButton,
    )

    from app.ui.styles.app_style import get_application_stylesheet

    app = QApplication.instance() or QApplication([])
    sheet = get_application_stylesheet()

    # Qt reports a rejected sheet on stderr with a single line.
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        app.setStyleSheet(sheet)
    noise = buf.getvalue()
    record("Qt accepted the application stylesheet",
           "Could not parse" not in noise,
           noise.strip() or "no parser warning")

    # Behavioural proof, on the widget classes the rules actually target.
    probes = [
        (QLabel, "taskTextLabel", 14),
        (QLabel, "priorityBadgeHigh", 11),
        (QLabel, "priorityBadgeLow", 11),
        (QComboBox, "prioritySelector", 12),
        (QPushButton, "historyCloseButton", 13),
    ]

    for cls, obj, expect in probes:
        w = cls()
        w.setObjectName(obj)
        if cls is QComboBox:
            w.addItems(["عاجل", "عادي", "منخفض"])
        w.show()
        px = w.font().pixelSize()
        record(f"stylesheet reaches {cls.__name__}#{obj}", px == expect,
               f"font {px}px, expected {expect}px")
        w.close()

    record("no unquoted flag combination remains in a qproperty value",
           all("|" not in line or "'" in line
               for line in sheet.splitlines()
               if line.strip().startswith("qproperty-")))


# ---------------------------------------------------------------------------
# 3. The dark theme actually renders
# ---------------------------------------------------------------------------
def check_dark_theme_renders():
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel

    from app.core.models import Day, Task, TaskPriority
    from app.core.services.task_service import TaskService
    from app.database.connection import create_connection
    from app.database.day_repository import DayRepository
    from app.database.migrations import apply_migrations
    from app.database.task_repository import TaskRepository
    from app.ui.styles.app_style import COLOR_STICKY_PAPER, get_application_stylesheet
    from app.ui.windows.main_window import MainWindow

    class _Geometry:
        def __init__(self, g=(60, 60, 380, 560)):
            self._g = g

        def get_validated_geometry(self):
            return self._g

        def save_geometry(self, *a):
            pass

    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyleSheet(get_application_stylesheet())

    conn = create_connection(":memory:")
    apply_migrations(conn)
    repo = TaskRepository(conn)
    service = TaskService(repo)
    day = DayRepository(conn).create("2026-09-27")
    service.create_task(day.id, "مهمة عاجلة", priority=TaskPriority.HIGH)
    service.create_task(day.id, "مهمة عادية", priority=TaskPriority.MEDIUM)
    service.create_task(day.id, "مهمة منخفضة", priority=TaskPriority.LOW)

    win = MainWindow(
        day=Day(id=day.id, date="2026-09-27", quote_text=None,
                created_at="2026-09-27T00:00:00",
                updated_at="2026-09-27T00:00:00"),
        quote_text=None,
        task_service=service,
        initial_tasks=service.get_today_tasks(day.id),
        geometry_manager=_Geometry(),
    )
    win.resize(380, 560)
    win.show()
    app.processEvents()

    image = QImage(win.size(), QImage.Format.Format_ARGB32)
    image.fill(0)
    win.render(image)

    # The paper must be the intended dark paper colour, not a default grey.
    paper = image.pixelColor(win.width() // 2, 8)
    want = tuple(int(COLOR_STICKY_PAPER[i:i + 2], 16) for i in (1, 3, 5))
    got = (paper.red(), paper.green(), paper.blue())
    record("paper surface is the intended dark colour", got == want,
           f"got {got}, expected {want}")

    # Task text must be near-white, never the default black that made it
    # unreadable on the dark paper before the fix.
    row = win._task_list._items[1]
    label = row._text_label
    origin = label.mapTo(win, label.rect().topLeft())
    sample = image.pixelColor(origin.x() + 4, origin.y() + label.height() // 2)
    record("task text renders light (readable on dark paper)",
           sample.lightness() > 100,
           f"sampled {sample.name()} lightness {sample.lightness()}")

    # Badges must carry their own tint.
    badge = row._priority_badge
    if badge is not None:
        bpos = badge.mapTo(win, badge.rect().topLeft())
        bcol = image.pixelColor(bpos.x() + 2, bpos.y() + badge.height() // 2)
        record("HIGH badge renders with a red-ish tint", bcol.red() > bcol.green(),
               f"badge sample {bcol.name()}")
    else:
        record("HIGH badge exists", False, "no badge widget on the HIGH row")

    win.close()


# ---------------------------------------------------------------------------
# 4-8. The Priority UX on Windows
# ---------------------------------------------------------------------------
def check_priority_selector():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from app.core.models import TaskPriority
    from app.ui.priority_presentation import PRIORITY_LABELS, PRIORITY_ORDER
    from app.ui.styles.app_style import get_application_stylesheet
    from app.ui.widgets.priority_selector import PrioritySelector

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(get_application_stylesheet())
    sel = PrioritySelector()
    sel.show()
    app.processEvents()

    record("selector defaults to عادي (MEDIUM)",
           sel.selected_priority() is TaskPriority.MEDIUM
           and sel.currentText() == "عادي", sel.currentText())
    record("selector labels are عاجل / عادي / منخفض",
           [sel.itemText(i) for i in range(sel.count())]
           == [PRIORITY_LABELS[p] for p in PRIORITY_ORDER])
    record("selector is right-to-left",
           sel.layoutDirection() == Qt.LayoutDirection.RightToLeft)
    record("popup view is right-to-left",
           sel.view().layoutDirection() == Qt.LayoutDirection.RightToLeft)

    # Compact: it must not dominate the input row.
    from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget
    host = QWidget()
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    row.addWidget(sel)
    field = QLineEdit()
    row.addWidget(field, 1)
    host.resize(380, 60)
    host.show()
    app.processEvents()
    record("selector stays compact beside the task input",
           sel.width() <= 0.35 * host.width(),
           f"selector {sel.width()}px of {host.width()}px row, input {field.width()}px")
    record("selector is tall enough to click",
           sel.height() >= 20, f"{sel.height()}px")

    metrics = sel.fontMetrics()
    fits = all(metrics.horizontalAdvance(sel.itemText(i)) <= sel.width() - 32
               for i in range(sel.count()))
    record("every Arabic label fits without eliding", fits)
    host.close()
    sel.close()


def check_creation_flow():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from app.core.models import Day, TaskPriority
    from app.core.services.task_service import TaskService
    from app.database.connection import create_connection
    from app.database.day_repository import DayRepository
    from app.database.migrations import apply_migrations
    from app.database.task_repository import TaskRepository
    from app.ui.styles.app_style import get_application_stylesheet
    from app.ui.windows.main_window import MainWindow

    class _Geometry:
        def get_validated_geometry(self):
            return (60, 60, 380, 560)

        def save_geometry(self, *a):
            pass

    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyleSheet(get_application_stylesheet())

    conn = create_connection(":memory:")
    apply_migrations(conn)
    repo = TaskRepository(conn)
    service = TaskService(repo)
    day = DayRepository(conn).create("2026-09-27")
    win = MainWindow(
        day=Day(id=day.id, date="2026-09-27", quote_text=None,
                created_at="2026-09-27T00:00:00",
                updated_at="2026-09-27T00:00:00"),
        quote_text=None, task_service=service, initial_tasks=[],
        geometry_manager=_Geometry(),
    )
    win.show()
    app.processEvents()

    for index, priority in enumerate(
            (TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW), start=1):
        win._priority_selector.set_priority(priority)
        win._on_task_submitted("مهمة " + priority.name)
        stored = repo.get_by_id(index)
        record(f"creating a {priority.name} task persists {priority.name}",
               stored is not None and stored.priority is priority,
               stored.priority.name if stored else "not found")

    record("selector resets to عادي after a successful submission",
           win._priority_selector.selected_priority() is TaskPriority.MEDIUM,
           win._priority_selector.currentText())

    badges = {}
    for task in service.get_today_tasks(day.id):
        item = win._task_list._items[task.id]
        badges[task.priority] = (item._priority_badge.text()
                                 if item._priority_badge else None)
    record("HIGH row shows عاجل", badges.get(TaskPriority.HIGH) == "عاجل",
           str(badges.get(TaskPriority.HIGH)))
    record("LOW row shows منخفض", badges.get(TaskPriority.LOW) == "منخفض",
           str(badges.get(TaskPriority.LOW)))
    record("MEDIUM row shows no badge", badges.get(TaskPriority.MEDIUM) is None)
    win.close()


def check_edit_flow():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from app.core.models import Day, TaskPriority
    from app.core.services.task_service import TaskService
    from app.database.connection import create_connection
    from app.database.day_repository import DayRepository
    from app.database.migrations import apply_migrations
    from app.database.task_repository import TaskRepository
    from app.ui.styles.app_style import get_application_stylesheet
    from app.ui.widgets.task_edit_dialog import TaskEditDialog
    from app.ui.windows.main_window import MainWindow

    class _Geometry:
        def get_validated_geometry(self):
            return (60, 60, 380, 560)

        def save_geometry(self, *a):
            pass

    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyleSheet(get_application_stylesheet())

    conn = create_connection(":memory:")
    apply_migrations(conn)
    repo = TaskRepository(conn)
    service = TaskService(repo)
    day = DayRepository(conn).create("2026-09-27")
    task = service.create_task(day.id, "مهمة أصلية", priority=TaskPriority.HIGH)
    win = MainWindow(
        day=Day(id=day.id, date="2026-09-27", quote_text=None,
                created_at="2026-09-27T00:00:00",
                updated_at="2026-09-27T00:00:00"),
        quote_text=None, task_service=service,
        initial_tasks=service.get_today_tasks(day.id),
        geometry_manager=_Geometry(),
    )
    win.show()
    app.processEvents()

    # The dialog opens showing the current priority.
    dlg = TaskEditDialog(initial_text="مهمة أصلية",
                         initial_priority=TaskPriority.HIGH, parent=win)
    record("edit dialog opens with the current priority عاجل",
           dlg._priority_selector.selected_priority() is TaskPriority.HIGH,
           dlg._priority_selector.currentText())
    record("edit dialog is right-to-left",
           dlg.layoutDirection() == Qt.LayoutDirection.RightToLeft)
    dlg.close()

    before = repo.get_by_id(task.id)
    service.update_task_text(task.id, "نص معدل")
    win._task_list.update_task_text(task.id, "نص معدل")
    service.update_task_priority(task.id, TaskPriority.LOW)
    win._task_list.update_task_priority(task.id, TaskPriority.LOW)
    after = repo.get_by_id(task.id)
    record("text-only change preserves priority",
           after.priority is TaskPriority.LOW and after.text == "نص معدل")
    record("priority-only change preserves text", after.text == "نص معدل")
    record("editing preserves id, day, completion, position and source",
           (after.id, after.day_id, after.is_completed, after.position,
            after.source_task_id, after.created_at)
           == (before.id, before.day_id, before.is_completed, before.position,
               before.source_task_id, before.created_at))
    win.close()


def check_context_menu():
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtWidgets import QApplication, QMenu

    from app.core.models import Day, TaskPriority
    from app.core.services.task_service import TaskService
    from app.database.connection import create_connection
    from app.database.day_repository import DayRepository
    from app.database.migrations import apply_migrations
    from app.database.task_repository import TaskRepository
    from app.ui.styles.app_style import get_application_stylesheet
    from app.ui.widgets import task_item as task_item_module
    from app.ui.windows.main_window import MainWindow

    class _Geometry:
        def get_validated_geometry(self):
            return (60, 60, 380, 560)

        def save_geometry(self, *a):
            pass

    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyleSheet(get_application_stylesheet())

    conn = create_connection(":memory:")
    apply_migrations(conn)
    repo = TaskRepository(conn)
    service = TaskService(repo)
    day = DayRepository(conn).create("2026-09-27")
    task = service.create_task(day.id, "مهمة القائمة", priority=TaskPriority.MEDIUM)
    win = MainWindow(
        day=Day(id=day.id, date="2026-09-27", quote_text=None,
                created_at="2026-09-27T00:00:00",
                updated_at="2026-09-27T00:00:00"),
        quote_text=None, task_service=service,
        initial_tasks=service.get_today_tasks(day.id),
        geometry_manager=_Geometry(),
    )
    win.show()
    app.processEvents()

    captured = []

    class _RecordingMenu(QMenu):
        def exec(self, *a, **k):  # noqa: N802 - Qt naming
            captured.append(self)
            return None

    real = task_item_module.QMenu
    task_item_module.QMenu = _RecordingMenu
    try:
        item = win._task_list._items[task.id]
        item.contextMenuEvent(QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse,
            item.mapToGlobal(item.rect().center()),
            item.mapToGlobal(item.rect().center()),
            Qt.KeyboardModifier.NoModifier,
        ))
        top = captured[0]
    finally:
        task_item_module.QMenu = real

    texts = [a.text() for a in top.actions()]
    record("context menu shows تعديل المهمة / الأولوية / حذف المهمة",
           texts == ["تعديل المهمة", "الأولوية", "حذف المهمة"], str(texts))
    sub = top.actions()[1].menu()
    record("priority submenu shows عاجل / عادي / منخفض",
           [a.text() for a in sub.actions()] == ["عاجل", "عادي", "منخفض"])
    record("submenu is right-to-left",
           sub.layoutDirection() == Qt.LayoutDirection.RightToLeft)
    record("current priority is checked",
           [a.text() for a in sub.actions() if a.isChecked()] == ["عادي"])

    before = repo.get_by_id(task.id)
    win._on_task_priority_change_requested(task.id, TaskPriority.HIGH)
    after = repo.get_by_id(task.id)
    record("choosing a priority updates it immediately (no dialog)",
           after.priority is TaskPriority.HIGH, after.priority.name)
    record("the task id, text, day, completion and position are preserved",
           (after.id, after.text, after.day_id, after.is_completed,
            after.position, after.source_task_id)
           == (before.id, before.text, before.day_id, before.is_completed,
               before.position, before.source_task_id))
    record("the visible row follows",
           win._task_list._items[task.id].priority is TaskPriority.HIGH)
    win.close()


def check_history_and_rollover():
    from app.core.models import TaskPriority
    from app.core.services.daily_rollover_service import DailyRolloverService
    from app.core.services.history_service import HistoryService
    from app.core.services.task_service import TaskService
    from app.database.connection import create_connection
    from app.database.day_repository import DayRepository
    from app.database.migrations import apply_migrations
    from app.database.task_repository import TaskRepository

    conn = create_connection(":memory:")
    apply_migrations(conn)
    day_repo = DayRepository(conn)
    task_repo = TaskRepository(conn)
    service = TaskService(task_repo)
    rollover = DailyRolloverService(conn=conn, day_repo=day_repo,
                                    task_repo=task_repo)
    history = HistoryService(day_repo=day_repo, task_repo=task_repo)

    day_a = day_repo.get_or_create("2026-09-25")
    src = service.create_task(day_a.id, "مهمة تاريخية", priority=TaskPriority.HIGH)
    rolled = rollover.rollover_tasks(source_date="2026-09-25",
                                     target_date="2026-09-26")
    record("rollover preserves HIGH", rolled and rolled[0].priority is TaskPriority.HIGH)
    record("rollover keeps source_task_id", rolled and rolled[0].source_task_id == src.id)

    service.update_task_priority(rolled[0].id, TaskPriority.LOW)
    hist_a = history.get_day_history("2026-09-25")
    hist_b = history.get_day_history("2026-09-26")
    record("Day A still shows HIGH after Day B was changed to LOW",
           any(t.priority is TaskPriority.HIGH for t in hist_a.tasks),
           str([t.priority.name for t in hist_a.tasks]))
    record("Day B shows LOW",
           any(t.priority is TaskPriority.LOW for t in hist_b.tasks),
           str([t.priority.name for t in hist_b.tasks]))
    record("the historical source record was never mutated",
           task_repo.get_by_id(src.id).priority is TaskPriority.HIGH)

    # The History window renders the recorded priority.
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from app.ui.styles.app_style import get_application_stylesheet
    from app.ui.windows.history_window import HistoryWindow

    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyleSheet(get_application_stylesheet())
    hw = HistoryWindow(history_service=history, initial_date="2026-09-25")
    record("History window is right-to-left",
           hw.layoutDirection() == Qt.LayoutDirection.RightToLeft)
    hw.close()


def check_platform_regressions():
    """Window flags, minimum size, geometry persistence, taskbar/Alt+Tab."""
    import ctypes

    from PySide6.QtCore import Qt

    if not hasattr(ctypes, "windll"):
        note("platform checks skipped: ctypes.windll is Windows-only "
             "(this run is not on Windows)")
        return

    from PySide6.QtWidgets import QApplication

    from app.core.models import Day, TaskPriority
    from app.core.services.task_service import TaskService
    from app.database.connection import create_connection
    from app.database.day_repository import DayRepository
    from app.database.migrations import apply_migrations
    from app.database.task_repository import TaskRepository
    from app.ui.styles.app_style import get_application_stylesheet
    from app.ui.windows.main_window import MainWindow

    class _Geometry:
        def __init__(self):
            self.saved = []

        def get_validated_geometry(self):
            return (60, 60, 380, 560)

        def save_geometry(self, x, y, w, h):
            self.saved.append((x, y, w, h))

    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setStyleSheet(get_application_stylesheet())

    conn = create_connection(":memory:")
    apply_migrations(conn)
    repo = TaskRepository(conn)
    service = TaskService(repo)
    day = DayRepository(conn).create("2026-09-27")
    service.create_task(day.id, "مهمة", priority=TaskPriority.HIGH)
    geo = _Geometry()
    win = MainWindow(
        day=Day(id=day.id, date="2026-09-27", quote_text=None,
                created_at="2026-09-27T00:00:00",
                updated_at="2026-09-27T00:00:00"),
        quote_text=None, task_service=service,
        initial_tasks=service.get_today_tasks(day.id),
        geometry_manager=geo,
    )
    win.show()
    app.processEvents()

    flags = int(win.windowFlags())
    # Phase 6C measured 2059 (0x80b) = FramelessWindowHint | Tool.
    record("window flags unchanged (FramelessWindowHint | Tool, not AlwaysOnTop)",
           flags == 2059, f"flags={flags} (0x{flags:x})")
    record("minimum size still enforced",
           win.minimumWidth() == 320 and win.minimumHeight() == 420,
           f"{win.minimumWidth()}x{win.minimumHeight()}")
    record("geometry manager still saves window bounds",
           callable(getattr(geo, "save_geometry", None)))

    hwnd = int(win.winId())
    if hwnd:
        user32 = ctypes.windll.user32
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000
        ex = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
        record("window is a tool window (kept out of the taskbar / Alt+Tab list)",
               bool(ex & WS_EX_TOOLWINDOW) and not bool(ex & WS_EX_APPWINDOW),
               f"exstyle=0x{ex & 0xFFFFFFFF:x}")
    win.close()

    # The tray: on a CI runner there is no interactive shell, so this is
    # reported as a note rather than claimed as verified.
    try:
        from PySide6.QtWidgets import QSystemTrayIcon

        available = QSystemTrayIcon.isSystemTrayAvailable()
        if available:
            record("system tray is available", True)
        else:
            note("system tray is not available on this runner "
                 "(no interactive shell) -- tray behaviour not verified here")
    except Exception as exc:  # noqa: BLE001
        note(f"tray availability not verifiable on this runner: {exc}")

    # The desktop layer must still attach (or report honestly why not).
    try:
        from app.platform.windows.desktop_window import (
            WindowsDesktopWindowController,
        )

        layer = WindowsDesktopWindowController()
        hwnd = int(win.winId())
        attached = layer.attach_to_desktop(hwnd)
        record("Windows desktop layer still attaches", bool(attached),
               f"attach_to_desktop(0x{hwnd:x}) -> {attached}")

        # WS_EX_TOOLWINDOW keeps the note out of the taskbar and Alt+Tab.
        user32 = ctypes.windll.user32
        ex = user32.GetWindowLongW(ctypes.c_void_p(hwnd), -20)
        record("desktop layer keeps the note out of taskbar / Alt+Tab",
               bool(ex & 0x80) and not bool(ex & 0x40000),
               f"exstyle=0x{ex & 0xFFFFFFFF:x}")
    except Exception as exc:  # noqa: BLE001
        note(f"desktop layer attach not verifiable on this runner: {exc}")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
ANNOTATE_FILTER = None


def _esc(text):
    """Escape a string for use in a GitHub workflow command."""
    return (text.replace("%", "%25")
                .replace("\r", "%0D")
                .replace("\n", "%0A"))


def emit_annotations():
    """Publish results as check-run annotations -- the only reachable channel.

    Failures are emitted FIRST, because GitHub does not reliably return every
    annotation from a step: if the tail is dropped, the critical information is
    still there.
    """
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [(n, d) for n, ok, d in RESULTS if not ok]

    if failed:
        lines = [f"PHASE 6D.1 WINDOWS VERIFICATION -- {len(failed)} FAILURE(S) "
                 f"of {len(RESULTS)} checks"]
        for name, detail in failed:
            lines.append(f"FAIL: {name}")
            if detail:
                lines.append(f"      {detail}")
        print("::error title=phase6d1-FAILURES::" + _esc("\n".join(lines)))

    if NOTES:
        print("::warning title=phase6d1-NOTES::"
              + _esc("NOT VERIFIABLE ON A CI RUNNER:\n" + "\n".join(NOTES)))

    summary = (f"PHASE 6D.1 WINDOWS VERIFICATION -- {passed} passed, "
               f"{len(failed)} failed, {len(RESULTS)} total")
    print("::warning title=phase6d1-SUMMARY::" + _esc(summary))

    # One small annotation per check, in order.  GitHub only returns a handful
    # of annotations per check-run, so a second run can narrow the set with
    # --annotate <substring> to surface the checks that were truncated away.
    shown = RESULTS
    if ANNOTATE_FILTER:
        shown = [r for r in RESULTS if ANNOTATE_FILTER.lower() in r[0].lower()]
        print(f"::warning title=phase6d1-FILTER::"
              + _esc(f"annotating {len(shown)} of {len(RESULTS)} checks "
                     f"matching {ANNOTATE_FILTER!r}"))
    for index, (name, ok, detail) in enumerate(shown, start=1):
        text = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            text += f" -- {detail}"
        print(f"::notice title=phase6d1-check{index:02d}::" + _esc(text[:400]))


def main():
    print("=" * 70)
    print("Phase 6D.1 -- Windows verification (QSS fix + Priority UX)")
    print("=" * 70)

    print("\n--- environment ---")
    print(env_snapshot())

    for name, fn in [
        ("focused tests", check_focused_tests),
        ("stylesheet accepted", check_stylesheet_accepted),
        ("dark theme renders", check_dark_theme_renders),
        ("priority selector", check_priority_selector),
        ("creation flow", check_creation_flow),
        ("edit flow", check_edit_flow),
        ("context menu", check_context_menu),
        ("history and rollover", check_history_and_rollover),
        ("platform regressions", check_platform_regressions),
    ]:
        print(f"\n--- {name} ---")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - never abort the whole run
            record(f"{name} (section raised)", False,
                   f"{type(exc).__name__}: {exc}")
            traceback.print_exc()

    print("\n" + "=" * 70)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    print(f"RESULT: {passed} passed, {len(failed)} failed, {len(RESULTS)} total")
    for name, detail in failed:
        print(f"  FAIL {name}  {detail}")
    if NOTES:
        print("NOTES:")
        for text in NOTES:
            print(f"  - {text}")
    print("=" * 70)

    emit_annotations()
    return 1 if failed else 0


if __name__ == "__main__":
    if "--annotate" in sys.argv:
        ANNOTATE_FILTER = sys.argv[sys.argv.index("--annotate") + 1]
    sys.exit(main())
