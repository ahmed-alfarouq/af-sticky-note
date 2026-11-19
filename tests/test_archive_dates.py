"""The archive lists only past days that hold tasks."""
from app.core.services.history_service import HistoryService
from app.core.services.task_service import TaskService
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository


def test_archive_dates_are_past_days_with_tasks_newest_first(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)
    tasks = TaskService(task_repo)
    history = HistoryService(day_repo=day_repo, task_repo=task_repo)

    old = day_repo.create("2026-10-20")
    empty = day_repo.create("2026-10-22")   # a day that never held a task
    recent = day_repo.create("2026-10-24")
    today = day_repo.create("2026-10-27")

    tasks.create_task(old.id, "A")
    tasks.create_task(recent.id, "B")
    tasks.create_task(today.id, "C")        # today itself is not archived

    assert history.get_archive_dates("2026-10-27") == ["2026-10-24", "2026-10-20"]
    assert empty.date not in history.get_archive_dates("2026-10-27")


def test_archive_dates_empty_without_history(db_connection):
    history = HistoryService(
        day_repo=DayRepository(db_connection), task_repo=TaskRepository(db_connection)
    )
    assert history.get_archive_dates("2026-10-27") == []