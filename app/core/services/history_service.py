"""Read-only service providing historical day records, tasks, and statistics.

Guarantees historical immutability:
- Pure read-only queries against DayRepository and TaskRepository.
- Does not create days, does not modify tasks, does not alter rollover relationships.
- Calculates daily stats purely via compute_daily_stats domain logic.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from app.core.daily_stats import DailyStats, compute_daily_stats
from app.core.models import Day, Task
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DayHistoryView:
    date: str
    day: Optional[Day]
    tasks: List[Task]
    stats: DailyStats


class HistoryService:
    """Read-only service for viewing historical days and their tasks."""

    def __init__(self, day_repo: DayRepository, task_repo: TaskRepository) -> None:
        self._day_repo = day_repo
        self._task_repo = task_repo

    def get_available_dates(self) -> List[str]:
        """Return all historical dates recorded in the database (newest first)."""
        return self._day_repo.list_all_dates_desc()

    def get_day_history(self, date_str: str) -> DayHistoryView:
        """Retrieve historical snapshot for a specific calendar date (read-only).

        If the day does not exist in the database, returns an empty snapshot
        without creating any records.
        """
        day = self._day_repo.get_by_date(date_str)
        if day is None or day.id is None:
            empty_stats = compute_daily_stats([])
            return DayHistoryView(
                date=date_str,
                day=None,
                tasks=[],
                stats=empty_stats,
            )

        tasks = self._task_repo.list_for_day(day.id)
        stats = compute_daily_stats(tasks)
        return DayHistoryView(
            date=date_str,
            day=day,
            tasks=tasks,
            stats=stats,
        )
