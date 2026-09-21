"""Manual sanity check — not part of the automated test suite.

Creates a throwaway database, exercises the repositories, prints the
result, and deletes the file. Run directly, not with pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import create_connection
from app.database.day_repository import DayRepository
from app.database.migrations import apply_migrations
from app.database.task_repository import TaskRepository
from app.core.daily_stats import compute_daily_stats

DB_PATH = Path(__file__).parent.parent / "data" / "manual_verification.db"


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = create_connection(DB_PATH)
    apply_migrations(conn)

    day_repo = DayRepository(conn)
    task_repo = TaskRepository(conn)

    day = day_repo.create("2026-09-21")
    print(f"Created day: {day}")

    for text in ["شراء القهوة", "مراجعة الكود", "الرد على البريد"]:
        task_repo.create(day.id, text)

    tasks = task_repo.list_for_day(day.id)
    task_repo.set_completed(tasks[0].id, True)
    tasks = task_repo.list_for_day(day.id)

    stats = compute_daily_stats(tasks)
    print(f"Tasks: {[(t.text, t.is_completed) for t in tasks]}")
    print(f"Stats: {stats}")

    conn.close()
    DB_PATH.unlink()
    print("Verification database cleaned up.")


if __name__ == "__main__":
    main()