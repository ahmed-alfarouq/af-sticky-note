"""R-task-list: inline title editing, hover delete, collapsible group (v3 §7).

Priority semantics are untouched: no test here changes or asserts priority
meanings, and the meta-line/badge behavior is covered elsewhere.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


def _wiring(db_connection):
    from app.core.services.category_service import CategoryService
    from app.core.services.task_service import TaskService
    from app.database.category_repository import CategoryRepository
    from app.database.day_repository import DayRepository
    from app.database.task_repository import TaskRepository
    from app.ui.category_icons import CategoryIconProvider

    task_repo = TaskRepository(db_connection)
    category_repo = CategoryRepository(db_connection)
    service = TaskService(task_repo=task_repo, category_repo=category_repo)
    category_service = CategoryService(category_repo)
    provider = CategoryIconProvider(Path(__file__).resolve().parent.parent / "assets" / "icons")
    return task_repo, service, category_service, provider, DayRepository(db_connection)


def _make_item(task, categories=(), provider=None):
    from app.ui.widgets.task_item import TaskItem

    return TaskItem(task, categories=categories, icon_provider=provider)


def _make_task(task_id=1, text="مهمة", **kwargs):
    from app.core.models import Task, TaskPriority

    params = dict(
        id=task_id, day_id=1, text=text, is_completed=False, position=0,
        created_at="t", updated_at="t", priority=TaskPriority.MEDIUM,
        category_id="general",
    )
    params.update(kwargs)
    return Task(**params)


def _make_window(service, category_service, provider, day):
    from app.ui.windows.main_window import MainWindow

    return MainWindow(
        day=day,
        quote_text=day.quote_text,
        task_service=service,
        on_exit_requested=MagicMock(),
        category_service=category_service,
        icon_provider=provider,
    )


# ------------------------------------------------------------ inline editing

def test_inline_commit_persists_text_and_preserves_everything_else(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority

    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    task = service.create_task(day.id, "قبل", priority=TaskPriority.HIGH, category_id="work")
    assert task is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        item = window._task_list._items[task.id]
        received = []
        item.inline_edit_committed.connect(lambda tid, text: received.append((tid, text)))

        item._start_inline_edit()
        assert item.is_editing_inline()
        assert item._edit_field.text() == "قبل"
        assert item._edit_field.maxLength() == 200
        item._edit_field.setText("  بعد  ")
        item._commit_inline_edit()

        assert received == [(task.id, "بعد")]
        assert not item.is_editing_inline()
        window._on_task_inline_edit_committed(task.id, "بعد")

        stored = task_repo.get_by_id(task.id)
        assert stored is not None
        assert stored.text == "بعد"
        assert stored.id == task.id
        assert stored.day_id == task.day_id
        assert stored.category_id == "work"
        assert stored.priority == TaskPriority.HIGH
        assert stored.is_completed == task.is_completed
        assert stored.position == task.position
        assert stored.source_task_id == task.source_task_id
        assert stored.created_at == task.created_at
        assert len(service.get_today_tasks(day.id)) == 1  # no duplicate
        assert item.task_text == "بعد"
    finally:
        window.close()


def test_inline_cancel_and_empty_edit_change_nothing(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    task = service.create_task(day.id, "ثابتة", category_id="life")
    assert task is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        item = window._task_list._items[task.id]
        received = []
        item.inline_edit_committed.connect(lambda tid, text: received.append((tid, text)))

        item._start_inline_edit()
        item._edit_field.setText("معدلة")
        item._cancel_inline_edit()
        assert received == []
        assert not item.is_editing_inline()
        assert item.task_text == "ثابتة"

        item._start_inline_edit()
        item._edit_field.setText("   ")
        item._commit_inline_edit()
        assert received == []
        assert task_repo.get_by_id(task.id).text == "ثابتة"
    finally:
        window.close()


def test_inline_edit_starts_from_title_interaction():
    if _skip_without_qt():
        return
    _qt_app()
    from PySide6.QtGui import QKeyEvent

    item = _make_item(_make_task())
    try:
        assert not item.is_editing_inline()
        # Double-click on the title opens the field with text selected.
        item.eventFilter(item._text_label, QEvent(QEvent.Type.MouseButtonDblClick))
        assert item.is_editing_inline()
        assert item._edit_field.selectedText() == "مهمة"
        item._cancel_inline_edit()
        # Enter on the focused title opens it too.
        key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.KeyboardModifier.NoModifier)
        item.eventFilter(item._text_label, key_event)
        assert item.is_editing_inline()
        # Escape cancels without emitting.
        received = []
        item.inline_edit_committed.connect(lambda tid, text: received.append((tid, text)))
        esc = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        item.eventFilter(item._edit_field, esc)
        assert received == []
        assert not item.is_editing_inline()
    finally:
        item.close()


# ------------------------------------------------------------ hover delete

def test_delete_button_hidden_until_hover_or_focus():
    if _skip_without_qt():
        return
    _qt_app()
    item = _make_item(_make_task())
    try:
        assert item._delete_opacity.opacity() == 0.0
        assert item._delete_btn.accessibleName() == "حذف المهمة"
        assert item._delete_btn.toolTip() == "حذف المهمة"
        item.eventFilter(item._checkbox, QEvent(QEvent.Type.Enter))
        assert item._delete_opacity.opacity() == 1.0
        item.eventFilter(item._checkbox, QEvent(QEvent.Type.Leave))
        assert item._delete_opacity.opacity() == 0.0
        # Focus needs a visible widget; showing focuses the checkbox, so
        # focus-within legitimately reveals the control.
        item.show()
        QApplication.instance().processEvents()
        assert item._delete_opacity.opacity() == 1.0
        focused = QApplication.instance().focusWidget()
        if focused is not None:
            focused.clearFocus()
        QApplication.instance().processEvents()
        assert item._delete_opacity.opacity() == 0.0
        item._delete_btn.setFocus()
        assert item._delete_opacity.opacity() == 1.0
        item._delete_btn.clearFocus()
        item.eventFilter(item._checkbox, QEvent(QEvent.Type.Leave))
        assert item._delete_opacity.opacity() == 0.0
    finally:
        item.close()


def test_delete_click_removes_only_its_task(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    first = service.create_task(day.id, "أولى", category_id="work")
    second = service.create_task(day.id, "ثانية", category_id="life")
    assert first is not None and second is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        item = window._task_list._items[first.id]
        before_completed = window._task_list._items[second.id]._checkbox.isChecked()
        item._delete_btn.click()
        assert task_repo.get_by_id(first.id) is None
        assert first.id not in window._task_list._items
        remaining = task_repo.get_by_id(second.id)
        assert remaining is not None and remaining.text == "ثانية"
        assert window._task_list._items[second.id]._checkbox.isChecked() == before_completed
    finally:
        window.close()


# ------------------------------------------------------------ collapsible group

def test_completed_group_collapses_without_touching_records(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    done = service.create_task(day.id, "منجزة", category_id="work")
    todo = service.create_task(day.id, "نشطة", category_id="life")
    assert done is not None and todo is not None
    service.toggle_task_completion(done.id, True)
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    task_list = window._task_list
    window.show()
    QApplication.instance().processEvents()
    try:
        before = [(t.id, t.text, t.is_completed) for t in task_list.tasks_snapshot()]
        assert task_list.is_completed_expanded() is True
        assert task_list._items[done.id].isVisible()

        task_list._section_label.click()
        assert task_list.is_completed_expanded() is False
        assert task_list._items[done.id].isHidden()
        assert task_list._items[todo.id].isVisible()
        assert [(t.id, t.text, t.is_completed) for t in task_list.tasks_snapshot()] == before
        assert [t.category_id for t in task_list.tasks_snapshot()] == ["life", "work"]

        task_list._section_label.click()
        assert task_list.is_completed_expanded() is True
        assert task_list._items[done.id].isVisible()
        # No database writes happened through collapse/expand.
        assert task_repo.get_by_id(done.id).is_completed is True
        assert task_repo.get_by_id(todo.id).is_completed is False
    finally:
        window.close()


def test_group_header_hidden_without_completed_and_text_updates(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    service.create_task(day.id, "نشطة")
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        assert window._task_list._section_label.isHidden()
    finally:
        window.close()


# ------------------------------------------------------------ press animation

def test_press_animation_params_restore_and_geometry():
    if _skip_without_qt():
        return
    _qt_app()
    from PySide6.QtCore import QSize

    from app.ui.widgets.task_item import (
        PRESSED_ICON_SIZE,
        PRESS_ANIMATION_MS,
        PRESS_ICON_SIZE,
    )

    assert PRESS_ANIMATION_MS == 150
    assert (PRESSED_ICON_SIZE, PRESS_ICON_SIZE) == (14, 16)
    item = _make_item(_make_task())
    try:
        item.show()
        QApplication.instance().processEvents()
        assert (item._checkbox.width(), item._checkbox.height()) == (32, 32)
        assert item._press_animation is None
        item._checkbox.click()
        animation = item._press_animation
        assert animation is not None
        assert animation.duration() == 150
        assert animation.startValue() == QSize(16, 16)
        assert animation.endValue() == QSize(14, 14)
        animation.setCurrentTime(150)
        QApplication.instance().processEvents()
        assert item._checkbox.iconSize() == QSize(16, 16)
        assert (item._checkbox.width(), item._checkbox.height()) == (32, 32)
        # Interrupted run restarts safely and still restores.
        item._checkbox.click()
        first = item._press_animation
        item._checkbox.click()
        assert item._press_animation is not first
        item._press_animation.setCurrentTime(150)
        QApplication.instance().processEvents()
        assert item._checkbox.iconSize() == QSize(16, 16)
    finally:
        item.close()


def test_checkbox_focus_ring_rule_is_scoped():
    from pathlib import Path

    sheet = (Path(__file__).resolve().parent.parent / "app" / "ui" / "styles" / "app_style.py").read_text(
        encoding="utf-8"
    )
    block = sheet.split("QCheckBox#taskCheckBox:focus")[1].split("}}")[0]
    assert "2px" in block and ("#8FB8D8" in block or "{COLOR_SOFT}" in block)


# ------------------------------------------------------------ focus transfer

def test_toggle_moves_focus_to_next_open_task(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    first = service.create_task(day.id, "أولى")
    second = service.create_task(day.id, "ثانية")
    assert first is not None and second is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        window.resize(380, 640)
        window.show()
        window.activateWindow()
        QApplication.instance().processEvents()
        window._task_list._items[first.id]._checkbox.setFocus()
        window._on_task_completed_toggled(first.id, True)
        QApplication.instance().processEvents()
        assert window._task_list._items[second.id]._checkbox.hasFocus()
        from app.database.task_repository import TaskRepository

        assert TaskRepository(db_connection).get_by_id(first.id).is_completed is True
    finally:
        window.close()


def test_toggle_last_open_task_focuses_input(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    only = service.create_task(day.id, "وحيدة")
    assert only is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        window.resize(380, 640)
        window.show()
        window.activateWindow()
        QApplication.instance().processEvents()
        window._task_list._items[only.id]._checkbox.setFocus()
        window._on_task_completed_toggled(only.id, True)
        QApplication.instance().processEvents()
        assert window._task_input.hasFocus()
    finally:
        window.close()


def test_toggle_middle_task_focuses_next_open_task(db_connection):
    """v3 §7.3 'next': completing a middle row moves to its successor."""
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    first = service.create_task(day.id, "أولى")
    middle = service.create_task(day.id, "وسطى")
    last = service.create_task(day.id, "أخيرة")
    assert first is not None and middle is not None and last is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        window.resize(380, 640)
        window.show()
        window.activateWindow()
        QApplication.instance().processEvents()
        window._task_list._items[middle.id]._checkbox.setFocus()
        window._on_task_completed_toggled(middle.id, True)
        QApplication.instance().processEvents()
        assert window._task_list._items[last.id]._checkbox.hasFocus()
        assert not window._task_list._items[first.id]._checkbox.hasFocus()
    finally:
        window.close()


def test_toggle_last_of_several_open_tasks_focuses_input(db_connection):
    """No open task follows the toggled row: focus goes to the add input."""
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    first = service.create_task(day.id, "أولى")
    last = service.create_task(day.id, "أخيرة")
    assert first is not None and last is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        window.resize(380, 640)
        window.show()
        window.activateWindow()
        QApplication.instance().processEvents()
        window._task_list._items[last.id]._checkbox.setFocus()
        window._on_task_completed_toggled(last.id, True)
        QApplication.instance().processEvents()
        assert window._task_input.hasFocus()
        remaining = [t for t in service.get_today_tasks(day.id) if not t.is_completed]
        assert [t.id for t in remaining] == [first.id]
    finally:
        window.close()


def test_uncompleting_keeps_focus_on_its_row(db_connection):
    """An uncompleted row is open again: focus stays where it is."""
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    task = service.create_task(day.id, "مهمة")
    assert task is not None
    service.toggle_task_completion(task.id, True)
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    try:
        window.resize(380, 640)
        window.show()
        window.activateWindow()
        QApplication.instance().processEvents()
        item = window._task_list._items[task.id]
        item._checkbox.setFocus()
        window._on_task_completed_toggled(task.id, False)
        QApplication.instance().processEvents()
        assert item._checkbox.hasFocus()
    finally:
        window.close()
