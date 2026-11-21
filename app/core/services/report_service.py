"""Read-only weekly/range reporting service (Phase 7E).

Qt-free orchestration over aggregate repository queries: validates the
range, runs a bounded number of SELECTs (two aggregates + one category
lookup, independent of days/categories), and assembles the immutable
:class:`DateRangeReport` the future Dashboard will consume.

Historical rules honored: tasks count on their stored day (rollover copies
are independent rows, never merged); inactive categories with historical
tasks remain fully reportable; unrecorded days appear with zeros.
"""
from __future__ import annotations

from typing import Dict, List

from app.core.daily_reports import (
    CategoryReport,
    DailyReport,
    DateRangeReport,
    completion_percent,
    enumerate_dates,
    validate_range,
)
from app.core.models import Category
from app.database.category_repository import CategoryRepository
from app.database.report_repository import ReportRepository


class ReportService:
    def __init__(
        self,
        report_repo: ReportRepository,
        category_repo: CategoryRepository,
    ) -> None:
        self._report_repo = report_repo
        self._category_repo = category_repo

    def get_range_report(self, start_date: str, end_date: str) -> DateRangeReport:
        """Build the aggregate report for the inclusive range."""
        start, end = validate_range(start_date, end_date)
        start_iso, end_iso = start.isoformat(), end.isoformat()

        by_category = self._report_repo.totals_by_category(start_iso, end_iso)
        by_day = self._report_repo.totals_by_day(start_iso, end_iso)
        known = {category.id: category for category in self._category_repo.list_all()}

        daily_reports = tuple(self._daily_reports(start, end, by_day))
        category_reports = tuple(self._category_reports(by_category, known))

        total = sum(entry.total for entry in daily_reports)
        completed = sum(entry.completed for entry in daily_reports)
        return DateRangeReport(
            start_date=start_iso,
            end_date=end_iso,
            total_tasks=total,
            completed_tasks=completed,
            incomplete_tasks=total - completed,
            completion_percentage=completion_percent(completed, total),
            category_reports=category_reports,
            daily_reports=daily_reports,
        )

    @staticmethod
    def _daily_reports(start, end, by_day) -> List[DailyReport]:
        recorded: Dict[str, tuple] = {day: (total, done) for day, total, done in by_day}
        reports = []
        for iso in enumerate_dates(start, end):
            total, done = recorded.get(iso, (0, 0))
            reports.append(
                DailyReport(
                    date=iso,
                    total=total,
                    completed=done,
                    incomplete=total - done,
                    completion_percentage=completion_percent(done, total),
                )
            )
        return reports

    @staticmethod
    def _category_reports(by_category, known: Dict[str, Category]) -> List[CategoryReport]:
        """One row per known category (zeros when unused in range), in
        ``sort_order`` -- plus any referenced-but-unknown id defensively."""
        counted: Dict[str, tuple] = {cid: (total, done) for cid, total, done in by_category}
        reports = []
        for meta in sorted(known.values(), key=lambda c: (c.sort_order, c.id)):
            total, done = counted.pop(meta.id, (0, 0))
            reports.append(
                CategoryReport(
                    category_id=meta.id,
                    category_name_ar=meta.name_ar,
                    icon_key=meta.icon_key,
                    total=total,
                    completed=done,
                    incomplete=total - done,
                    completion_percentage=completion_percent(done, total),
                )
            )
        for category_id in sorted(counted):
            total, done = counted[category_id]
            reports.append(
                CategoryReport(
                    category_id=category_id,
                    category_name_ar=category_id,
                    icon_key=category_id,
                    total=total,
                    completed=done,
                    incomplete=total - done,
                    completion_percentage=completion_percent(done, total),
                )
            )
        return reports
