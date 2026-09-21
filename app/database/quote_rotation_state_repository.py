"""Persistence for the single current-cycle counter."""
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
            self._conn.execute(
                "INSERT INTO quote_rotation_state (id, current_cycle) VALUES (?, 1)",
                (_ROW_ID,),
            )
            return 1
        return row["current_cycle"]

    def advance_cycle(self) -> int:
        self._conn.execute(
            "UPDATE quote_rotation_state SET current_cycle = current_cycle + 1 WHERE id = ?",
            (_ROW_ID,),
        )
        return self.get_current_cycle()