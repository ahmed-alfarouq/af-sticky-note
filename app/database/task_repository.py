"""Persistence for tasks. UI and core layers never touch SQL directly."""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from app.core.models import Task
from app.infrastructure.clock import utc_now_iso


class TaskRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_for_day(self, day_id: int) -> List[Task]:
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE day_id = ? ORDER BY position ASC",
            (day_id,),
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_by_id(self, task_id: int) -> Optional[Task]:
        row = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def create(self, day_id: int, text: str, position: Optional[int] = None) -> Task:
        """Create a task under day_id.

        Raises sqlite3.IntegrityError if day_id does not reference an
        existing Day — foreign-key enforcement prevents orphan tasks.
        """
        if position is None:
            position = self._next_position(day_id)
        now = utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO tasks (day_id, text, is_completed, position, created_at, updated_at)
                VALUES (?, ?, 0, ?, ?, ?)
                """,
                (day_id, text, position, now, now),
            )
        return Task(
            id=cursor.lastrowid,
            day_id=day_id,
            text=text,
            is_completed=False,
            position=position,
            created_at=now,
            updated_at=now,
        )

    def update_text(self, task_id: int, text: str) -> None:
        now = utc_now_iso()
        with self._conn:
            self._conn.execute(
                "UPDATE tasks SET text = ?, updated_at = ? WHERE id = ?",
                (text, now, task_id),
            )

    def set_completed(self, task_id: int, is_completed: bool) -> None:
        now = utc_now_iso()
        with self._conn:
            self._conn.execute(
                "UPDATE tasks SET is_completed = ?, updated_at = ? WHERE id = ?",
                (int(is_completed), now, task_id),
            )

    def delete(self, task_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def _next_position(self, day_id: int) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM tasks WHERE day_id = ?",
            (day_id,),
        ).fetchone()
        return row["next_position"]

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            day_id=row["day_id"],
            text=row["text"],
            is_completed=bool(row["is_completed"]),
            position=row["position"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )