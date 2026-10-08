"""Phase 7C: task-row + input-dock visual redesign tests.

Covers the reference hierarchy ``[completion] [expanding text]
[category icon] [priority dot]`` (RTL), icon-only metadata (no row text
for category/priority), in-place mutation visuals, completed quiet state,
minimum-size/resize validity, the long-text/language matrix, and the
bottom input dock. Qt tests no-op when PySide6 is unavailable.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFrame, QSizePolicy

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
    return service, category_service, provider, DayRepository(db_connection), task_repo


def _make_task(category_id="general", priority=None, text="مهمة", is_completed=False):
    from app.core.models import Task, TaskPriority

    return Task(
        id=1, day_id=1, text=text, is_completed=is_completed, position=0,
        created_at="t", updated_at="t",
        priority=priority or TaskPriority.MEDIUM, category_id=category_id,
    )


def _make_item(task, categories=(), provider=None):
    from app.ui.widgets.task_item import TaskItem

    item = TaskItem(task, categories=categories, icon_provider=provider)
    item.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    return item


def _categories(db_connection):
    from app.core.services.category_service import CategoryService
    from app.database.category_repository import CategoryRepository

    return CategoryService(CategoryRepository(db_connection)).list_active_categories()


# ------------------------------------------------------------ row structure

def test_row_has_icon_and_dot_metadata_in_rtl_order(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, _, provider, _, _ = _wiring(db_connection)
    item = _make_item(_make_task(), _categories(db_connection), provider)
    item.resize(340, 60)
    item.show()
    QApplication.instance().processEvents()

    assert item._checkbox.isVisible()
    assert item._category_icon.isVisible()
    assert item._priority_dot.isVisible()
    # Fixed metadata boxes: identical footprint for every row.
    assert (item._category_icon.width(), item._category_icon.height()) == (22, 22)
    assert (item._priority_dot.width(), item._priority_dot.height()) == (12, 12)
    # Text owns the flexible space.
    assert item._text_label.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    # RTL: checkbox rightmost, then text, then category icon, then dot.
    assert item._checkbox.x() > item._category_icon.x() > item._priority_dot.x()
    item.close()


def test_row_shows_no_category_or_priority_text(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority

    _, _, provider, _, _ = _wiring(db_connection)
    categories = _categories(db_connection)
    for category in categories:
        for priority in TaskPriority:
            item = _make_item(
                _make_task(category_id=category.id, priority=priority),
                categories, provider,
            )
            row_texts = [item._text_label.text(), item._priority_dot.text()]
            assert category.name_ar not in row_texts
            assert item._priority_dot.text() == ""
            item.close()


def test_row_shows_every_category_icon_with_name_tooltip(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, _, provider, _, _ = _wiring(db_connection)
    categories = _categories(db_connection)
    assert [c.id for c in categories] == ["religion", "work", "life", "general"]
    expected_names = {"religion": "دين", "work": "عمل", "life": "حياة", "general": "عام"}
    for category in categories:
        item = _make_item(_make_task(category_id=category.id), categories, provider)
        assert not item._category_icon.pixmap().isNull()
        assert item._category_icon.toolTip() == expected_names[category.id]
        item.close()


def test_row_dot_level_and_tooltip_per_priority():
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority

    expected = {
        TaskPriority.HIGH: ("priorityDotHigh", "عاجل"),
        TaskPriority.MEDIUM: ("priorityDotMedium", "عادي"),
        TaskPriority.LOW: ("priorityDotLow", "منخفض"),
    }
    for priority, (name, arabic) in expected.items():
        item = _make_item(_make_task(priority=priority))
        assert item._priority_dot.objectName() == name
        assert arabic in item._priority_dot.toolTip()
        item.close()


def test_category_mutation_updates_icon_in_place(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, _, provider, _, _ = _wiring(db_connection)
    categories = _categories(db_connection)
    item = _make_item(_make_task(category_id="general"), categories, provider)
    before = item._category_icon.pixmap().toImage()
    item.update_task_category("work")
    assert item.category_id == "work"
    assert item._category_icon.toolTip() == "عمل"
    assert not item._category_icon.pixmap().isNull()
    assert item._category_icon.pixmap().toImage() != before
    item.close()


def test_priority_mutation_updates_dot_in_place():
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority

    item = _make_item(_make_task())
    item.update_task_priority(TaskPriority.HIGH)
    assert item._priority_dot.objectName() == "priorityDotHigh"
    item.update_task_priority(TaskPriority.LOW)
    assert item._priority_dot.objectName() == "priorityDotLow"
    item.close()


def test_completed_row_is_quiet_but_metadata_survives(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority

    _, _, provider, _, _ = _wiring(db_connection)
    item = _make_item(
        _make_task(category_id="work", priority=TaskPriority.HIGH),
        _categories(db_connection), provider,
    )
    item.set_completed_silently(True)
    assert item._text_label.objectName() == "taskTextLabelCompleted"
    assert item._priority_dot.objectName() == "priorityDotHigh"
    assert item._priority_dot.property("completed") is True
    assert not item._category_icon.pixmap().isNull()
    assert item._category_icon.toolTip() == "عمل"
    item.close()


# ------------------------------------------------------------ language matrix

LANGUAGE_CASES = [
    "مهمة قصيرة",
    "مهمة عربية طويلة جدا تحتاج إلى أكثر من سطر واحد لعرضها بالكامل داخل الصف",
    "Short task",
    "A long English task that needs more than one line to display fully inside the row",
    "مهمة mixed مختلطة task",
    "مهمة رقم 123",
    "Task 456",
    "https://example.com/a/very/long/path/that/does/not/break/anywhere/at/all",
]


@pytest.mark.parametrize("text", LANGUAGE_CASES)
def test_language_matrix_rows_stay_valid(db_connection, text):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority

    _, _, provider, _, _ = _wiring(db_connection)
    categories = _categories(db_connection)
    for priority in TaskPriority:
        for category in ("general", "work"):
            item = _make_item(
                _make_task(category_id=category, priority=priority, text=text),
                categories, provider,
            )
            item.resize(340, 80)
            item.show()
            QApplication.instance().processEvents()
            assert item._text_label.wordWrap()
            assert not item._category_icon.pixmap().isNull()
            assert item._priority_dot.objectName() in (
                "priorityDotHigh", "priorityDotMedium", "priorityDotLow")
            # Metadata never overlaps: fixed boxes stay disjoint.
            assert not item._category_icon.geometry().intersects(
                item._priority_dot.geometry())
            item.close()


# ------------------------------------------------------------ input dock

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
    return window


def test_input_dock_contains_all_controls(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    window = _make_window(service, category_service, provider, day)

    dock = window.findChild(QFrame, "taskInputDock")
    assert dock is not None
    assert window._priority_selector is not None
    assert window._category_selector is not None
    assert window._task_input is not None
    assert window._add_btn is not None
    assert window._add_btn.text() == "+"
    # Selector distinction: dock shows icon+name / priority names.
    assert window._category_selector.itemText(
        window._category_selector.currentIndex()) == "عام"
    window.close()


def test_add_button_submits_through_creation_path(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    window = _make_window(service, category_service, provider, day)

    window._category_selector.set_category("life")
    window._task_input.setText("مهمة الزر")
    window._add_btn.click()

    tasks = service.get_today_tasks(day.id)
    assert len(tasks) == 1
    assert (tasks[0].text, tasks[0].category_id) == ("مهمة الزر", "life")
    assert window._category_selector.selected_category_id() == "general"
    window.close()


def test_minimum_size_layout_has_no_metadata_overlap(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    service.create_task(day.id, "مهمة عند أصغر حجم مع نص أطول قليلا", category_id="work")
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    window.resize(320, 420)
    window.show()
    QApplication.instance().processEvents()

    assert window._add_btn.isVisible()
    assert window._task_input.isVisible()
    item = window._task_list._items[next(iter(window._task_list._items))]
    assert not item._category_icon.geometry().intersects(item._priority_dot.geometry())
    assert window._task_list.horizontalScrollBar().maximum() == 0
    window.close()


def test_wider_window_gives_text_more_space(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    service.create_task(day.id, "نص", category_id="general")
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    window.resize(320, 420)
    window.show()
    QApplication.instance().processEvents()
    item = window._task_list._items[next(iter(window._task_list._items))]
    narrow = item._text_label.width()

    window.resize(600, 500)
    QApplication.instance().processEvents()
    assert item._text_label.width() > narrow
    window.close()


# ------------------------------------------------------------ 7C.1: unbreakable text

UNBREAKABLE_CASES = [
    "https://example.com/a/very/long/path/that/does/not/break/anywhere/at/all",
    "C:\\Users\\someone\\Documents\\projects\\daily-sticky\\assets\\icons\\religion.png",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "مهمة-متصلة-بشرطات-طويلة-جدا-بدون-مسافات-على-الإطلاق-في-النص",
]


def test_display_transform_is_identity_for_normal_text():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_item import to_display_text

    for text in ("مهمة قصيرة", "Short task", "Task 456", "مهمة رقم 123", ""):
        assert to_display_text(text) == text


def test_display_transform_adds_breaks_only_where_needed():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_item import from_display_text, to_display_text

    for text in UNBREAKABLE_CASES:
        display = to_display_text(text)
        assert "\u200b" in display  # zero-width space present
        assert from_display_text(display) == text  # stored text recoverable


def test_task_text_property_never_leaks_break_characters(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _, _, provider, _, _ = _wiring(db_connection)
    raw = UNBREAKABLE_CASES[0]
    item = _make_item(_make_task(text=raw), _categories(db_connection), provider)
    assert item.task_text == raw
    assert "\u200b" not in item.task_text
    assert item._text_label.toolTip() == raw
    item.close()


@pytest.mark.parametrize("text", UNBREAKABLE_CASES)
# Narrow widths force wrapping; at 600px short segments legitimately fit on
# one line (covered structurally by the window scrollbar test instead).
@pytest.mark.parametrize("width", [320, 380])
def test_unbreakable_tokens_wrap_without_metadata_overlap(db_connection, text, width):
    if _skip_without_qt():
        return
    _qt_app()
    _, _, provider, _, _ = _wiring(db_connection)
    item = _make_item(_make_task(text=text), _categories(db_connection), provider)
    item.resize(width - 20, 80)
    item.show()
    QApplication.instance().processEvents()
    # The token must wrap (multi-line label) instead of clipping past the
    # edge: its height-for-width exceeds a single-line row at the same width.
    probe = _make_item(_make_task(text="نص"))
    probe.resize(width - 20, 80)
    probe.show()
    QApplication.instance().processEvents()
    label_width = item._text_label.width()
    assert item._text_label.heightForWidth(label_width) > probe._text_label.heightForWidth(
        label_width
    )
    # The label itself stays bounded and metadata stays disjoint/visible.
    assert item._text_label.width() <= item.width()
    assert not item._category_icon.geometry().intersects(item._priority_dot.geometry())
    assert not item._category_icon.pixmap().isNull()
    probe.close()
    item.close()


def test_unbreakable_token_in_window_has_no_horizontal_scroll(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-09-27")
    service.create_task(day.id, UNBREAKABLE_CASES[0], category_id="work")
    service.create_task(day.id, UNBREAKABLE_CASES[2], category_id="religion")
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    for size in ((320, 420), (380, 560), (600, 500)):
        window.resize(*size)
        window.show()
        QApplication.instance().processEvents()
        assert window._task_list.horizontalScrollBar().maximum() == 0
        for item in window._task_list._items.values():
            assert item._category_icon.isVisible()
            assert item._priority_dot.isVisible()
            assert item._checkbox.isVisible()
    window.close()
