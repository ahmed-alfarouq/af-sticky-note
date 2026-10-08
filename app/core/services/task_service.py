"""Application service managing tasks.

Coordinates task operations between the UI and TaskRepository:
- Validates task text (rejects empty or whitespace-only inputs).
- Strips leading/trailing whitespace.
- Keeps UI decoupled from database / SQL details.
- Never duplicates repository SQL logic.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.core.models import DEFAULT_CATEGORY_ID, Task, TaskPriority
from app.core.services.category_service import CategoryService
from app.database.category_repository import CategoryRepository
from app.database.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        category_repo: Optional[CategoryRepository] = None,
    ) -> None:
        self._task_repo = task_repo
        self._category_repo = category_repo
        # Single home for the "omitted -> default, explicit -> must exist"
        # rule; kept optional so pre-category call sites keep working.
        self._category_service = (
            CategoryService(category_repo) if category_repo is not None else None
        )

    def _resolve_category(self, category_id: Optional[str]) -> str:
        """Return a validated category id, defaulting to DEFAULT_CATEGORY_ID.

        Raises ValueError for empty/non-string ids and for ids unknown to the
        category repository (when one is wired). Never silently substitutes:
        callers pass None (or omit) for the default, anything else must exist.
        """
        if self._category_service is not None:
            return self._category_service.resolve_category_id(category_id)
        if category_id is None:
            return DEFAULT_CATEGORY_ID
        if not isinstance(category_id, str) or not category_id:
            raise ValueError(f"Invalid task category: {category_id!r}")
        return category_id

    def get_today_tasks(self, day_id: int) -> List[Task]:
        """Fetch all tasks for the given day, ordered by position ascending."""
        return self._task_repo.list_for_day(day_id)

    def create_task(
        self,
        day_id: int,
        text: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        category_id: Optional[str] = None,
    ) -> Optional[Task]:
        """Validate non-empty text, strip whitespace, and persist.

        Returns the created Task on success.
        Returns None if text is empty or whitespace-only (no record created).
        Omitting category_id assigns the default category; an explicit but
        unknown category_id raises ValueError.
        """
        if text is None:
            return None
        cleaned = text.strip()
        if not cleaned:
            return None

        # Validate priority enum if passed as string or enum
        if not isinstance(priority, TaskPriority):
            try:
                priority = TaskPriority(priority)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid task priority: {priority}")

        category = self._resolve_category(category_id)

        return self._task_repo.create(day_id=day_id, text=cleaned, priority=priority, category_id=category)

    def toggle_task_completion(self, task_id: int, is_completed: bool) -> None:
        """Update the completion status of a task."""
        self._task_repo.set_completed(task_id=task_id, is_completed=is_completed)

    def update_task_priority(self, task_id: int, priority: TaskPriority) -> None:
        """Update the priority of a task."""
        if not isinstance(priority, TaskPriority):
            try:
                priority = TaskPriority(priority)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid task priority: {priority}")
        self._task_repo.update_priority(task_id=task_id, priority=priority)

    def update_task_category(self, task_id: int, category_id: str) -> None:
        """Update the category of a task.

        Unknown or empty ids raise ValueError; unlike create_task, None is
        rejected here because an update always names its target category.
        """
        if category_id is None:
            raise ValueError("Invalid task category: None")
        category = self._resolve_category(category_id)
        self._task_repo.update_category(task_id=task_id, category_id=category)

    def delete_task(self, task_id: int) -> None:
        """Remove a task by ID."""
        self._task_repo.delete(task_id=task_id)

    def update_task_text(self, task_id: int, new_text: str) -> bool:
        """Update task text if valid and non-empty.

        Returns True on successful update, False if new_text is blank.
        """
        if new_text is None:
            return False
        cleaned = new_text.strip()
        if not cleaned:
            return False
        self._task_repo.update_text(task_id=task_id, text=cleaned)
        return True

    def clear_completed_tasks(self, day_id: int) -> int:
        """Clear all completed tasks for a specific day.

        Returns the count of deleted tasks.
        Guarantees that other days' task records are never affected.
        """
        return self._task_repo.delete_completed_for_day(day_id=day_id)
