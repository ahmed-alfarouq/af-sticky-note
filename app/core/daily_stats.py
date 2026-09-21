"""Pure calculation of daily statistics from source-of-truth tasks.

No SQLite, no filesystem, no Qt — trivial to unit test.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.core.models import Task


@dataclass(frozen=True)
class DailyStats:
    total: int
    completed: int
    incomplete: int
    completion_percentage: float


def compute_daily_stats(tasks: Sequence[Task]) -> DailyStats:
    """Compute stats from a list of tasks.

    With 0 tasks, completion_percentage is defined as 0.0 (not NaN,
    not an error) — an empty day is considered 0% complete rather
    than undefined.
    """
    total = len(tasks)
    completed = sum(1 for task in tasks if task.is_completed)
    incomplete = total - completed
    percentage = round((completed / total) * 100, 2) if total else 0.0
    return DailyStats(
        total=total,
        completed=completed,
        incomplete=incomplete,
        completion_percentage=percentage,
    )