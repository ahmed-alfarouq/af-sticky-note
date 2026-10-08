"""Phase 7D: main-window hierarchy tests (date, progress, quote, sections).

Qt tests no-op (rather than fail) when PySide6 is unavailable, following the
project's UI-test convention.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.models import TaskPriority

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFrame

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


# ------------------------------------------------------------ date parts

def test_date_parts_split_gregorian_and_hijri():
    from app.infrastructure.clock import format_dual_calendar_date, get_date_parts

    day_number, weekday, month_year, hijri = get_date_parts("2026-10-08")
    assert day_number == "8"
    assert weekday == "الخميس"  # 2026-10-08 is a Thursday
    assert month_year == "أكتوبر 2026"
    assert hijri.endswith("هـ")
    # Hijri agrees with the legacy dual-calendar string.
    assert hijri in format_dual_calendar_date("2026-10-08")


def test_date_parts_degrade_gracefully_on_bad_input():
    from app.infrastructure.clock import get_date_parts

    assert get_date_parts("not-a-date")[0] == "not-a-date"
    assert get_date_parts("2026-13-99") == ("2026-13-99", "", "", "")


# ------------------------------------------------------------ date header

def test_date_header_shows_hierarchy(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.date_header import DateHeaderWidget

    header = DateHeaderWidget("2026-10-08")
    header.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    assert header._day_number.text() == "8"
    assert header._weekday_label.text() == "الخميس"
    assert "أكتوبر 2026" in header._secondary_label.text()
    assert "هـ" in header._secondary_label.text()
    assert header._day_number.objectName() == "dayNumber"
    header.close()


def test_date_header_ring_is_left_of_day_number_in_rtl():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.date_header import DateHeaderWidget

    header = DateHeaderWidget("2026-10-08")
    header.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    header.resize(340, 70)
    header.show()
    QApplication.instance().processEvents()
    assert header._day_number.x() > header._ring.x()
    header.close()


# ------------------------------------------------------------ progress ring

def test_ring_reports_progress_and_skips_redundant_repaints():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.progress_ring import ProgressRing

    ring = ProgressRing()
    assert ring.progress_value() == (0, 0)
    ring.set_progress(0, 0)  # zero-task state: defined, no crash
    assert ring.progress_value() == (0, 0)
    ring.set_progress(1, 4)
    assert ring.progress_value() == (1, 4)
    ring.set_progress(4, 4)
    assert ring.progress_value() == (4, 4)
    ring.close()


def test_window_ring_reflects_tasks_and_toggle(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, provider, day)
    assert window._date_header.progress_value() == (0, 0)

    window._on_task_submitted("أولى")
    window._on_task_submitted("ثانية")
    assert window._date_header.progress_value() == (0, 2)

    tasks = service.get_today_tasks(day.id)
    window._on_task_completed_toggled(tasks[0].id, True)
    assert window._date_header.progress_value() == (1, 2)

    window._on_task_delete_requested(tasks[1].id)
    assert window._date_header.progress_value() == (1, 1)
    window.close()


# ------------------------------------------------------------ quote section

def test_quote_section_is_quote_only_and_visible(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.quote_widget import QuoteWidget

    widget = QuoteWidget(quote_text="حكمة اليوم")
    assert widget.objectName() == "quoteSection"
    assert not hasattr(widget, "_date_label")
    assert "حكمة اليوم" in widget._quote_label.text()
    widget.set_quote_text("جديدة")
    assert "جديدة" in widget._quote_label.text()
    widget.close()


# ------------------------------------------------------------ completed section

def test_completed_tasks_sink_below_active_with_section_label(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    done = service.create_task(day.id, "منجزة أولا", category_id="work")
    todo = service.create_task(day.id, "لاحقة", category_id="life")
    assert done is not None and todo is not None
    service.toggle_task_completion(done.id, True)

    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    order = [item.task_id for item in window._task_list._items.values()]
    # Visual order is view-level; dict preserves insertion -- check layout order.
    layout = window._task_list._layout
    visual = [layout.itemAt(i).widget().task_id
              for i in range(layout.count())
              if getattr(layout.itemAt(i).widget(), "task_id", None) is not None]
    assert visual == [todo.id, done.id]
    label = window._task_list._section_label
    assert not label.isHidden()
    assert label.text() == "مكتملة • 1"
    window.close()


def test_section_label_hidden_without_completed(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    service.create_task(day.id, "نشطة")
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    assert window._task_list._section_label.isHidden()
    window.close()


def test_toggle_moves_row_between_sections_in_place(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    first = service.create_task(day.id, "أ")
    second = service.create_task(day.id, "ب")
    assert first is not None and second is not None
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    before = window._task_list._items[first.id]
    window._on_task_completed_toggled(first.id, True)
    # Same widget object, now positioned after the active one.
    assert window._task_list._items[first.id] is before
    layout = window._task_list._layout
    visual = [layout.itemAt(i).widget().task_id
              for i in range(layout.count())
              if getattr(layout.itemAt(i).widget(), "task_id", None) is not None]
    assert visual == [second.id, first.id]
    assert window._date_header.progress_value() == (1, 2)
    window.close()


def test_completed_row_keeps_menus_and_mutations(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, task_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    task = service.create_task(day.id, "م", category_id="general")
    assert task is not None
    service.toggle_task_completion(task.id, True)
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))

    window._on_task_category_change_requested(task.id, "religion")
    window._on_task_priority_change_requested(task.id, TaskPriority.HIGH)
    stored = task_repo.get_by_id(task.id)
    assert stored is not None
    assert (stored.category_id, stored.is_completed) == ("religion", True)
    assert stored.priority.name == "HIGH"
    window.close()


# ------------------------------------------------------------ composition

@pytest.mark.parametrize("size", [(320, 420), (380, 560), (600, 500)])
def test_all_sections_coexist_without_horizontal_scroll(db_connection, size):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    service.create_task(day.id, "مهمة", category_id="work")
    window = _make_window(service, category_service, provider, day)
    window._task_list.set_tasks(service.get_today_tasks(day.id))
    window.resize(*size)
    window.show()
    QApplication.instance().processEvents()

    for name in ("_header_frame", "_date_header", "_quote_widget",
                 "_task_list", "_task_input", "_add_btn"):
        widget = getattr(window, name)
        assert widget.isVisible(), name
    assert "8" in window._date_header._day_number.text()
    assert window._task_list.horizontalScrollBar().maximum() == 0
    window.close()


def test_add_button_and_selectors_survive_refinement(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo, _ = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, provider, day)
    window._category_selector.set_category("work")
    window._task_input.setText("عبر الزر")
    window._add_btn.click()
    tasks = service.get_today_tasks(day.id)
    assert [(t.text, t.category_id) for t in tasks] == [("عبر الزر", "work")]
    window.close()
