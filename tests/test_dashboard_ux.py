"""Phase 7F: weekly dashboard window tests.

Qt tests no-op (rather than fail) when PySide6 is unavailable, following the
project's UI-test convention. Reporting semantics themselves stay covered by
tests/test_weekly_reports.py; here the dashboard's presentation, presets,
validation, lifecycle, and packaging are verified.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


def _wired_service(db_connection):
    from app.core.services.report_service import ReportService
    from app.core.services.task_service import TaskService
    from app.database.category_repository import CategoryRepository
    from app.database.day_repository import DayRepository
    from app.database.report_repository import ReportRepository
    from app.database.task_repository import TaskRepository

    task_service = TaskService(TaskRepository(db_connection), CategoryRepository(db_connection))
    report_service = ReportService(ReportRepository(db_connection), CategoryRepository(db_connection))
    return task_service, report_service, DayRepository(db_connection)


def _provider():
    from app.ui.category_icons import CategoryIconProvider

    return CategoryIconProvider(Path(__file__).resolve().parent.parent / "assets" / "icons")


def _seed_week(db_connection):
    task_service, _, day_repo = _wired_service(db_connection)
    plan = {
        "2026-10-05": [("a1", "work", True), ("a2", "work", False)],
        "2026-10-07": [("b1", "life", True)],
        "2026-10-09": [("c1", "religion", False)],
    }
    for day_iso, tasks in plan.items():
        day = day_repo.get_or_create(day_iso)
        for text, category, done in tasks:
            task = task_service.create_task(day.id, text, category_id=category)
            assert task is not None
            if done:
                task_service.toggle_task_completion(task.id, True)


def _make_dashboard(db_connection, **kwargs):
    from app.ui.windows.dashboard_window import WeeklyDashboardWindow

    _, report_service, _ = _wired_service(db_connection)
    kwargs.setdefault("icon_provider", _provider())
    return WeeklyDashboardWindow(report_service=report_service, **kwargs)


# ------------------------------------------------------------ presets (Qt-free)

def test_preset_ranges_end_today():
    from app.ui.windows.dashboard_window import (
        PRESET_LAST_7,
        PRESET_LAST_14,
        PRESET_THIS_WEEK,
        preset_range,
    )

    today = date(2026, 10, 9)  # a Friday
    assert preset_range(PRESET_THIS_WEEK, today) == ("2026-10-05", "2026-10-09")
    assert preset_range(PRESET_LAST_7, today) == ("2026-10-03", "2026-10-09")
    assert preset_range(PRESET_LAST_14, today) == ("2026-09-26", "2026-10-09")
    monday = date(2026, 10, 5)
    assert preset_range(PRESET_THIS_WEEK, monday) == ("2026-10-05", "2026-10-05")
    sunday = date(2026, 10, 11)
    assert preset_range(PRESET_THIS_WEEK, sunday) == ("2026-10-05", "2026-10-11")


def test_unknown_preset_rejected():
    from app.ui.windows.dashboard_window import preset_range

    with pytest.raises(ValueError):
        preset_range("nope", date(2026, 10, 9))


# ------------------------------------------------------------ construction/content

def test_dashboard_opens_with_last7_and_shows_totals(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _seed_week(db_connection)
    dialog = _make_dashboard(db_connection)
    try:
        assert dialog.windowTitle() == "لوحة التقارير الأسبوعية"
        assert dialog.layoutDirection() == Qt.LayoutDirection.RightToLeft
        start, end = dialog.current_range()
        # Default preset is last-7-days ending today (whatever today is).
        assert end == date.today().isoformat()
        assert (date.fromisoformat(end) - date.fromisoformat(start)).days == 6
        assert dialog.load_count() == 1
        # Fixed range over the seeded week: 4 tasks, 2 completed -> 50%.
        from PySide6.QtCore import QDate

        dialog._start_edit.setDate(QDate(2026, 10, 5))
        dialog._end_edit.setDate(QDate(2026, 10, 11))
        dialog._apply_btn.click()
        assert dialog._stat_values["total"].text() == "4"
        assert dialog._stat_values["completed"].text() == "2"
        assert dialog._stat_values["incomplete"].text() == "2"
        assert dialog._stat_values["percent"].text() == "50٪"
        assert dialog.load_count() == 2
    finally:
        dialog.close()


def test_dashboard_custom_range_and_validation(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _seed_week(db_connection)
    dialog = _make_dashboard(db_connection)
    try:
        from PySide6.QtCore import QDate

        dialog._start_edit.setDate(QDate(2026, 10, 7))
        dialog._end_edit.setDate(QDate(2026, 10, 7))
        dialog._apply_btn.click()
        assert dialog.current_range() == ("2026-10-07", "2026-10-07")
        assert dialog._stat_values["total"].text() == "1"
        assert dialog._error_label.isHidden()  # no error shown
        assert dialog.load_count() == 2

        # Invalid range: friendly error, previous content preserved.
        dialog._start_edit.setDate(QDate(2026, 10, 9))
        dialog._end_edit.setDate(QDate(2026, 10, 5))
        dialog._apply_btn.click()
        assert not dialog._error_label.isHidden()
        assert "غير صالح" in dialog._error_label.text()
        assert dialog.current_range() == ("2026-10-07", "2026-10-07")
        assert dialog.load_count() == 2
    finally:
        dialog.close()


def test_dashboard_zero_task_range_shows_empty_state(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    dialog = _make_dashboard(db_connection)
    try:
        from PySide6.QtCore import QDate

        dialog._start_edit.setDate(QDate(2025, 1, 1))
        dialog._end_edit.setDate(QDate(2025, 1, 7))
        dialog._apply_btn.click()
        assert dialog._stat_values["total"].text() == "0"
        assert dialog._stat_values["percent"].text() == "0٪"
        assert not dialog._empty_label.isHidden()
        assert len(dialog._chart.chart_data()) == 7
        assert all(row.total == 0 for row in dialog._chart.chart_data())
    finally:
        dialog.close()


def test_dashboard_category_cards_order_icons_and_history(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.database.category_repository import CategoryRepository

    _seed_week(db_connection)
    CategoryRepository(db_connection).set_active("life", False)
    dialog = _make_dashboard(db_connection)
    try:
        from PySide6.QtCore import QDate

        dialog._start_edit.setDate(QDate(2026, 10, 5))
        dialog._end_edit.setDate(QDate(2026, 10, 11))
        dialog._apply_btn.click()
        cards = dialog.category_cards()
        assert [c.category_id() for c in cards] == ["religion", "work", "life", "general"]
        by_id = {c.category_id(): c for c in cards}
        assert by_id["work"]._stats_label.text() == "مكتملة 1 من 2 • 50٪"
        # Inactive historical category stays visible with stored metadata.
        assert by_id["life"]._name_label.text() == "حياة"
        assert not by_id["life"]._icon_label.pixmap().isNull()
        assert by_id["general"]._stats_label.text() == "مكتملة 0 من 0 • 0٪"
    finally:
        dialog.close()


def test_dashboard_chart_data_chronological_and_valued(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _seed_week(db_connection)
    dialog = _make_dashboard(db_connection)
    try:
        from PySide6.QtCore import QDate

        dialog._start_edit.setDate(QDate(2026, 10, 5))
        dialog._end_edit.setDate(QDate(2026, 10, 18))  # 14 days
        dialog._apply_btn.click()
        data = dialog._chart.chart_data()
        assert len(data) == 14
        assert [row.date for row in data] == sorted(row.date for row in data)
        assert data[0].date == "2026-10-05" and data[-1].date == "2026-10-18"
        by_date = {row.date: row for row in data}
        assert (by_date["2026-10-05"].total, by_date["2026-10-05"].completed) == (2, 1)
        assert by_date["2026-10-06"].total == 0
        # Paint path survives a 30-day range too.
        dialog._start_edit.setDate(QDate(2026, 9, 20))
        dialog._end_edit.setDate(QDate(2026, 10, 19))
        dialog._apply_btn.click()
        assert len(dialog._chart.chart_data()) == 30
        pixmap = dialog._chart.grab()
        assert not pixmap.isNull()
    finally:
        dialog.close()


def test_dashboard_preset_switch_reloads_once_each(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _seed_week(db_connection)
    dialog = _make_dashboard(db_connection)
    try:
        assert dialog.load_count() == 1
        dialog._preset_buttons["last14"].click()
        assert dialog.load_count() == 2
        start, end = dialog.current_range()
        assert end == date.today().isoformat()
        assert (date.fromisoformat(end) - date.fromisoformat(start)).days == 13
    finally:
        dialog.close()


def test_dashboard_rejects_without_crashing_on_service_failure(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.windows.dashboard_window import WeeklyDashboardWindow

    class _FailingService:
        def get_range_report(self, start, end):
            raise RuntimeError("disk gone")

    dialog = WeeklyDashboardWindow(report_service=_FailingService(), parent=None)  # type: ignore
    try:
        assert not dialog._error_label.isHidden()
        assert "تعذر" in dialog._error_label.text()
    finally:
        dialog.close()


def test_dashboard_close_keeps_main_window_alive(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import Day

    task_service, report_service, day_repo = _wired_service(db_connection)
    from app.ui.windows.main_window import MainWindow

    day = Day(id=1, date="2026-10-09", quote_text="q", created_at="t", updated_at="t")
    window = MainWindow(
        day=day, quote_text="q", task_service=task_service,
        on_exit_requested=MagicMock(), report_service=report_service,
        icon_provider=_provider(),
    )
    dashboard = None
    try:
        from app.ui.windows.dashboard_window import WeeklyDashboardWindow

        dashboard = WeeklyDashboardWindow(
            report_service=report_service, icon_provider=_provider(), parent=window)
        dashboard.reject()  # close without accepting
        assert dashboard.result() == 0
        assert not window._allow_window_close  # exit path untouched
        assert task_service.get_today_tasks(1) == []
    finally:
        if dashboard is not None:
            dashboard.close()
        window.close()


def test_task_list_menu_offers_dashboard(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    import app.ui.widgets.task_list as task_list_module
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtWidgets import QMenu
    from app.ui.widgets.task_list import TaskList

    captured = []

    class _RecordingMenu(QMenu):
        def exec(self, *args, **kwargs):  # noqa: N802 - Qt naming
            captured.append(self)
            return None

    original = task_list_module.QMenu
    task_list_module.QMenu = _RecordingMenu
    try:
        listing = TaskList()
        event = QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse,
            listing.mapToGlobal(listing.rect().center()),
            listing.mapToGlobal(listing.rect().center()),
            Qt.KeyboardModifier.NoModifier,
        )
        listing.contextMenuEvent(event)
    finally:
        task_list_module.QMenu = original
    assert captured
    assert "لوحة التقارير الأسبوعية" in [a.text() for a in captured[0].actions()]
    listing.close()


# ------------------------------------------------------------ Gate B: tooltips

def test_chart_bar_tooltips_carry_date_and_counts(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _seed_week(db_connection)
    dialog = _make_dashboard(db_connection)
    try:
        from PySide6.QtCore import QDate

        dialog._start_edit.setDate(QDate(2026, 10, 5))
        dialog._end_edit.setDate(QDate(2026, 10, 11))
        dialog._apply_btn.click()
        chart = dialog._chart
        assert chart.bar_tooltip(0) == "2026-10-05 • مكتملة 1 من 2 • 50٪"
        assert chart.bar_tooltip(1) == "2026-10-06 • مكتملة 0 من 0 • 0٪"
        assert chart.bar_tooltip(99) == ""
        assert chart.bar_tooltip(-1) == ""
    finally:
        dialog.close()


def test_chart_mouse_move_resolves_bar_without_queries(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.daily_reports import DailyReport

    dialog = _make_dashboard(db_connection)
    try:
        rows = [DailyReport(f"2026-10-{day:02d}", 2, 1, 1, 50) for day in range(1, 8)]
        dialog._chart.set_data(rows)
        dialog._chart.resize(350, 140)
        # First slot maps to the first day, last slot to the last day.
        assert dialog._chart._index_at_x(10.0) == 0
        assert dialog._chart._index_at_x(340.0) == 6
        dialog._chart.setToolTip(dialog._chart.bar_tooltip(dialog._chart._index_at_x(10.0)))
        assert dialog._chart.toolTip().startswith("2026-10-01")
    finally:
        dialog.close()


# ------------------------------------------------------------ Gate B: preset persistence

def _ini_settings(tmp_path, name="dash.ini"):
    from PySide6.QtCore import QSettings

    return QSettings(str(tmp_path / name), QSettings.Format.IniFormat)


def test_preset_choice_persists_and_restores(db_connection, tmp_path):
    if _skip_without_qt():
        return
    _qt_app()
    _seed_week(db_connection)

    first = _make_dashboard(db_connection, qsettings=_ini_settings(tmp_path))
    try:
        first._preset_buttons["last14"].click()
        assert first.load_count() == 2
    finally:
        first.close()

    second = _make_dashboard(db_connection, qsettings=_ini_settings(tmp_path))
    try:
        # Restored without an explicit click; single load from persisted state.
        assert second._preset_buttons["last14"].isChecked()
        start, end = second.current_range()
        assert (date.fromisoformat(end) - date.fromisoformat(start)).days == 13
    finally:
        second.close()


def test_custom_range_persists_and_restores(db_connection, tmp_path):
    if _skip_without_qt():
        return
    _qt_app()
    _seed_week(db_connection)
    from PySide6.QtCore import QDate

    first = _make_dashboard(db_connection, qsettings=_ini_settings(tmp_path))
    try:
        first._start_edit.setDate(QDate(2026, 10, 5))
        first._end_edit.setDate(QDate(2026, 10, 7))
        first._apply_btn.click()
        assert first.current_range() == ("2026-10-05", "2026-10-07")
    finally:
        first.close()

    second = _make_dashboard(db_connection, qsettings=_ini_settings(tmp_path))
    try:
        assert second.current_range() == ("2026-10-05", "2026-10-07")
        assert not any(b.isChecked() for b in second._preset_buttons.values())
    finally:
        second.close()


def test_invalid_persisted_state_falls_back_to_default(db_connection, tmp_path):
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.windows.dashboard_window import DASHBOARD_SETTINGS_GROUP

    settings = _ini_settings(tmp_path)
    settings.beginGroup(DASHBOARD_SETTINGS_GROUP)
    settings.setValue("preset", "nope")
    settings.setValue("start", "garbage")
    settings.setValue("end", "also-garbage")
    settings.endGroup()
    settings.sync()

    dialog = _make_dashboard(db_connection, qsettings=_ini_settings(tmp_path))
    try:
        assert dialog._preset_buttons["last7"].isChecked()
        start, end = dialog.current_range()
        assert (date.fromisoformat(end) - date.fromisoformat(start)).days == 6
    finally:
        dialog.close()


def test_no_settings_means_no_persistence_but_same_default(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    dialog = _make_dashboard(db_connection)
    try:
        assert dialog._preset_buttons["last7"].isChecked()
        assert dialog.load_count() == 1
    finally:
        dialog.close()


# ------------------------------------------------------------ Gate C: lifecycle

def test_repeated_open_close_cycles_stay_clean(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    _seed_week(db_connection)
    for _ in range(3):
        dialog = _make_dashboard(db_connection)
        try:
            from PySide6.QtCore import QDate

            dialog._start_edit.setDate(QDate(2026, 10, 5))
            dialog._end_edit.setDate(QDate(2026, 10, 11))
            dialog._apply_btn.click()
            assert dialog.load_count() == 2
            assert len(dialog.category_cards()) == 4
        finally:
            dialog.close()
            dialog.deleteLater()
    QApplication.instance().processEvents()


# ------------------------------------------------------------ packaging

def test_spec_covers_dashboard_and_reporting_modules():
    from pathlib import Path as _Path

    spec = (_Path(__file__).resolve().parent.parent / "packaging" / "DailySticky.spec"
            ).read_text(encoding="utf-8")
    for module in (
        "app.core.daily_reports",
        "app.core.services.report_service",
        "app.database.report_repository",
        "app.ui.windows.dashboard_window",
        "app.ui.widgets.daily_chart",
        "app.ui.widgets.category_card",
    ):
        assert module in spec, f"{module} missing from spec hiddenimports"
    assert "assets/icons" in spec
