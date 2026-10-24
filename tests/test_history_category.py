"""Phase 7I: historical category indicators in the History window.

The History window is strictly read-only: each historical task row shows the
category recorded on that day (shared cached icon + Arabic name tooltip,
mirroring live TaskItem rows) without querying per row or mutating anything.
Qt tests no-op when PySide6 is unavailable.
"""
from __future__ import annotations

from pathlib import Path

import pytest

try:  # pragma: no cover - environment dependent
    from PySide6.QtWidgets import QApplication, QLabel

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


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
    history_service = HistoryService(day_repo=DayRepository(db_connection), task_repo=task_repo)
    provider = CategoryIconProvider(Path(__file__).resolve().parent.parent / "assets" / "icons")
    return service, category_service, history_service, provider, category_repo


def _make_window(history_service, date, categories=(), provider=None):
    from app.ui.windows.history_window import HistoryWindow

    return HistoryWindow(
        history_service=history_service,
        initial_date=date,
        categories=categories,
        icon_provider=provider,
    )


def _row_icon(row):
    return row.findChild(QLabel, "taskCategoryIcon")


def _snapshot(db_connection):
    tasks = db_connection.execute(
        "SELECT id, day_id, text, is_completed, category_id FROM tasks ORDER BY id"
    ).fetchall()
    categories = db_connection.execute(
        "SELECT id, name_ar, icon_key, sort_order, is_active FROM categories ORDER BY id"
    ).fetchall()
    return (
        [(r["id"], r["day_id"], r["text"], r["is_completed"], r["category_id"]) for r in tasks],
        [(r["id"], r["name_ar"], r["icon_key"], r["sort_order"], r["is_active"]) for r in categories],
    )


def test_known_category_shows_arabic_name_and_icon(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, history_service, provider, _ = _wiring(db_connection)
    from app.database.day_repository import DayRepository

    day_repo = DayRepository(db_connection)
    day = day_repo.create("2026-09-20")
    service.create_task(day.id, "مهمة عمل", category_id="work")

    window = _make_window(
        history_service, "2026-09-20", category_service.list_active_categories(), provider
    )
    icons = window._task_container.findChildren(QLabel, "taskCategoryIcon")
    assert len(icons) == 1
    assert icons[0].toolTip() == "عمل"
    assert not icons[0].pixmap().isNull()


def test_inactive_category_remains_identifiable(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, _, history_service, provider, category_repo = _wiring(db_connection)
    from app.database.day_repository import DayRepository

    day_repo = DayRepository(db_connection)
    day = day_repo.create("2026-09-20")
    service.create_task(day.id, "مهمة حياة", category_id="life")
    category_repo.set_active("life", False)

    # Full metadata (including inactive) keeps the Arabic name visible.
    window = _make_window(history_service, "2026-09-20", category_repo.list_all(), provider)
    icons = window._task_container.findChildren(QLabel, "taskCategoryIcon")
    assert len(icons) == 1
    assert icons[0].toolTip() == "حياة"
    assert not icons[0].pixmap().isNull()


def test_unknown_category_falls_back_safely(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import Task, TaskPriority

    _, category_service, history_service, provider, _ = _wiring(db_connection)
    window = _make_window(
        history_service, "2026-09-20", category_service.list_active_categories(), provider
    )
    ghost = Task(
        id=999, day_id=1, text="شبح", is_completed=False, position=0,
        created_at="t", updated_at="t", priority=TaskPriority.MEDIUM,
        category_id="no-such-category",
    )
    row = window._create_read_only_task_row(ghost)
    icon = _row_icon(row)
    assert icon is not None
    assert icon.toolTip() == "no-such-category"
    # Drawn fallback icon, never a crash or an empty hole.
    assert not icon.pixmap().isNull()


def test_missing_icon_asset_uses_fallback_without_crashing(db_connection, tmp_path):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.category_icons import CategoryIconProvider

    _, category_service, history_service, _, _ = _wiring(db_connection)
    empty_dir = tmp_path / "no-icons"
    empty_dir.mkdir()
    provider = CategoryIconProvider(empty_dir)
    window = _make_window(
        history_service, "2026-09-20", category_service.list_active_categories(), provider
    )
    from app.core.models import Task, TaskPriority

    task = Task(
        id=1, day_id=1, text="نص", is_completed=False, position=0,
        created_at="t", updated_at="t", priority=TaskPriority.HIGH,
        category_id="work",
    )
    row = window._create_read_only_task_row(task)
    icon = _row_icon(row)
    assert icon.toolTip() == "عمل"
    assert not icon.pixmap().isNull()


def test_rendering_does_not_modify_historical_records(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, history_service, provider, _ = _wiring(db_connection)
    from app.core.models import TaskPriority
    from app.database.day_repository import DayRepository

    day_repo = DayRepository(db_connection)
    day = day_repo.create("2026-09-20")
    t1 = service.create_task(day.id, "أولى", priority=TaskPriority.HIGH, category_id="work")
    t2 = service.create_task(day.id, "ثانية", category_id="religion")
    service.toggle_task_completion(t2.id, True)

    before = _snapshot(db_connection)
    window = _make_window(
        history_service, "2026-09-20", category_service.list_active_categories(), provider
    )
    window._on_next_day()
    window._load_day_view("2026-09-20")
    after = _snapshot(db_connection)

    assert before == after
    assert [t[0] for t in after[0]] == [t1.id, t2.id]
    assert {t[4] for t in after[0]} == {"work", "religion"}
    assert {t[3] for t in after[0]} == {0, 1}


def test_production_wiring_shows_inactive_category_in_history(db_connection, monkeypatch):
    """End-to-end through the production metadata path: MainWindow loads the
    full category list once, and the History dialog it opens identifies a
    task recorded under a since-deactivated category -- while the creation
    selector stays active-only."""
    if _skip_without_qt():
        return
    _qt_app()
    from unittest.mock import MagicMock

    from app.database.day_repository import DayRepository

    service, category_service, history_service, provider, category_repo = _wiring(db_connection)
    day_repo = DayRepository(db_connection)
    day = day_repo.create("2026-09-20")
    service.create_task(day.id, "مهمة حياة", category_id="life")
    category_repo.set_active("life", False)

    # Production loading path: MainWindow.__init__ reads both lists once.
    from app.ui.windows.main_window import MainWindow

    main_window = MainWindow(
        day=day_repo.get_by_date("2026-09-20"),
        quote_text="حكمة",
        task_service=service,
        initial_tasks=service.get_today_tasks(day.id),
        history_service=history_service,
        on_exit_requested=MagicMock(),
        category_service=category_service,
        icon_provider=provider,
    )
    assert "life" not in main_window._category_selector.category_ids()

    captured = {}

    class _Capture:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def exec(self):
            return 0

    import app.ui.windows.history_window as history_module
    from app.ui.windows.history_window import HistoryWindow as RealHistoryWindow

    monkeypatch.setattr(history_module, "HistoryWindow", _Capture)
    main_window._on_history_requested()

    assert [c.id for c in captured["categories"]] == [
        "general", "work", "personal", "study", "health", "home", "religion", "life",
    ]
    assert captured["icon_provider"] is provider

    # The captured production kwargs render the inactive Arabic name.
    window = RealHistoryWindow(
        history_service=history_service,
        initial_date="2026-09-20",
        categories=captured["categories"],
        icon_provider=captured["icon_provider"],
    )
    icons = window._task_container.findChildren(QLabel, "taskCategoryIcon")
    assert len(icons) == 1
    assert icons[0].toolTip() == "حياة"


def test_existing_row_fields_stay_intact(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.windows.history_window import HistoryWindow

    service, category_service, history_service, provider, _ = _wiring(db_connection)
    from app.core.models import TaskPriority
    from app.database.day_repository import DayRepository

    day_repo = DayRepository(db_connection)
    day = day_repo.create("2026-09-20")
    service.create_task(day.id, "عاجلة", priority=TaskPriority.HIGH, category_id="work")
    service.create_task(day.id, "عادية", category_id="general")

    window = _make_window(
        history_service, "2026-09-20", category_service.list_active_categories(), provider
    )
    assert isinstance(window, HistoryWindow)
    assert window._date_title_label.text() == "2026-09-20"
    assert "2" in window._stats_label.text()

    rows = window._task_container.findChildren(QLabel, "taskCategoryIcon")
    assert len(rows) == 2
    # Category names never leak into visible row text (icon-only convention).
    visible = window._task_container.findChildren(QLabel)
    assert not any("عمل" == label.text() or "عام" == label.text() for label in visible)
    # Priority badge behavior unchanged: exactly one HIGH badge.
    assert len(window._task_container.findChildren(QLabel, "priorityBadgeHigh")) == 1
