"""View ordering for the task list (never rewrites stored positions)."""

from __future__ import annotations

from typing import Iterable, List, Tuple

from app.core.models import Task
from app.ui.widgets.task_item import TaskItem

__all__ = ["view_order_key", "split_rows"]


def view_order_key(task: Task) -> Tuple[int, int, int]:
    """Incomplete tasks first (by position), completed last (by position)."""
    return (1 if task.is_completed else 0, task.position, task.id or 0)


def split_rows(rows: Iterable[TaskItem]) -> Tuple[List[TaskItem], List[TaskItem]]:
    """Return ``(open_rows, completed_rows)``, each in view order."""
    ordered = sorted(rows, key=lambda row: view_order_key(row.task))
    open_rows = [row for row in ordered if not row.task.is_completed]
    done_rows = [row for row in ordered if row.task.is_completed]
    return open_rows, done_rows
