"""R-kbd-a11y: tab order, shortcuts, focus, accessible names (v3 §11, §14).

Priority semantics are untouched: no test here changes or asserts priority
meanings; the priority combo is covered only for its dynamic accessible
name, which does not depend on the unresolved mapping.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


class _FakeSettings:
    def __init__(self, pinned=True):
        self._data = {"WindowState/pinned": pinned}

    def beginGroup(self, group):
        self._group = group

    def endGroup(self):
        pass

    def value(self, key, default=None):
        return self._data.get(f"{self._group}/{key}", default)

    def setValue(self, key, value):
        self._data[f"{self._group}/{key}"] = value


class _FakeController:
    def __init__(self, ok=True):
        self.ok = ok
        self.calls = []

    def set_pinned(self, hwnd, pinned):
        self.calls.append((hwnd, pinned))
        return self.ok

    def attach_to_desktop(self, hwnd):
        return self.ok

    def detach_from_desktop(self, hwnd):
        return self.ok

    def is_attached(self):
        return False


def _wiring(db_connection):
    from app.core.services.category_service import CategoryService
    from app.core.services.history_service import HistoryService
    from app.core.services.task_service import TaskService
    from app.database.category_repository import CategoryRepository
    from app.database.day_repository import DayRepository
    from app.database.task_repository import TaskRepository
    from app.ui.category_icons import CategoryIconProvider

    task_repo = TaskRepository(db_connection)
    category_repo = CategoryRepository(db_connection)
    service = TaskService(task_repo=task_repo, category_repo=category_repo)
    category_service = CategoryService(category_repo)
    history = HistoryService(DayRepository(db_connection), task_repo)
    provider = CategoryIconProvider(Path(__file__).resolve().parent.parent / "assets" / "icons")
    return service, category_service, history, provider, DayRepository(db_connection)


def _make_window(service, category_service, history, provider, day,
                 controller=None):
    from app.ui.pin_state import PinStateManager
    from app.ui.windows.main_window import MainWindow

    return MainWindow(
        day=day,
        quote_text="q",
        task_service=service,
        history_service=history,
        on_exit_requested=MagicMock(),
        category_service=category_service,
        icon_provider=provider,
        window_controller=controller or _FakeController(),
        pin_state_manager=PinStateManager(_FakeSettings(True)),
    )


def _tag(window, widget):
    if widget is None:
        return None
    for name in ("_pin_btn", "_archive_btn", "_settings_btn", "_close_btn",
                 "_task_input", "_add_btn", "_category_selector",
                 "_priority_selector"):
        if widget is getattr(window, name):
            return name
    if widget is window._task_list._section_label:
        return "group_header"
    parent = widget.parent()
    while parent is not None and type(parent).__name__ != "TaskItem":
        parent = parent.parent()
    if parent is not None:
        kind = type(widget).__name__
        return f"row{parent.task_id}:{kind}"
    return type(widget).__name__


# ------------------------------------------------------------ tab order

def test_tab_order_follows_spec_sequence(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    todo = service.create_task(day.id, "todo")
    done = service.create_task(day.id, "done")
    assert todo is not None and done is not None
    service.toggle_task_completion(done.id, True)
    window = _make_window(service, category_service, history, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        window.resize(380, 640)
        window.show()
        window.activateWindow()
        QApplication.instance().processEvents()
        window._pin_btn.setFocus()
        window._task_input.setText("x")  # enables Add (disabled buttons take no tab stop)
        sequence = []
        for _ in range(14):
            sequence.append(_tag(window, window.focusWidget()))
            window.focusNextChild()
        assert sequence == [
            "_pin_btn", "_archive_btn", "_settings_btn", "_close_btn",
            f"row{todo.id}:QCheckBox", f"row{todo.id}:_TaskTextLabel",
            f"row{todo.id}:IconButton", "group_header",
            f"row{done.id}:QCheckBox", f"row{done.id}:_TaskTextLabel",
            f"row{done.id}:IconButton", "_task_input", "_add_btn",
            "_category_selector",
        ]
    finally:
        window.close()


# ------------------------------------------------------------ shortcuts

def test_shortcuts_registered_once_with_window_scope(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from PySide6.QtGui import QShortcut

    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day)
    try:
        shortcuts = window.findChildren(QShortcut)
        by_key = {s.key().toString(): s for s in shortcuts}
        assert set(by_key) == {"Ctrl+N", "Ctrl+Shift+P"}
        for shortcut in by_key.values():
            assert shortcut.context() == Qt.ShortcutContext.WindowShortcut
    finally:
        window.close()


def test_ctrl_n_focuses_input_without_touching_text(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from PySide6.QtCore import QEvent

    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day)
    try:
        window.resize(380, 640)
        window.show()
        window.activateWindow()
        QApplication.instance().processEvents()
        window._task_input.setText("hello")
        window._pin_btn.setFocus()
        QApplication.sendEvent(
            window,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier),
        )
        QApplication.instance().processEvents()
        assert window._task_input.hasFocus()
        assert window._task_input.text() == "hello"
    finally:
        window.close()


def test_ctrl_shift_p_toggles_pin_through_platform(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from PySide6.QtCore import QEvent

    controller = _FakeController(ok=True)
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day,
                          controller=controller)
    try:
        window.resize(380, 640)
        window.show()
        window.activateWindow()
        QApplication.instance().processEvents()
        assert window.is_pinned() is True
        QApplication.sendEvent(
            window,
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_P,
                      Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier),
        )
        QApplication.instance().processEvents()
        assert window.is_pinned() is False
        assert controller.calls and controller.calls[-1][1] is False
    finally:
        window.close()


# ------------------------------------------------------------ accessible names

def test_accessible_names_match_spec_table(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day)
    try:
        assert window._pin_btn.accessibleName() == "إلغاء التثبيت"
        assert window._archive_btn.accessibleName() == "الأرشيف"
        assert window._settings_btn.accessibleName() == "إعدادات"
        assert window._close_btn.accessibleName() == "إغلاق"
        assert window._task_input.accessibleName() == "مهمة جديدة"
        assert window._add_btn.accessibleName() == "إضافة المهمة"
        assert window._category_selector.accessibleName() == "الفئة"
        ring = window._date_header._ring
        ring.set_progress(1, 4)
        assert ring.accessibleName() == "أُنجز 1 من 4"
        assert ring.toolTip() == "أُنجز 1 من 4"
    finally:
        window.close()


def test_checkbox_name_is_the_task_text_and_priority_name_is_dynamic(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority

    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    task = service.create_task(day.id, "نص المهمة")
    assert task is not None
    window = _make_window(service, category_service, history, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        item = window._task_list._items[task.id]
        assert item._checkbox.accessibleName() == "نص المهمة"
        window._priority_selector.set_priority(TaskPriority.HIGH)
        assert window._priority_selector.accessibleName() == "الأولوية: عاجل"
        window._priority_selector.set_priority(TaskPriority.MEDIUM)
        assert window._priority_selector.accessibleName() == "الأولوية: عادي"
    finally:
        window.close()


def test_interactive_controls_take_keyboard_focus(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day)
    try:
        for widget in (window._pin_btn, window._archive_btn, window._settings_btn,
                       window._close_btn, window._task_input, window._add_btn,
                       window._category_selector, window._priority_selector,
                       window._task_list._section_label):
            assert widget.focusPolicy() & Qt.FocusPolicy.TabFocus, widget
    finally:
        window.close()


def test_focus_ring_rules_cover_interactive_names():
    from pathlib import Path

    sheet = (Path(__file__).resolve().parent.parent / "app" / "ui" / "styles" / "app_style.py").read_text(
        encoding="utf-8"
    )
    for name in ("pinButton", "headerIconButton", "taskAddButton", "taskTitleEdit",
                 "rowDeleteButton", "completedGroupHeader", "categoryChip"):
        assert f"#{name}:focus" in sheet or f"#{name}[focused" in sheet, name
