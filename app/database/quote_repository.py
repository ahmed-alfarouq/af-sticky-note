"""Persistence for quotes. UI and core layers never touch SQL directly."""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from app.core.models import Quote
from app.infrastructure.clock import utc_now_iso


class QuoteRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self) -> List[Quote]:
        rows = self._conn.execute("SELECT * FROM quotes ORDER BY id ASC").fetchall()
        return [self._row_to_quote(row) for row in rows]

    def list_normal(self) -> List[Quote]:
        """Non-favorite quotes — the pool the rotation cycle draws from."""
        rows = self._conn.execute(
            "SELECT * FROM quotes WHERE is_favorite = 0 ORDER BY id ASC"
        ).fetchall()
        return [self._row_to_quote(row) for row in rows]

    def list_favorites(self) -> List[Quote]:
        rows = self._conn.execute(
            "SELECT * FROM quotes WHERE is_favorite = 1 ORDER BY id ASC"
        ).fetchall()
        return [self._row_to_quote(row) for row in rows]

    def get_by_id(self, quote_id: int) -> Optional[Quote]:
        row = self._conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
        return self._row_to_quote(row) if row else None

    def get_by_text(self, text: str) -> Optional[Quote]:
        row = self._conn.execute("SELECT * FROM quotes WHERE text = ?", (text,)).fetchone()
        return self._row_to_quote(row) if row else None

    def create(self, text: str, is_favorite: bool = False, is_user_created: bool = False) -> Quote:
        now = utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO quotes (text, is_favorite, is_user_created, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (text, int(is_favorite), int(is_user_created), now, now),
            )
        return Quote(
            id=cursor.lastrowid,
            text=text,
            is_favorite=is_favorite,
            is_user_created=is_user_created,
            created_at=now,
            updated_at=now,
        )

    def set_favorite(self, quote_id: int, is_favorite: bool) -> None:
        now = utc_now_iso()
        with self._conn:
            self._conn.execute(
                "UPDATE quotes SET is_favorite = ?, updated_at = ? WHERE id = ?",
                (int(is_favorite), now, quote_id),
            )

    @staticmethod
    def _row_to_quote(row: sqlite3.Row) -> Quote:
        return Quote(
            id=row["id"],
            text=row["text"],
            is_favorite=bool(row["is_favorite"]),
            is_user_created=bool(row["is_user_created"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )