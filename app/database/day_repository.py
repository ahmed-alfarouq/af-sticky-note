"""Persistence for daily records. UI and core layers never touch SQL directly."""
from __future__ import annotations

import sqlite3
from typing import Optional

from app.core.models import Day
from app.infrastructure.clock import utc_now_iso


class DayRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_id(self, day_id: int) -> Optional[Day]:
        row = self._conn.execute("SELECT * FROM days WHERE id = ?", (day_id,)).fetchone()
        return self._row_to_day(row) if row else None

    def get_by_date(self, date: str) -> Optional[Day]:
        row = self._conn.execute("SELECT * FROM days WHERE date = ?", (date,)).fetchone()
        return self._row_to_day(row) if row else None

    def create(self, date: str) -> Day:
        """Create a new Day for the given local calendar date (YYYY-MM-DD).

        Raises sqlite3.IntegrityError if a Day for that date already
        exists (date has a UNIQUE constraint). Callers wanting
        "load or create" semantics should use get_or_create.
        """
        now = utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO days (date, quote_text, created_at, updated_at) VALUES (?, NULL, ?, ?)",
                (date, now, now),
            )
        return Day(id=cursor.lastrowid, date=date, quote_text=None, created_at=now, updated_at=now)

    def get_or_create(self, date: str) -> Day:
        """Load the Day for this date if it exists; otherwise create it.

        Never copies tasks or state from any other day — a new Day
        always starts empty.
        """
        existing = self.get_by_date(date)
        if existing is not None:
            return existing
        return self.create(date)

    @staticmethod
    def _row_to_day(row: sqlite3.Row) -> Day:
        return Day(
            id=row["id"],
            date=row["date"],
            quote_text=row["quote_text"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )