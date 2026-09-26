"""Persistence for daily records. UI and core layers never touch SQL directly.

Statements commit immediately when called standalone (autocommit
connection mode) or participate in an ambient explicit transaction
opened by a caller via transaction(conn). This repository never
calls commit()/rollback() itself.
"""
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
        now = utc_now_iso()
        self._conn.execute(
            "UPDATE days SET quote_text = ?, updated_at = ? WHERE id = ?",
            (quote_text, now, day_id),
        )
        updated_day = self.get_by_id(day_id)
        assert updated_day is not None, f"Day {day_id} vanished immediately after its own update"
        return updated_day

    def list_all_dates_desc(self) -> list[str]:
        """Return all recorded calendar dates in descending order (newest first)."""
        rows = self._conn.execute("SELECT date FROM days ORDER BY date DESC").fetchall()
        return [row["date"] for row in rows]

    @staticmethod
    def _row_to_day(row: sqlite3.Row) -> Day:
        return Day(
            id=row["id"],
            date=row["date"],
            quote_text=row["quote_text"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )