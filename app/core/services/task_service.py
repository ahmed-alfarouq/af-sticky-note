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

from app.core.models import Task
from app.database.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, task_repo: TaskRepository) -> None:
        self._task_repo = task_repo

    def get_today_tasks(self, day_id: int) -> List[Task]:
        """Fetch all tasks for the given day, ordered by position ascending."""
        return self._task_repo.list_for_day(day_id)

    def create_task(self, day_id: int, text: str) -> Optional[Task]:
        """Validate non-empty text, strip whitespace, and persist.

        Returns the created Task on success.
        Returns None if text is empty or whitespace-only (no record created).
        """
        if text is None:
            return None
        cleaned = text.strip()
        if not cleaned:
            return None
        return self._task_repo.create(day_id=day_id, text=cleaned)

    def toggle_task_completion(self, task_id: int, is_completed: bool) -> None:
        """Update the completion status of a task."""
        self._task_repo.set_completed(task_id=task_id, is_completed=is_completed)

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
