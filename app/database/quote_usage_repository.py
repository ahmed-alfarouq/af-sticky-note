"""Persistence for quote-usage history (which quote was used on which
day, in which cycle, and whether it was a favorite pick).

This table is the durable state that makes cycle-level non-repetition
possible across application restarts — it is never held only in memory.
"""
from __future__ import annotations

import sqlite3
from typing import Optional, Set

from app.core.models import QuoteUsage
from app.infrastructure.clock import utc_now_iso


class QuoteUsageRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record_usage(
        self, day_id: int, quote_id: int, cycle_number: int, is_favorite_selection: bool
    ) -> QuoteUsage:
        now = utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO quote_usage (day_id, quote_id, cycle_number, is_favorite_selection, selected_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (day_id, quote_id, cycle_number, int(is_favorite_selection), now),
            )
        return QuoteUsage(
            id=cursor.lastrowid,
            day_id=day_id,
            quote_id=quote_id,
            cycle_number=cycle_number,
            is_favorite_selection=is_favorite_selection,
            selected_at=now,
        )

    def get_consumed_normal_ids(self, cycle_number: int) -> Set[int]:
        """Quote IDs already used as a normal (non-favorite) pick in this cycle."""
        rows = self._conn.execute(
            "SELECT quote_id FROM quote_usage WHERE cycle_number = ? AND is_favorite_selection = 0",
            (cycle_number,),
        ).fetchall()
        return {row["quote_id"] for row in rows}

    def get_for_day(self, day_id: int) -> Optional[QuoteUsage]:
        row = self._conn.execute(
            "SELECT * FROM quote_usage WHERE day_id = ?", (day_id,)
        ).fetchone()
        return self._row_to_usage(row) if row else None

    @staticmethod
    def _row_to_usage(row: sqlite3.Row) -> QuoteUsage:
        return QuoteUsage(
            id=row["id"],
            day_id=row["day_id"],
            quote_id=row["quote_id"],
            cycle_number=row["cycle_number"],
            is_favorite_selection=bool(row["is_favorite_selection"]),
            selected_at=row["selected_at"],
        )