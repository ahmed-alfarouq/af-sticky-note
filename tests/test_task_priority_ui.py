"""Phase 6A — priority controls in the sticky-note UI.

Skipped automatically when PySide6 is not installed.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QLineEdit, QToolButton

from app.core.models import Day, Task, TaskPriority
from app.core.services.history_service import HistoryService
from app.core.services.task_service import TaskService
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository
from app.ui.priority_presentation import PRIORITY_LABELS_AR
from app.ui.widgets.task_edit_dialog import TaskEditDialog
from app.ui.widgets.task_input import TaskInput
from app.ui.widgets.task_item import TaskItem
from app.ui.windows.history_window import HistoryWindow
from app.ui.windows.main_window import MainWindow


def test_task_row_text_is_rtl_and_checkbox_is_physical_right(qapp):
    item = TaskItem(_sample_task(TaskPriority.HIGH, text="مهمة تجريبية"))
    assert item.layoutDirection() == Qt.LayoutDirection.LeftToRight
    assert item._text_label.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert item._text_label.alignment() == (
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    )

    item.resize(360, 56)
    item.show()
    qapp.processEvents()
    text_rect = item._text_label.geometry()
    box_rect = item._checkbox.geometry()
    badge = item._priority_badge
    assert box_rect.center().x() > text_rect.center().x()
    assert badge.isHidden() is False
    assert badge.geometry().right() <= text_rect.left() + 2
    assert text_rect.right() <= box_rect.left() + 2
    item.close()


def test_long_task_text_wraps_across_the_row_not_into_a_column(qapp):
    text = "هذا نص عربي طويل يجب أن يلتف بعرض البطاقة ويبقى الشارة ملاصقة للنص"
    item = TaskItem(_sample_task(TaskPriority.HIGH, text=text))
    item.resize(360, 120)
    item.show()
    qapp.processEvents()
    assert item._text_label.width() > 160
    assert item._priority_badge.geometry().right() <= item._text_label.geometry().left() + 4
    assert item._checkbox.geometry().center().x() > item._text_label.geometry().center().x()
    item.close()


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _sample_task(priority: TaskPriority, text: str = "مهمة", task_id: int = 1) -> Task:
    return Task(
        id=task_id,
        day_id=1,
        text=text,
        is_completed=False,
        position=0,
        created_at="2026-09-27T00:00:00+00:00",
        updated_at="2026-09-27T00:00:00+00:00",
        priority=priority,
    )


def _open_window(qapp, db_connection, tasks=()):
    day_repo = DayRepository(db_connection)
    day = day_repo.get_or_create("2026-09-27")
    service = TaskService(TaskRepository(db_connection))
    window = MainWindow(
        day=day,
        quote_text="اقتباس",
        task_service=service,
        initial_tasks=tasks,
    )
    return window, service, day


def _priority_menu(item: TaskItem):
    menu = item._create_context_menu()
    for action in menu.actions():
        if action.menu() is not None and action.text() == "الأولوية":
            return menu, action.menu()
    raise AssertionError("priority submenu missing")


def _action_by_text(menu, text: str):
    for action in menu.actions():
        if action.text() == text:
            return action
    raise AssertionError(f"action {text!r} missing")


def _visible_badges(root):
    """Badges the widget itself has not hidden.

    ``isVisible()`` is false whenever an ancestor window is hidden, which is
    the normal state in offscreen tests that never call ``show()``.
    """
    found = []
    for name in ("priorityBadgeHigh", "priorityBadgeLow"):
        for label in root.findChildren(QLabel, name):
            if not label.isHidden() and label.text():
                found.append(label.text())
    return found


def test_new_task_selector_defaults_to_medium_and_submits_choice(qapp):
    row = TaskInput()
    assert row.priority() == TaskPriority.MEDIUM
    # Physical placement is explicit. Text direction lives on the field.
    assert row.layoutDirection() == Qt.LayoutDirection.LeftToRight

    selector = row.findChild(QToolButton, "taskPriorityButton")
    edit = row.findChild(QLineEdit, "taskInputField")
    assert selector is not None and edit is not None
    assert selector.text().startswith(PRIORITY_LABELS_AR[TaskPriority.MEDIUM])
    assert edit.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert edit.alignment() == (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    row.resize(420, 48)
    row.show()
    qapp.processEvents()
    # Typing field is the primary control on the physical right.
    assert edit.geometry().x() > selector.geometry().x()

    captured = []
    row.task_submitted.connect(lambda text, priority: captured.append((text, priority)))

    row.setText("مهمة عاجلة")
    row.set_priority(TaskPriority.HIGH)
    edit.returnPressed.emit()
    assert captured == [("مهمة عاجلة", TaskPriority.HIGH.value)]

    row.set_priority(TaskPriority.LOW)
    row.setText("مهمة منخفضة")
    edit.returnPressed.emit()
    assert captured[-1] == ("مهمة منخفضة", TaskPriority.LOW.value)
    row.close()


def test_create_task_persists_selected_priority_and_shows_badge(qapp, db_connection):
    window, service, day = _open_window(qapp, db_connection)
    window._task_input.setText("عاجلة")
    window._task_input.set_priority(TaskPriority.HIGH)
    window._task_input._on_return_pressed()

    tasks = service.get_today_tasks(day.id)
    assert len(tasks) == 1
    assert tasks[0].priority == TaskPriority.HIGH
    assert tasks[0].text == "عاجلة"
    assert window._task_input.text() == ""
    assert window._task_input.priority() == TaskPriority.MEDIUM
    assert _visible_badges(window) == ["عاجل"]

    window._task_input.setText("منخفضة")
    window._task_input.set_priority(TaskPriority.LOW)
    window._on_task_submitted(window._task_input.text(), window._task_input.priority().value)
    tasks = service.get_today_tasks(day.id)
    assert [task.priority for task in tasks] == [TaskPriority.HIGH, TaskPriority.LOW]
    assert _visible_badges(window) == ["عاجل", "منخفض"]

    window._task_input.setText("عادية")
    window._on_task_submitted("عادية", TaskPriority.MEDIUM.value)
    medium = service.get_today_tasks(day.id)[-1]
    assert medium.priority == TaskPriority.MEDIUM
    item_badge = window._task_list._items[medium.id].findChild(QLabel, "priorityBadgeMedium")
    assert item_badge is not None
    assert item_badge.isHidden() is True
    window.close()


def test_failed_create_keeps_text_and_selected_priority(qapp, db_connection):
    window, service, day = _open_window(qapp, db_connection)
    window._task_input.setText("   ")
    window._task_input.set_priority(TaskPriority.HIGH)
    window._on_task_submitted("   ", TaskPriority.HIGH.value)
    assert service.get_today_tasks(day.id) == []
    assert window._task_input.text() == "   "
    assert window._task_input.priority() == TaskPriority.HIGH
    window.close()


def test_edit_dialog_loads_current_priority_and_rejects_blank_text(qapp):
    dialog = TaskEditDialog("مهمة عاجلة", TaskPriority.HIGH)
    assert dialog.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert dialog.get_text() == "مهمة عاجلة"
    assert dialog.get_priority() == TaskPriority.HIGH
    assert dialog.findChild(QToolButton, "taskPriorityButton").text().startswith("عاجل")
    assert dialog._input_field.alignment() == (
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    )

    dialog._input_field.setText("   ")
    dialog.accept()
    assert dialog.result() != QDialog.DialogCode.Accepted

    dialog._input_field.setText("نص محدّث")
    dialog._priority_selector.set_priority(TaskPriority.LOW)
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.get_text() == "نص محدّث"
    assert dialog.get_priority() == TaskPriority.LOW
    dialog.close()


def test_edit_dialog_preselects_low_and_medium(qapp):
    low = TaskEditDialog("منخفضة", TaskPriority.LOW)
    medium = TaskEditDialog("عادية", TaskPriority.MEDIUM)
    assert low.get_priority() == TaskPriority.LOW
    assert low.findChild(QToolButton, "taskPriorityButton").text().startswith("منخفض")
    assert medium.get_priority() == TaskPriority.MEDIUM
    assert medium.findChild(QToolButton, "taskPriorityButton").text().startswith("عادي")
    low.close()
    medium.close()


def test_apply_edit_persists_text_and_priority_and_cancel_does_not(qapp, db_connection):
    window, service, day = _open_window(qapp, db_connection)
    created = service.create_task(day.id, "قبل التعديل", priority=TaskPriority.HIGH)
    window._task_list.add_task(created)
    before = TaskRepository(db_connection).get_by_id(created.id)

    class RejectingDialog:
        def __init__(self, initial_text, initial_priority=TaskPriority.MEDIUM, parent=None):
            self.initial_text = initial_text
            self.initial_priority = initial_priority

        def exec(self):
            return QDialog.DialogCode.Rejected

        def get_text(self):
            raise AssertionError("cancel must not read a new value")

        def get_priority(self):
            raise AssertionError("cancel must not read a new priority")

    original = __import__(
        "app.ui.widgets.task_edit_dialog", fromlist=["TaskEditDialog"]
    ).TaskEditDialog
    import app.ui.widgets.task_edit_dialog as dialog_module

    dialog_module.TaskEditDialog = RejectingDialog
    try:
        window._on_task_edit_requested(created.id)
    finally:
        dialog_module.TaskEditDialog = original

    assert TaskRepository(db_connection).get_by_id(created.id) == before
    assert window._task_list.task_text(created.id) == "قبل التعديل"
    assert window._task_list.task_priority(created.id) == TaskPriority.HIGH

    assert window._apply_task_edit(created.id, "   ", TaskPriority.LOW) is False
    assert TaskRepository(db_connection).get_by_id(created.id).priority == TaskPriority.HIGH
    assert window._task_list.task_priority(created.id) == TaskPriority.HIGH

    assert window._apply_task_edit(created.id, "بعد التعديل", TaskPriority.LOW) is True
    stored = TaskRepository(db_connection).get_by_id(created.id)
    assert stored.text == "بعد التعديل"
    assert stored.priority == TaskPriority.LOW
    assert stored.id == created.id
    assert stored.day_id == day.id
    assert window._task_list.task_text(created.id) == "بعد التعديل"
    assert window._task_list.task_priority(created.id) == TaskPriority.LOW
    assert _visible_badges(window._task_list._items[created.id]) == ["منخفض"]
    window.close()


def test_context_menu_priority_actions_update_without_changing_text(qapp, db_connection):
    window, service, day = _open_window(qapp, db_connection)
    created = service.create_task(day.id, "قائمة سياقية", priority=TaskPriority.MEDIUM)
    window._task_list.add_task(created)
    item = window._task_list._items[created.id]

    menu, priority_menu = _priority_menu(item)
    labels = [action.text() for action in priority_menu.actions() if action.text()]
    assert labels == ["عاجل", "عادي", "منخفض"]
    assert _action_by_text(menu, "تعديل المهمة") is not None
    assert _action_by_text(menu, "حذف المهمة") is not None
    assert _action_by_text(priority_menu, "عادي").isChecked() is True
    assert _action_by_text(priority_menu, "عاجل").isChecked() is False

    before = TaskRepository(db_connection).get_by_id(created.id)
    _action_by_text(priority_menu, "عادي").trigger()
    unchanged = TaskRepository(db_connection).get_by_id(created.id)
    assert unchanged.updated_at == before.updated_at
    assert unchanged.priority == TaskPriority.MEDIUM

    _action_by_text(priority_menu, "عاجل").trigger()
    high = TaskRepository(db_connection).get_by_id(created.id)
    assert high.priority == TaskPriority.HIGH
    assert high.text == "قائمة سياقية"
    assert high.id == created.id
    assert high.day_id == day.id
    assert item.priority() == TaskPriority.HIGH
    assert _visible_badges(item) == ["عاجل"]

    menu2, priority_menu2 = _priority_menu(item)
    assert _action_by_text(priority_menu2, "عاجل").isChecked() is True
    _action_by_text(priority_menu2, "منخفض").trigger()
    low = TaskRepository(db_connection).get_by_id(created.id)
    assert low.priority == TaskPriority.LOW
    assert low.text == "قائمة سياقية"
    assert item.priority() == TaskPriority.LOW
    assert _visible_badges(item) == ["منخفض"]

    menu3, priority_menu3 = _priority_menu(item)
    _action_by_text(priority_menu3, "عادي").trigger()
    medium = TaskRepository(db_connection).get_by_id(created.id)
    assert medium.priority == TaskPriority.MEDIUM
    assert medium.text == "قائمة سياقية"
    assert item.findChild(QLabel, "priorityBadgeMedium").isHidden() is True
    menu.deleteLater()
    menu2.deleteLater()
    menu3.deleteLater()
    window.close()


def test_initial_high_task_shows_badge_immediately(qapp, db_connection):
    task = _sample_task(TaskPriority.HIGH, text="ظاهرة", task_id=7)
    # Persist so the row matches a real task, then show it as the initial list.
    day_repo = DayRepository(db_connection)
    day = day_repo.get_or_create("2026-09-27")
    service = TaskService(TaskRepository(db_connection))
    created = service.create_task(day.id, "ظاهرة", priority=TaskPriority.HIGH)
    window, _, _ = _open_window(qapp, db_connection, tasks=[created])
    assert _visible_badges(window) == ["عاجل"]
    assert window._task_list.task_priority(created.id) == TaskPriority.HIGH
    window.close()
    assert task.priority == TaskPriority.HIGH


def test_history_window_shows_historical_priority_badges(qapp, db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    service = TaskService(task_repo)
    history = HistoryService(day_repo=day_repo, task_repo=task_repo)

    day_a = day_repo.get_or_create("2026-09-25")
    day_b = day_repo.get_or_create("2026-09-26")
    service.create_task(day_a.id, "تاريخ عاجل", priority=TaskPriority.HIGH)
    service.create_task(day_b.id, "تاريخ منخفض", priority=TaskPriority.LOW)
    service.create_task(day_b.id, "تاريخ عادي", priority=TaskPriority.MEDIUM)

    def current_badges():
        found = []
        layout = window._task_layout
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is not None:
                found.extend(_visible_badges(widget))
        return found

    window = HistoryWindow(history_service=history, initial_date="2026-09-25")
    assert window.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert current_badges() == ["عاجل"]

    window._btn_next.click()
    qapp.processEvents()
    assert window._current_date == "2026-09-26"
    assert current_badges() == ["منخفض"]
    # MEDIUM stays unbadged, matching the live list.
    medium_hidden = False
    layout = window._task_layout
    for index in range(layout.count()):
        widget = layout.itemAt(index).widget()
        if widget is None:
            continue
        for badge in widget.findChildren(QLabel, "priorityBadgeMedium"):
            assert badge.isHidden() is True
            medium_hidden = True
    assert medium_hidden is True
    window.close()


def test_priority_controls_do_not_move_exit_button(qapp, db_connection):
    previous = qapp.layoutDirection()
    qapp.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    window, _, _ = _open_window(qapp, db_connection)
    window.resize(380, 560)
    window.show()
    qapp.processEvents()
    try:
        header_layout = window._header_frame.layout()
        assert header_layout.itemAt(0).widget() is window._exit_btn
        assert window._exit_btn.text() == "✕"
        assert window._header_frame.layoutDirection() == Qt.LayoutDirection.LeftToRight
        exit_x = window._exit_btn.mapTo(window, window._exit_btn.rect().center()).x()
        pin_x = window._pin_widget.mapTo(window, window._pin_widget.rect().center()).x()
        assert exit_x < window.width() / 3
        assert exit_x < pin_x
    finally:
        qapp.setLayoutDirection(previous)
        window.close()
