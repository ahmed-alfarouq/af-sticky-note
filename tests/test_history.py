from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository


def test_day_a_tasks_remain_unchanged_after_day_b_created(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)

    day_a = day_repo.create("2026-09-20")
    task_repo.create(day_a.id, "مهمة من الأمس")

    day_repo.create("2026-09-21")  # Day B

    assert [t.text for t in task_repo.list_for_day(day_a.id)] == ["مهمة من الأمس"]


def test_day_b_starts_without_copied_tasks(db_connection):
    day_repo = DayRepository(db_connection)
    task_repo = TaskRepository(db_connection)

    day_a = day_repo.create("2026-09-20")
    task_repo.create(day_a.id, "غير مكتملة بالأمس")

    day_b = day_repo.create("2026-09-21")
    assert task_repo.list_for_day(day_b.id) == []


def test_day_a_quote_remains_unchanged_after_day_b_created(db_connection):
    day_repo = DayRepository(db_connection)
    day_a = day_repo.create("2026-09-20")

    with db_connection:
        db_connection.execute(
            "UPDATE days SET quote_text = ? WHERE id = ?",
            ("اقتباس اليوم الأول", day_a.id),
        )

    day_repo.create("2026-09-21")  # Day B created afterward

    assert day_repo.get_by_id(day_a.id).quote_text == "اقتباس اليوم الأول"