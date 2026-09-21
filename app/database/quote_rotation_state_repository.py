"""Persistence for the single current-cycle counter.

A one-row table rather than a computed MAX(cycle_number) query: it
stays correct even in the edge case where a cycle has just started
and has zero usage rows recorded against it yet.
"""
from __future__ import annotations

import sqlite3

_ROW_ID = 1


class QuoteRotationStateRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_current_cycle(self) -> int:
        row = self._conn.execute(
            "SELECT current_cycle FROM quote_rotation_state WHERE id = ?", (_ROW_ID,)
        ).fetchone()
        if row is None:
            # Defensive: the migration seeds this row, but stay safe
            # if it's ever missing (e.g. a hand-edited test database).
            with self._conn:
                self._conn.execute(
                    "INSERT INTO quote_rotation_state (id, current_cycle) VALUES (?, 1)",
                    (_ROW_ID,),
                )
            return 1
        return row["current_cycle"]

    def advance_cycle(self) -> int:
        with self._conn:
            self._conn.execute(
                "UPDATE quote_rotation_state SET current_cycle = current_cycle + 1 WHERE id = ?",
                (_ROW_ID,),
            )
        return self.get_current_cycle()