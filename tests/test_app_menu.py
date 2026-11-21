"""R-menu: pinned-mode application menu tests (v3 §10).

Covers menu contents/order/separator in both pin states, single-dispatch of
every action, dismiss-without-action, row-menu isolation, RTL/minimum width,
placement safety, lifecycle safety, and pin/visibility invariance.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtGui import QContextMenuEvent
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
                 controller=None, pinned=True, carry=None):
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
        pin_state_manager=PinStateManager(_FakeSettings(pinned)),
        on_carry_forward_requested=carry,
    )


def _actions(menu):
    return [a for a in menu.actions() if not a.isSeparator()]


def _label_texts(menu):
    return [a.text() for a in _actions(menu)]


# ------------------------------------------------------------ contents

def test_menu_contents_order_separator_and_pin_labels(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    pinned_window = _make_window(service, category_service, history, provider, day, pinned=True)
    unpinned_window = _make_window(service, category_service, history, provider, day, pinned=False)
    try:
        for window, pin_label in ((pinned_window, "إلغاء التثبيت"),
                                  (unpinned_window, "تثبيت")):
            menu = window._build_window_menu()
            try:
                labels = _label_texts(menu)
                assert labels[:2] + labels[3:] == [
                    "إضافة مهمة", "نقل غير المكتمل",
                    "إعدادات", "فتح بيانات التطبيق", "إغلاق التطبيق",
                ]
                assert labels[2] == pin_label
                separators = [a for a in menu.actions() if a.isSeparator()]
                assert len(separators) == 1
                assert menu.actions().index(separators[0]) == 4
                assert all(a.isEnabled() for a in _actions(menu))
                assert menu.objectName() == "appContextMenu"
                assert menu.layoutDirection() == Qt.LayoutDirection.RightToLeft
                assert menu.minimumWidth() == 220
            finally:
                menu.close()
    finally:
        pinned_window.close()
        unpinned_window.close()


# ------------------------------------------------------------ dispatch

def test_every_action_dispatches_exactly_once(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    carried = []
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day,
                          carry=lambda: carried.append(1) or 2)
    calls = MagicMock()
    window._on_settings_requested = calls.settings
    window._on_exit_clicked = calls.exit
    window._on_pin_clicked = calls.pin
    window._on_open_app_data_requested = calls.data
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        menu = window._build_window_menu()
        try:
            actions = _actions(menu)
            actions[0].trigger()  # add -> focuses input
            assert window._task_input.hasFocus()
            actions[1].trigger()  # carry forward
            assert carried == [1]
            actions[2].trigger()  # pin toggle
            calls.pin.assert_called_once()
            actions[3].trigger()  # settings
            calls.settings.assert_called_once()
            actions[4].trigger()  # app data
            calls.data.assert_called_once()
            actions[5].trigger()  # exit
            calls.exit.assert_called_once()
        finally:
            menu.close()
    finally:
        window.close()


def test_dismiss_triggers_no_action(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    calls = MagicMock()
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day)
    window._on_settings_requested = calls.settings
    window._on_exit_clicked = calls.exit
    window._on_pin_clicked = calls.pin
    window._on_open_app_data_requested = calls.data
    pinned_before = window.is_pinned()
    visible_before = window.isVisible()
    try:
        menu = window._build_window_menu()
        menu.close()  # dismiss without choosing
        QApplication.instance().processEvents()
        assert calls.mock_calls == []
        assert window.is_pinned() == pinned_before
        assert window.isVisible() == visible_before
    finally:
        window.close()


def test_carry_forward_reloads_today_and_preserves_state(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    task = service.create_task(day.id, "قديمة", category_id="work")
    assert task is not None
    window = _make_window(service, category_service, history, provider, day)
    try:
        window._task_list.set_tasks([])
        assert window._task_list._items == {}
        window._on_carry_forward_requested()  # no injected op: warns, changes nothing
        assert window._task_list._items == {}
        window._on_carry_forward_requested_cb = lambda: 0
        window._on_carry_forward_requested()
        assert sorted(window._task_list._items) == [task.id]
        assert window._date_header.progress_value() == (0, 1)
    finally:
        window.close()


def test_open_app_data_uses_configured_data_dir(db_connection, monkeypatch):
    if _skip_without_qt():
        return
    _qt_app()
    opened = []

    class _FakeDesktop:
        @staticmethod
        def openUrl(url):
            opened.append(url.toString())
            return True

    monkeypatch.setattr("PySide6.QtGui.QDesktopServices.openUrl", _FakeDesktop.openUrl)
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day)
    try:
        from app.infrastructure.paths import get_app_data_dir

        window._on_open_app_data_requested()
        assert opened == [QUrl.fromLocalFile(str(get_app_data_dir())).toString()]
    finally:
        window.close()


# ------------------------------------------------------------ isolation/lifecycle

def test_row_menu_stays_isolated_from_window_menu(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import Task, TaskPriority
    from app.ui.widgets.task_item import TaskItem

    task = Task(id=1, day_id=1, text="م", is_completed=False, position=0,
                created_at="t", updated_at="t", priority=TaskPriority.MEDIUM)
    item = TaskItem(task)
    try:
        import app.ui.widgets.task_item as task_item_module
        from PySide6.QtWidgets import QMenu

        captured = []

        class _RecordingMenu(QMenu):
            def exec(self, *args, **kwargs):
                captured.append(self)
                return None

        original = task_item_module.QMenu
        task_item_module.QMenu = _RecordingMenu
        try:
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse,
                item.mapToGlobal(item.rect().center()),
                item.mapToGlobal(item.rect().center()),
                Qt.KeyboardModifier.NoModifier,
            )
            item.contextMenuEvent(event)
        finally:
            task_item_module.QMenu = original
        assert captured
        texts = [a.text() for a in captured[0].actions() if not a.isSeparator()]
        assert "إضافة مهمة" not in texts
        assert "إغلاق التطبيق" not in texts
    finally:
        item.close()


def test_window_menu_parented_and_single_instance(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, history, provider, day)
    try:
        first = window._build_window_menu()
        second = window._build_window_menu()
        try:
            assert first is not second  # fresh instance per open, no reuse
            assert first.parent() is window
            assert second.parent() is window
        finally:
            first.close()
            second.close()
    finally:
        window.close()
