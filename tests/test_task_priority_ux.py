"""Tests for Phase 6D -- completing the user-facing Task Priority UX.

Covers the whole priority flow end to end:

* choosing a priority for a new task (selector defaults, labels, values),
* editing text and/or priority through the edit dialog,
* changing priority directly from the task context menu,
* the visual priority indication on a task row,
* priority preservation across rollover and its immutability in history,
* RTL layout of every new surface.

Qt tests no-op (rather than fail) when PySide6 is unavailable, following the
convention used by the rest of this project's UI tests.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Optional

from app.core.models import Day, Task, TaskPriority
from app.core.services.daily_rollover_service import DailyRolloverService
from app.core.services.history_service import HistoryService
from app.core.services.task_service import TaskService
from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.task_repository import TaskRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@contextmanager
def _patched(module, name, value):
    """Temporarily replace ``module.name`` -- no pytest fixture required.

    The portable backend suite runs these tests without pytest installed, so
    the ``monkeypatch`` fixture is deliberately not used here.
    """
    original = getattr(module, name)
    setattr(module, name, value)
    try:
        yield value
    finally:
        setattr(module, name, original)


# ---------------------------------------------------------------------------
# Optional Qt support
# ---------------------------------------------------------------------------
try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


def _make_task(
    task_id: Optional[int] = None,
    day_id: int = 1,
    text: str = "مهمة",
    is_completed: bool = False,
    position: int = 0,
    priority: TaskPriority = TaskPriority.MEDIUM,
    source_task_id: Optional[int] = None,
) -> Task:
    return Task(
        id=task_id,
        day_id=day_id,
        text=text,
        is_completed=is_completed,
        position=position,
        created_at="2026-09-27T00:00:00",
        updated_at="2026-09-27T00:00:00",
        priority=priority,
        source_task_id=source_task_id,
    )


# ===========================================================================
# 1. Creation
# ===========================================================================
def test_new_task_defaults_to_medium_priority(db_connection):
    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")

    created = service.create_task(day.id, "مهمة بدون أولوية محددة")

    assert created is not None
    assert created.priority is TaskPriority.MEDIUM
    assert created.priority == TaskPriority.MEDIUM


def test_new_task_keeps_the_selected_priority(db_connection):
    repo = TaskRepository(db_connection)
    service = TaskService(repo)
    day = DayRepository(db_connection).create("2026-09-27")

    for priority in (TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW):
        created = service.create_task(day.id, "اتصل بالعميل", priority=priority)

        assert created is not None
        assert created.priority is priority
        # The value round-trips through the database unchanged.
        stored = repo.get_by_id(created.id)
        assert stored is not None
        assert stored.priority is priority


def test_priority_selector_defaults_to_medium():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.priority_selector import PrioritySelector

    selector = PrioritySelector()

    assert selector.selected_priority() is TaskPriority.MEDIUM


def test_priority_selector_round_trips_every_value():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.priority_selector import PrioritySelector

    selector = PrioritySelector()
    for priority in (TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW):
        selector.set_priority(priority)
        assert selector.selected_priority() is priority

    # Back to the neutral default.
    selector.set_priority(TaskPriority.MEDIUM)
    assert selector.selected_priority() is TaskPriority.MEDIUM


def test_priority_labels_are_arabic_and_cover_every_priority():
    from app.ui.priority_presentation import (
        PRIORITY_LABELS,
        PRIORITY_ORDER,
        priority_label,
    )

    assert set(PRIORITY_ORDER) == set(PRIORITY_LABELS) == set(TaskPriority)
    assert PRIORITY_LABELS[TaskPriority.HIGH] == "عاجل"
    assert PRIORITY_LABELS[TaskPriority.MEDIUM] == "عادي"
    assert PRIORITY_LABELS[TaskPriority.LOW] == "منخفض"
    assert priority_label(TaskPriority.HIGH) == "عاجل"
    # An unknown value must never produce an empty label.
    assert priority_label(None) == "عادي"


def test_selector_never_exposes_an_index_or_a_raw_string():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.priority_selector import PrioritySelector

    selector = PrioritySelector()

    assert isinstance(selector.selected_priority(), TaskPriority)


# ===========================================================================
# 2. Editing
# ===========================================================================
def test_edit_dialog_opens_with_the_current_priority():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_edit_dialog import TaskEditDialog

    for priority in (TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW):
        dialog = TaskEditDialog(initial_text="اتصل بالعميل", initial_priority=priority)
        assert dialog.get_priority() is priority


def test_edit_dialog_changing_text_preserves_priority(db_connection):
    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")
    task = service.create_task(day.id, "نص أصلي", priority=TaskPriority.HIGH)

    # Only the text changes.
    assert service.update_task_text(task.id, "نص معدل") is True

    stored = TaskRepository(db_connection).get_by_id(task.id)
    assert stored.text == "نص معدل"
    assert stored.priority is TaskPriority.HIGH


def test_edit_dialog_changing_priority_preserves_text(db_connection):
    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")
    task = service.create_task(day.id, "نص أصلي", priority=TaskPriority.LOW)

    # Only the priority changes.
    service.update_task_priority(task.id, TaskPriority.HIGH)

    stored = TaskRepository(db_connection).get_by_id(task.id)
    assert stored.text == "نص أصلي"
    assert stored.priority is TaskPriority.HIGH


def test_edit_dialog_changing_both_persists_both(db_connection):
    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")
    task = service.create_task(day.id, "نص أصلي", priority=TaskPriority.MEDIUM)

    service.update_task_text(task.id, "نص معدل")
    service.update_task_priority(task.id, TaskPriority.HIGH)

    stored = TaskRepository(db_connection).get_by_id(task.id)
    assert stored.text == "نص معدل"
    assert stored.priority is TaskPriority.HIGH


def test_edit_dialog_validation_still_rejects_blank_text(db_connection):
    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")
    task = service.create_task(day.id, "نص صحيح", priority=TaskPriority.HIGH)

    assert service.update_task_text(task.id, "") is False
    assert service.update_task_text(task.id, "   ") is False

    stored = TaskRepository(db_connection).get_by_id(task.id)
    assert stored.text == "نص صحيح"
    assert stored.priority is TaskPriority.HIGH


def test_priority_update_preserves_every_other_field(db_connection):
    """A priority change must be an in-place update, never a new record."""
    repo = TaskRepository(db_connection)
    day = DayRepository(db_connection).create("2026-09-27")
    service = TaskService(repo)

    source = service.create_task(day.id, "مصدر", priority=TaskPriority.MEDIUM)
    task = service.create_task(
        day.id, "مهمة مرتبطة", priority=TaskPriority.MEDIUM,
    )
    # Give it a real source relationship and a completion state.
    repo.set_completed(task.id, True)
    before = repo.get_by_id(task.id)
    assert before is not None

    service.update_task_priority(task.id, TaskPriority.LOW)

    after = repo.get_by_id(task.id)
    assert after is not None
    assert after.id == before.id                      # same record, not a new one
    assert after.day_id == before.day_id
    assert after.text == before.text
    assert after.is_completed is True                 # completion preserved
    assert after.position == before.position          # order preserved
    assert after.source_task_id == before.source_task_id
    assert after.created_at == before.created_at
    assert after.priority is TaskPriority.LOW
    # The unrelated task is untouched.
    assert repo.get_by_id(source.id).priority is TaskPriority.MEDIUM


# ===========================================================================
# 3. Context menu
# ===========================================================================
def _trigger_context_menu(item):
    """Build the item's context menu without showing it.

    ``QMenu.exec`` cannot be monkeypatched on the sip class itself, so the
    module-level name that ``TaskItem`` imported is swapped for a recording
    subclass whose ``exec`` just captures the menu instead of blocking.
    """
    import app.ui.widgets.task_item as task_item_module
    from PySide6.QtWidgets import QMenu

    captured: list = []

    class _RecordingMenu(QMenu):
        def exec(self, *args, **kwargs):  # noqa: N802 - Qt naming
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

    assert captured, "contextMenuEvent did not build a menu"
    return captured[0]


def test_context_menu_shows_the_current_priority_as_checked():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_item import TaskItem

    for priority in (TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW):
        item = TaskItem(_make_task(priority=priority))
        menu = _trigger_context_menu(item)

        priority_menu = next(
            (action.menu() for action in menu.actions() if action.menu() is not None), None
        )
        assert priority_menu is not None, "no priority submenu was built"

        checked = [a.text() for a in priority_menu.actions() if a.isChecked()]
        expected = {TaskPriority.HIGH: "عاجل", TaskPriority.MEDIUM: "عادي",
                    TaskPriority.LOW: "منخفض"}[priority]
        assert checked == [expected], f"{priority} should show {expected} as checked"


def test_context_menu_priority_change_emits_the_domain_value():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_item import TaskItem

    item = TaskItem(_make_task(task_id=7, priority=TaskPriority.HIGH))
    received = []
    item.priority_change_requested.connect(lambda tid, p: received.append((tid, p)))

    menu = _trigger_context_menu(item)
    priority_menu = next(a.menu() for a in menu.actions() if a.menu() is not None)
    low_action = next(
        a for a in priority_menu.actions() if a.text() == "منخفض"
    )
    low_action.trigger()

    assert received == [(7, TaskPriority.LOW)]


def test_context_menu_priority_change_persists(db_connection):
    repo = TaskRepository(db_connection)
    service = TaskService(repo)
    day = DayRepository(db_connection).create("2026-09-27")

    transitions = (
        (TaskPriority.HIGH, TaskPriority.LOW),
        (TaskPriority.LOW, TaskPriority.HIGH),
        (TaskPriority.MEDIUM, TaskPriority.HIGH),
        (TaskPriority.HIGH, TaskPriority.MEDIUM),
    )
    for start, target in transitions:
        task = service.create_task(day.id, "مهمة", priority=start)

        # Exactly what the context menu handler does: update through the service.
        service.update_task_priority(task.id, target)

        stored = repo.get_by_id(task.id)
        assert stored is not None
        assert stored.priority is target
        assert stored.text == "مهمة"
        assert stored.id == task.id


# ===========================================================================
# 4. Visual priority indication
# ===========================================================================
def test_task_item_shows_a_badge_only_for_high_and_low():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_item import TaskItem

    high = TaskItem(_make_task(priority=TaskPriority.HIGH))
    low = TaskItem(_make_task(priority=TaskPriority.LOW))
    medium = TaskItem(_make_task(priority=TaskPriority.MEDIUM))

    assert high._priority_badge is not None
    assert high._priority_badge.text() == "عاجل"
    assert high._priority_badge.objectName() == "priorityBadgeHigh"

    assert low._priority_badge is not None
    assert low._priority_badge.text() == "منخفض"
    assert low._priority_badge.objectName() == "priorityBadgeLow"

    # MEDIUM stays badge-free: priority must remain secondary to the text.
    assert medium._priority_badge is None


def test_task_item_badge_updates_when_priority_changes():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_item import TaskItem

    item = TaskItem(_make_task(priority=TaskPriority.MEDIUM))
    assert item._priority_badge is None
    assert item.priority is TaskPriority.MEDIUM

    item.update_task_priority(TaskPriority.HIGH)
    assert item.priority is TaskPriority.HIGH
    assert item._priority_badge is not None
    assert item._priority_badge.text() == "عاجل"
    assert item._priority_badge.objectName() == "priorityBadgeHigh"

    # Back to MEDIUM: the badge disappears again, nothing stale is left.
    item.update_task_priority(TaskPriority.MEDIUM)
    assert item.priority is TaskPriority.MEDIUM
    assert item._priority_badge is None


def test_task_item_badge_survives_completion():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_item import TaskItem

    item = TaskItem(_make_task(priority=TaskPriority.HIGH, is_completed=False))
    item.set_completed_silently(True)

    assert item._priority_badge is not None
    assert item._priority_badge.text() == "عاجل"


# ===========================================================================
# 5. Rollover
# ===========================================================================
def test_rollover_preserves_priority(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)
    rollover = DailyRolloverService(
        conn=db_connection, day_repo=day_repo, task_repo=task_repo
    )

    for index, priority in enumerate(
        (TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW)
    ):
        day_a = day_repo.get_or_create(f"2026-09-2{index}")
        task_a = service.create_task(day_a.id, "مهمة متراكمة", priority=priority)

        rolled = rollover.rollover_tasks(
            source_date=f"2026-09-2{index}", target_date=f"2026-09-3{index}"
        )

        assert len(rolled) == 1
        assert rolled[0].priority is priority
        assert rolled[0].source_task_id == task_a.id
        assert rolled[0].is_completed is False
        assert rolled[0].text == "مهمة متراكمة"

        # The historical source task is completely unchanged.
        source = task_repo.get_by_id(task_a.id)
        assert source is not None
        assert source.priority is priority
        assert source.is_completed is False
        assert source.text == "مهمة متراكمة"


def test_changing_a_rolled_over_task_does_not_change_history(db_connection):
    """Day A shows HIGH forever, even after Day B's copy becomes LOW."""
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)
    rollover = DailyRolloverService(
        conn=db_connection, day_repo=day_repo, task_repo=task_repo
    )
    history = HistoryService(day_repo=day_repo, task_repo=task_repo)

    day_a = day_repo.get_or_create("2026-09-25")
    task_a = service.create_task(day_a.id, "مهمة تاريخية", priority=TaskPriority.HIGH)

    rollover.rollover_tasks(source_date="2026-09-25", target_date="2026-09-26")

    tasks_b = service.get_today_tasks(day_repo.get_by_date("2026-09-26").id)
    task_b = tasks_b[0]
    assert task_b.priority is TaskPriority.HIGH

    # The user changes the Day B copy to LOW through the context menu.
    service.update_task_priority(task_b.id, TaskPriority.LOW)

    # History for Day A must still report HIGH.
    day_a_history = history.get_day_history("2026-09-25")
    assert len(day_a_history.tasks) == 1
    assert day_a_history.tasks[0].priority is TaskPriority.HIGH
    assert day_a_history.tasks[0].id == task_a.id

    # And Day B now reports LOW.
    day_b_history = history.get_day_history("2026-09-26")
    assert day_b_history.tasks[0].priority is TaskPriority.LOW


def test_completed_tasks_keep_their_priority(db_connection):
    """MEDIUM -> HIGH -> complete and HIGH -> LOW -> complete both persist."""
    repo = TaskRepository(db_connection)
    service = TaskService(repo)
    day = DayRepository(db_connection).create("2026-09-27")

    task = service.create_task(day.id, "مهمة", priority=TaskPriority.MEDIUM)
    service.update_task_priority(task.id, TaskPriority.HIGH)
    service.toggle_task_completion(task.id, True)

    stored = repo.get_by_id(task.id)
    assert stored is not None
    assert stored.is_completed is True
    assert stored.priority is TaskPriority.HIGH

    # Priority of a completed task can still be changed.
    service.update_task_priority(task.id, TaskPriority.LOW)
    stored = repo.get_by_id(task.id)
    assert stored is not None
    assert stored.is_completed is True
    assert stored.priority is TaskPriority.LOW


# ===========================================================================
# 6. RTL
# ===========================================================================
def test_priority_selector_is_right_to_left():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.priority_selector import PrioritySelector

    selector = PrioritySelector()

    assert selector.layoutDirection() == Qt.LayoutDirection.RightToLeft


def test_edit_dialog_is_right_to_left_and_carries_both_values():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_edit_dialog import TaskEditDialog

    dialog = TaskEditDialog(initial_text="نص", initial_priority=TaskPriority.LOW)

    assert dialog.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert dialog.get_text() == "نص"
    assert dialog.get_priority() is TaskPriority.LOW


def test_context_menu_priority_submenu_is_right_to_left():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_item import TaskItem

    item = TaskItem(_make_task(priority=TaskPriority.MEDIUM))
    menu = _trigger_context_menu(item)
    priority_menu = next(a.menu() for a in menu.actions() if a.menu() is not None)

    assert menu.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert priority_menu.layoutDirection() == Qt.LayoutDirection.RightToLeft


# ===========================================================================
# 7. Backward compatibility
# ===========================================================================
def test_existing_medium_tasks_stay_medium(db_connection):
    """An old database row without an explicit priority reads back as MEDIUM."""
    conn = db_connection
    conn.execute(
        "INSERT INTO days (id, date, created_at, updated_at) VALUES "
        "(1, '2026-09-01', '2026-09-01T00:00:00', '2026-09-01T00:00:00')"
    )
    conn.execute(
        "INSERT INTO tasks (id, day_id, text, is_completed, position, created_at, updated_at) "
        "VALUES (1, 1, 'مهمة قديمة', 0, 0, '2026-09-01T00:00:00', '2026-09-01T00:00:00')"
    )
    conn.commit()

    repo = TaskRepository(conn)
    task = repo.get_by_id(1)

    assert task is not None
    assert task.priority is TaskPriority.MEDIUM


def test_priority_enum_has_no_extra_or_missing_members():
    assert [p.name for p in TaskPriority] == ["LOW", "MEDIUM", "HIGH"]


# ===========================================================================
# 8. MainWindow integration -- the real UI flow
# ===========================================================================
class _FakeGeometryManager:
    def __init__(self, geometry=(60, 60, 380, 560)):
        self._geometry = geometry
        self.saved = []

    def get_validated_geometry(self):
        return self._geometry

    def save_geometry(self, x, y, width, height):
        self.saved.append((x, y, width, height))


def _make_window(task_service, day_id=1):
    from unittest.mock import MagicMock

    from app.ui.windows.main_window import MainWindow

    day = Day(id=day_id, date="2026-09-27", quote_text="اقتباس",
              created_at="now", updated_at="now")
    window = MainWindow(
        day=day,
        quote_text=day.quote_text,
        task_service=task_service,
        geometry_manager=_FakeGeometryManager(),
        on_exit_requested=MagicMock(),
    )
    window.resize(380, 560)
    return window


def test_submitting_a_task_uses_the_selected_priority(db_connection):
    if _skip_without_qt():
        return
    _qt_app()

    repo = TaskRepository(db_connection)
    service = TaskService(repo)
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    for priority in (TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW):
        window._priority_selector.set_priority(priority)
        window._on_task_submitted("اتصل بالعميل")

    tasks = service.get_today_tasks(day.id)
    assert [t.priority for t in tasks] == [
        TaskPriority.HIGH,
        TaskPriority.MEDIUM,
        TaskPriority.LOW,
    ]
    assert all(t.text == "اتصل بالعميل" for t in tasks)
    window.close()


def test_selector_resets_to_medium_after_a_successful_submission(db_connection):
    if _skip_without_qt():
        return
    _qt_app()

    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    window._priority_selector.set_priority(TaskPriority.HIGH)
    window._on_task_submitted("مهمة عاجلة")

    assert window._priority_selector.selected_priority() is TaskPriority.MEDIUM
    window.close()


def test_selector_is_not_reset_when_submission_fails(db_connection):
    """Blank text must not silently reset the user's priority choice."""
    if _skip_without_qt():
        return
    _qt_app()

    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    window._priority_selector.set_priority(TaskPriority.HIGH)
    window._on_task_submitted("   ")

    assert service.get_today_tasks(day.id) == []
    assert window._priority_selector.selected_priority() is TaskPriority.HIGH
    window.close()


def test_context_menu_priority_change_updates_record_and_row(db_connection):
    if _skip_without_qt():
        return
    _qt_app()

    repo = TaskRepository(db_connection)
    service = TaskService(repo)
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    task = service.create_task(day.id, "مهمة", priority=TaskPriority.HIGH)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    assert window._task_list._items[task.id].priority is TaskPriority.HIGH

    # Exactly the signal the TaskItem emits from its context menu.
    window._on_task_priority_change_requested(task.id, TaskPriority.LOW)

    stored = repo.get_by_id(task.id)
    assert stored is not None
    assert stored.priority is TaskPriority.LOW
    assert stored.id == task.id
    assert stored.text == "مهمة"
    assert window._task_list._items[task.id].priority is TaskPriority.LOW
    window.close()


def _install_fake_edit_dialog(new_text, new_priority):
    """Make the edit dialog return fixed values instead of showing itself."""
    import app.ui.widgets.task_edit_dialog as dialog_module

    class _FakeDialog:
        last_initial_priority = None

        def __init__(self, initial_text="", initial_priority=None, parent=None):
            self.initial_text = initial_text
            self.initial_priority = initial_priority
            _FakeDialog.last_initial_priority = initial_priority

        def exec(self):
            return 1

        def get_text(self):
            return new_text

        def get_priority(self):
            return new_priority

    return _patched(dialog_module, "TaskEditDialog", _FakeDialog)


def test_edit_flow_changing_only_text_preserves_priority(db_connection):
    if _skip_without_qt():
        return
    _qt_app()

    repo = TaskRepository(db_connection)
    service = TaskService(repo)
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    task = service.create_task(day.id, "نص أصلي", priority=TaskPriority.HIGH)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    with _install_fake_edit_dialog("نص معدل", TaskPriority.HIGH):
        window._on_task_edit_requested(task.id)

    stored = repo.get_by_id(task.id)
    assert stored.text == "نص معدل"
    assert stored.priority is TaskPriority.HIGH
    window.close()


def test_edit_flow_changing_only_priority_preserves_text(db_connection):
    if _skip_without_qt():
        return
    _qt_app()

    repo = TaskRepository(db_connection)
    service = TaskService(repo)
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    task = service.create_task(day.id, "نص أصلي", priority=TaskPriority.MEDIUM)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    with _install_fake_edit_dialog("نص أصلي", TaskPriority.LOW):
        window._on_task_edit_requested(task.id)

    stored = repo.get_by_id(task.id)
    assert stored.text == "نص أصلي"
    assert stored.priority is TaskPriority.LOW
    window.close()


def test_edit_flow_changing_both_persists_both(db_connection):
    if _skip_without_qt():
        return
    _qt_app()

    repo = TaskRepository(db_connection)
    service = TaskService(repo)
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    task = service.create_task(day.id, "نص أصلي", priority=TaskPriority.MEDIUM)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    with _install_fake_edit_dialog("نص معدل", TaskPriority.HIGH):
        window._on_task_edit_requested(task.id)

    stored = repo.get_by_id(task.id)
    assert stored.text == "نص معدل"
    assert stored.priority is TaskPriority.HIGH
    assert window._task_list._items[task.id].priority is TaskPriority.HIGH
    window.close()


def test_edit_dialog_receives_the_current_priority(db_connection):
    """The dialog must open on the task's real priority, not on a default."""
    if _skip_without_qt():
        return
    _qt_app()

    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    task = service.create_task(day.id, "نص", priority=TaskPriority.LOW)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    with _install_fake_edit_dialog("نص", TaskPriority.LOW) as fake:
        window._on_task_edit_requested(task.id)
        assert fake.last_initial_priority is TaskPriority.LOW
    window.close()


def test_new_task_row_contains_the_priority_selector(db_connection):
    if _skip_without_qt():
        return
    _qt_app()

    service = TaskService(TaskRepository(db_connection))
    day = DayRepository(db_connection).create("2026-09-27")
    window = _make_window(service, day.id)

    assert window._priority_selector is not None
    assert window._priority_selector.parent() is not None
    # The selector and the text field share one row, so they cannot drift apart.
    assert window._priority_selector.parent() is window._task_input.parent()
    window.close()
