from app.core.daily_stats import compute_daily_stats
from app.core.models import Task


def _task(is_completed: bool, position: int) -> Task:
    return Task(
        id=position,
        day_id=1,
        text=f"task {position}",
        is_completed=is_completed,
        position=position,
        created_at="2026-09-21T00:00:00+00:00",
        updated_at="2026-09-21T00:00:00+00:00",
    )


def test_seventy_percent_completion():
    tasks = [_task(True, i) for i in range(7)] + [_task(False, i) for i in range(7, 10)]
    stats = compute_daily_stats(tasks)
    assert stats.total == 10
    assert stats.completed == 7
    assert stats.incomplete == 3
    assert stats.completion_percentage == 70.0


def test_zero_percent_completion():
    tasks = [_task(False, i) for i in range(10)]
    stats = compute_daily_stats(tasks)
    assert stats.completion_percentage == 0.0
    assert stats.incomplete == 10


def test_full_completion():
    tasks = [_task(True, i) for i in range(10)]
    stats = compute_daily_stats(tasks)
    assert stats.completion_percentage == 100.0
    assert stats.incomplete == 0


def test_empty_day_does_not_crash():
    stats = compute_daily_stats([])
    assert stats.total == 0
    assert stats.completion_percentage == 0.0


def test_incomplete_count_matches():
    tasks = [_task(True, 0), _task(False, 1), _task(False, 2)]
    stats = compute_daily_stats(tasks)
    assert stats.incomplete == 2