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
        now = utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO days (date, quote_text, created_at, updated_at) VALUES (?, NULL, ?, ?)",
                (date, now, now),
            )
        return Day(id=cursor.lastrowid, date=date, quote_text=None, created_at=now, updated_at=now)

    def get_or_create(self, date: str) -> Day:
        existing = self.get_by_date(date)
        if existing is not None:
            return existing
        return self.create(date)

    def set_quote_text(self, day_id: int, quote_text: str) -> Day:
        """Attach the assigned quote's text to a Day as its historical snapshot."""
        now = utc_now_iso()
        with self._conn:
            self._conn.execute(
                "UPDATE days SET quote_text = ?, updated_at = ? WHERE id = ?",
                (quote_text, now, day_id),
            )
        return self.get_by_id(day_id)

    @staticmethod
    def _row_to_day(row: sqlite3.Row) -> Day:
        return Day(
            id=row["id"],
            date=row["date"],
            quote_text=row["quote_text"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )