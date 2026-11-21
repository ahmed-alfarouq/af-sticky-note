"""Persistence for task categories. UI and core layers never touch SQL directly."""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from app.core.models import Category
from app.infrastructure.clock import utc_now_iso


class CategoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self) -> List[Category]:
        """All categories in deterministic sort_order (then id) order."""
        rows = self._conn.execute(
            "SELECT * FROM categories ORDER BY sort_order ASC, id ASC"
        ).fetchall()
        return [self._row_to_category(row) for row in rows]

    def list_active(self) -> List[Category]:
        """Categories available to future selection UI (is_active = 1)."""
        rows = self._conn.execute(
            "SELECT * FROM categories WHERE is_active = 1 ORDER BY sort_order ASC, id ASC"
        ).fetchall()
        return [self._row_to_category(row) for row in rows]

    def get_by_id(self, category_id: str) -> Optional[Category]:
        row = self._conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return self._row_to_category(row) if row else None

    def set_active(self, category_id: str, is_active: bool) -> None:
        """Activate/deactivate a category. Existing tasks keep their assignment."""
        now = utc_now_iso()
        self._conn.execute(
            "UPDATE categories SET is_active = ?, updated_at = ? WHERE id = ?",
            (int(is_active), now, category_id),
        )

    @staticmethod
    def _row_to_category(row: sqlite3.Row) -> Category:
        return Category(
            id=row["id"],
            name_ar=row["name_ar"],
            icon_key=row["icon_key"],
            sort_order=row["sort_order"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
