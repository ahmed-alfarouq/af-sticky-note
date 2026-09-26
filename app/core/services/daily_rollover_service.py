"""Domain service managing the daily rollover of incomplete tasks.

At the transition to a new day:
- Incomplete tasks from the source day are copied into the target day.
- Source day tasks remain historically untouched (immutable).
- Target tasks receive new primary keys, new timestamps, target day_id,
  and start incomplete (is_completed = False).
- Text, priority, and original position are preserved.
- The operation is idempotent: executing it repeatedly for the same target day
  will never duplicate tasks (guaranteed by database unique index and checks).
- Executed atomically within UnitOfWork.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import List, Optional

from app.core.models import Day, Task
from app.database.day_repository import DayRepository
from app.database.task_repository import TaskRepository
from app.database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class DailyRolloverService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        day_repo: DayRepository,
        task_repo: TaskRepository,
    ) -> None:
        self._conn = conn
        self._day_repo = day_repo
        self._task_repo = task_repo

    def rollover_tasks(
        self,
        source_date: str,
        target_date: str,
    ) -> List[Task]:
        """Carry over incomplete tasks from source_date to target_date.

        Returns the list of newly created or already existing rollover tasks
        on the target day.
        """
        if source_date >= target_date:
            raise ValueError(f"source_date ({source_date}) must be before target_date ({target_date})")

        # 1. Retrieve source day; if it does not exist, nothing to carry over
        source_day = self._day_repo.get_by_date(source_date)
        if source_day is None or source_day.id is None:
            logger.info("Source day %s does not exist; no tasks to rollover.", source_date)
            return []

        # 2. Retrieve or create target day
        target_day = self._day_repo.get_or_create(target_date)
        assert target_day.id is not None, "target_day id must be present"

        # 3. Atomically perform rollover inside UnitOfWork
        with UnitOfWork(self._conn):
            incomplete_tasks = self._task_repo.list_incomplete_for_day(source_day.id)
            if not incomplete_tasks:
                logger.info("Source day %s has no incomplete tasks.", source_date)
                return []

            rolled_over_tasks: List[Task] = []
            for task in incomplete_tasks:
                assert task.id is not None, "Task id must be present on persisted task"
                # Idempotency check: if already rolled over to target day, skip
                if self._task_repo.has_rollover_copy(target_day.id, task.id):
                    continue

                new_task = self._task_repo.create(
                    day_id=target_day.id,
                    text=task.text,
                    position=task.position,
                    priority=task.priority,
                    source_task_id=task.id,
                )
                rolled_over_tasks.append(new_task)

            return rolled_over_tasks
