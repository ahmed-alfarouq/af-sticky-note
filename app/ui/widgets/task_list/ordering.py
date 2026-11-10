"""View ordering for the task list (never rewrites stored positions).

Open tasks are ordered by priority first (most urgent on top), then by their
stored position, so equal priorities keep creation order. Completed tasks
follow in stored order; priority no longer matters once a task is done.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

from app.core.models import Task
from app.ui.priority_presentation import PRIORITY_ORDER
from app.ui.widgets.task_item import TaskItem

__all__ = ["open_order_key", "view_order_key", "split_rows"]


def open_order_key(task: Task) -> Tuple[int, int, int]:
    """Order among open tasks: priority rank, then position, then id."""
    return (PRIORITY_ORDER.index(task.priority), task.position, task.id or 0)


def view_order_key(task: Task) -> Tuple[int, int, int, int]:
    """Open tasks first (by :func:`open_order_key`), completed last (by position)."""
    if task.is_completed:
        return (1, 0, task.position, task.id or 0)
    return (0, *open_order_key(task))


def split_rows(rows: Iterable[TaskItem]) -> Tuple[List[TaskItem], List[TaskItem]]:
    """Return ``(open_rows, completed_rows)``, each in view order."""
    ordered = sorted(rows, key=lambda row: view_order_key(row.task))
    open_rows = [row for row in ordered if not row.task.is_completed]
    done_rows = [row for row in ordered if row.task.is_completed]
    return open_rows, done_rows