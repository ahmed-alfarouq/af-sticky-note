"""Read-only aggregate queries for weekly/range reporting (Phase 7E).

Two bounded GROUP BY queries plus the category metadata lookup -- never
one query per day, per category, or per task. All statements are
parameterized SELECTs; this repository never writes.
"""
from __future__ import annotations

import sqlite3
from typing import List, Tuple


class ReportRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def totals_by_category(self, start_date: str, end_date: str) -> List[Tuple[str, int, int]]:
        """``(category_id, total, completed)`` per category in the range."""
        rows = self._conn.execute(
            """
            SELECT t.category_id, COUNT(*), COALESCE(SUM(t.is_completed), 0)
            FROM tasks t
            JOIN days d ON d.id = t.day_id
            WHERE d.date BETWEEN ? AND ?
            GROUP BY t.category_id
            """,
            (start_date, end_date),
        ).fetchall()
        return [(row[0], row[1], row[2]) for row in rows]

    def totals_by_day(self, start_date: str, end_date: str) -> List[Tuple[str, int, int]]:
        """``(date, total, completed)`` per recorded day in the range."""
        rows = self._conn.execute(
            """
            SELECT d.date, COUNT(t.id), COALESCE(SUM(t.is_completed), 0)
            FROM days d
            LEFT JOIN tasks t ON t.day_id = d.id
            WHERE d.date BETWEEN ? AND ?
            GROUP BY d.date
            """,
            (start_date, end_date),
        ).fetchall()
        return [(row[0], row[1], row[2]) for row in rows]
