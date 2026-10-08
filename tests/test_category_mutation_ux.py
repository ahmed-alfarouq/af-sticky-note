"""Phase 7B: category mutation UX end to end (creation, edit, context menu).

Qt tests no-op (rather than fail) when PySide6 is unavailable, following the
project's UI-test convention.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtWidgets import QApplication, QMenu

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


@contextmanager
def _patched(module, name, value):
    original = getattr(module, name)
    setattr(module, name, value)
    try:
        yield value
    finally:
        setattr(module, name, original)


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
    day_repo = DayRepository(db_connection)
    return task_repo, service, category_service, provider, day_repo


def _make_window(service, category_service, provider, day):
    from app.ui.windows.main_window import MainWindow

    window = MainWindow(
        day=day,
        quote_text=day.quote_text,
        task_service=service,
        on_exit_requested=MagicMock(),
        category_service=category_service,
        icon_provider=provider,
    )
    window.resize(380, 560)
    return window


def _trigger_context_menu(item):
    """Build the item's context menu without showing it (recording exec)."""
    import app.ui.widgets.task_item as task_item_module

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


def _category_submenu(menu):
    for action in menu.actions():
        submenu = action.menu()
        if submenu is not None and action.text() == "الفئة":
            return submenu
    return None


# ------------------------------------------------------------ creation

def test_creating_a_task_persists_the_selected_category(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    window = _make_window(service, category_service, provider, day)

    window._category_selector.set_category("work")
    window._on_task_submitted("مهمة عمل")

    tasks = service.get_today_tasks(day.id)
    assert len(tasks) == 1
    assert tasks[0].category_id == "work"
    window.close()


def test_creating_with_default_selector_persists_general(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    window = _make_window(service, category_service, provider, day)

    assert window._category_selector.selected_category_id() == "general"
    window._on_task_submitted("مهمة عامة")
    assert service.get_today_tasks(day.id)[0].category_id == "general"
    window.close()


def test_successful_submission_resets_category_to_default(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    window = _make_window(service, category_service, provider, day)

    window._category_selector.set_category("life")
    window._on_task_submitted("مهمة")
    assert window._category_selector.selected_category_id() == "general"
    window.close()


def test_failed_submission_preserves_selected_category(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    window = _make_window(service, category_service, provider, day)

    window._category_selector.set_category("religion")
    window._on_task_submitted("   ")  # blank -> rejected, no task created
    assert service.get_today_tasks(day.id) == []
    assert window._category_selector.selected_category_id() == "religion"
    window.close()


# ------------------------------------------------------------ edit dialog

def _install_fake_edit_dialog(new_text, new_category_id, with_choices=True):
    import app.ui.widgets.task_edit_dialog as dialog_module
    from app.core.models import TaskPriority

    class _FakeDialog:
        seen_initial_category = None

        def __init__(self, initial_text="", initial_priority=None, parent=None,
                     initial_category_id="general", categories=(), icon_provider=None):
            self.initial_text = initial_text
            self.initial_priority = initial_priority
            _FakeDialog.seen_initial_category = initial_category_id
            self._categories = categories

        def exec(self):
            return 1

        def get_text(self):
            return new_text

        def get_priority(self):
            return TaskPriority.MEDIUM

        def get_category_id(self):
            return new_category_id

        def has_category_choices(self):
            return with_choices and len(self._categories) > 0

    return _patched(dialog_module, "TaskEditDialog", _FakeDialog)


def test_edit_dialog_loads_current_category(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    task = service.create_task(day.id, "مهمة", category_id="work")
    assert task is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    with _install_fake_edit_dialog("مهمة", "work") as fake:
        window._on_task_edit_requested(task.id)
    assert fake.seen_initial_category == "work"
    window.close()


def test_edit_flow_category_only_update(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    task = service.create_task(day.id, "نص ثابت", category_id="general")
    assert task is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    with _install_fake_edit_dialog("نص ثابت", "life"):
        window._on_task_edit_requested(task.id)

    stored = task_repo.get_by_id(task.id)
    assert stored is not None
    assert stored.category_id == "life"
    assert stored.text == "نص ثابت"
    assert stored.id == task.id
    assert stored.is_completed == task.is_completed
    assert stored.position == task.position
    assert stored.source_task_id == task.source_task_id
    assert window._task_list._items[task.id].category_id == "life"
    window.close()


def test_edit_flow_text_and_category_update(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    task = service.create_task(day.id, "قديم", category_id="general")
    assert task is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    with _install_fake_edit_dialog("جديد", "religion"):
        window._on_task_edit_requested(task.id)

    stored = task_repo.get_by_id(task.id)
    assert stored is not None
    assert (stored.text, stored.category_id) == ("جديد", "religion")
    window.close()


def test_edit_flow_without_choices_never_downgrades_category(db_connection):
    """The has_category_choices guard: a dialog that offered nothing must not
    rewrite a real category back to the default."""
    if _skip_without_qt():
        return
    _qt_app()
    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    task = service.create_task(day.id, "مهمة", category_id="work")
    assert task is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    with _install_fake_edit_dialog("مهمة", "general", with_choices=False):
        window._on_task_edit_requested(task.id)

    assert task_repo.get_by_id(task.id).category_id == "work"
    window.close()


def test_real_dialog_cancel_preserves_everything(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_edit_dialog import TaskEditDialog

    task_repo, service, _, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    task = service.create_task(day.id, "الأصل", category_id="life")
    assert task is not None

    from app.core.services.category_service import CategoryService
    from app.database.category_repository import CategoryRepository

    categories = CategoryService(CategoryRepository(db_connection)).list_active_categories()
    dialog = TaskEditDialog(
        initial_text="الأصل",
        initial_category_id="life",
        categories=categories,
        icon_provider=provider,
    )
    assert dialog.get_category_id() == "life"
    assert dialog.has_category_choices()
    dialog.reject()
    assert dialog.result() == 0
    assert task_repo.get_by_id(task.id).category_id == "life"


def test_real_dialog_loads_and_returns_category(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.services.category_service import CategoryService
    from app.database.category_repository import CategoryRepository
    from app.ui.widgets.task_edit_dialog import TaskEditDialog

    _, _, _, provider, _ = _wiring(db_connection)
    categories = CategoryService(CategoryRepository(db_connection)).list_active_categories()
    dialog = TaskEditDialog(
        initial_text="نص",
        initial_category_id="religion",
        categories=categories,
        icon_provider=provider,
    )
    assert dialog.get_category_id() == "religion"
    assert dialog._category_selector.itemText(dialog._category_selector.currentIndex()) == "دين"


# ------------------------------------------------------------ context menu

def test_context_menu_shows_category_submenu_with_current_checked(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import Task
    from app.core.services.category_service import CategoryService
    from app.database.category_repository import CategoryRepository
    from app.ui.widgets.task_item import TaskItem

    categories = CategoryService(CategoryRepository(db_connection)).list_active_categories()
    _, _, _, provider, _ = _wiring(db_connection)
    item = TaskItem(Task(id=1, day_id=1, text="م", is_completed=False, position=0,
                         created_at="t", updated_at="t", category_id="work"),
                    categories=categories, icon_provider=provider)
    menu = _trigger_context_menu(item)
    submenu = _category_submenu(menu)
    assert submenu is not None
    assert [a.text() for a in submenu.actions()] == ["دين", "عمل", "حياة", "عام"]
    assert [a.text() for a in submenu.actions() if a.isChecked()] == ["عمل"]
    item.close()


def test_context_menu_without_categories_has_no_category_submenu():
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import Task
    from app.ui.widgets.task_item import TaskItem

    item = TaskItem(Task(id=1, day_id=1, text="م", is_completed=False, position=0,
                         created_at="t", updated_at="t"))
    menu = _trigger_context_menu(item)
    assert _category_submenu(menu) is None
    item.close()


def test_context_menu_category_change_updates_in_place(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    task_repo, service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    task = service.create_task(day.id, "مهمة", category_id="general")
    assert task is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    window._on_task_category_change_requested(task.id, "work")

    stored = task_repo.get_by_id(task.id)
    assert stored is not None
    assert stored.category_id == "work"
    assert stored.id == task.id
    assert stored.day_id == task.day_id
    assert stored.text == task.text
    assert stored.is_completed == task.is_completed
    assert stored.position == task.position
    assert stored.priority == task.priority
    assert stored.source_task_id == task.source_task_id
    assert window._task_list._items[task.id].category_id == "work"
    window.close()
