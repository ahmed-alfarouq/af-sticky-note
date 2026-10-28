"""A single task row: completion circle, title, and meta line.

Layout (RTL: first added renders rightmost)::

    [checkbox 28px] --12px-- [title 15px / meta 12px, takes remaining width]

Variants: open, done, past-day unfinished, past-day completed. Past-day rows
are read-only: disabled checkbox, no inline edit, no context menu.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Sequence

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QContextMenuEvent, QKeyEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from app.core.models import Category, Task, TaskPriority
from app.ui.category_icons import CategoryIconProvider
from app.ui.category_presentation import category_label
from app.ui.priority_presentation import PRIORITY_LABELS
from app.ui.styles.task_item_style import (
    META_TOP_GAP,
    ROW_CONTENT_GAP,
    ROW_MIN_HEIGHT,
    ROW_PADDING_H,
    ROW_PADDING_V,
    TITLE_PX,
    repolish,
)
from app.ui.widgets.task_item.checkbox import CompletionCheckbox
from app.ui.widgets.task_item.elided_label import ElidedLabel
from app.ui.widgets.task_item.menu import build_task_menu
from app.ui.widgets.task_item.meta_line import TaskMetaLine

__all__ = ["TaskItem"]

_INLINE_EDIT_MAX_LENGTH = 200
_INLINE_EDIT_HEIGHT = 26
_EDIT_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F2)


class TaskItem(QFrame):
    """One task row."""

    completed_toggled = Signal(int, bool)            # task_id, is_completed
    edit_requested = Signal(int)                     # task_id
    delete_requested = Signal(int)                   # task_id
    priority_change_requested = Signal(int, object)  # task_id, TaskPriority
    category_change_requested = Signal(int, str)     # task_id, category_id
    inline_edit_committed = Signal(int, str)         # task_id, trimmed new text

    def __init__(
        self,
        task: Task,
        parent: Optional[QWidget] = None,
        categories: Sequence[Category] = (),
        icon_provider: Optional[CategoryIconProvider] = None,
        read_only: bool = False,
    ) -> None:
        super().__init__(parent)
        self.task_id = task.id
        self._task = task
        self._categories: List[Category] = list(categories)
        self._icon_provider = icon_provider
        self._read_only = read_only
        self._edit_field: Optional[QLineEdit] = None

        self._build_ui()
        self._refresh()

    # -- Construction -------------------------------------------------------

    def _build_ui(self) -> None:
        self.setObjectName("taskItemFrame")
        self.setMinimumHeight(ROW_MIN_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            ROW_PADDING_H, ROW_PADDING_V, ROW_PADDING_H, ROW_PADDING_V
        )
        layout.setSpacing(ROW_CONTENT_GAP)

        self._checkbox = CompletionCheckbox(self)
        self._checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self._checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

        # No explicit alignment: under the app-level RTL direction a QLabel
        # already anchors text to the right edge; AlignRight would mirror it.
        self._text_label = ElidedLabel(parent=self)
        self._text_label.setObjectName("taskTitle")
        self._text_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._text_label.installEventFilter(self)

        self._meta = TaskMetaLine(self)

        self._text_column = QVBoxLayout()
        self._text_column.setContentsMargins(0, 0, 0, 0)
        self._text_column.setSpacing(META_TOP_GAP)
        self._text_column.addStretch(1)
        self._text_column.addWidget(self._text_label)
        self._text_column.addWidget(self._meta)
        self._text_column.addStretch(1)
        layout.addLayout(self._text_column, 1)

    # -- State -> visuals (single place) -----------------------------------

    def _refresh(self) -> None:
        """Apply the current task and read-only flag to every part of the row."""
        task = self._task
        completed = task.is_completed

        self._checkbox.sync(completed, self._read_only)

        title = self._text_label
        title.set_full_text(task.text)
        title.setToolTip(task.text)
        font = title.font()
        font.setPixelSize(TITLE_PX)
        font.setStrikeOut(completed)
        title.setFont(font)
        title.setProperty("muted", completed)
        repolish(title)

        if completed:
            self._meta.setVisible(False)
        else:
            self._meta.setVisible(True)
            if self._read_only:
                self._meta.show_unfinished()
            else:
                self._meta.show_priority(task.priority, self._category_name())

        status = "مكتملة" if completed else "غير مكتملة"
        self.setAccessibleName(f"مهمة: {task.text}")
        self.setAccessibleDescription(
            f"الحالة: {status}. "
            f"الأولوية: {PRIORITY_LABELS[task.priority]}. "
            f"الفئة: {self._category_name()}"
        )

    def _category_name(self) -> str:
        for category in self._categories:
            if category.id == self._task.category_id:
                return category_label(category)
        return self._task.category_id

    # -- Public API ---------------------------------------------------------

    @property
    def task(self) -> Task:
        """The task this row currently carries."""
        return self._task

    def focus_widgets(self) -> List[QWidget]:
        """Tab stops of this row, in order."""
        return [self._checkbox, self._text_label]

    def focus_checkbox(self) -> None:
        self._checkbox.setFocus()

    @property
    def priority(self) -> TaskPriority:
        return self._task.priority

    @property
    def task_text(self) -> str:
        return self._task.text

    @property
    def category_id(self) -> str:
        return self._task.category_id

    def is_read_only(self) -> bool:
        return self._read_only

    def set_read_only(self, read_only: bool) -> None:
        """Switch between editable and past-day (read-only) presentation."""
        if read_only == self._read_only:
            return
        self._cancel_inline_edit()
        self._read_only = read_only
        self._refresh()

    def set_categories(
        self,
        categories: Sequence[Category],
        icon_provider: Optional[CategoryIconProvider] = None,
    ) -> None:
        self._categories = list(categories)
        if icon_provider is not None:
            self._icon_provider = icon_provider
        self._refresh()

    def update_task_category(self, category_id: str) -> None:
        self._task = replace(self._task, category_id=category_id)
        self._refresh()

    def update_task_priority(self, priority: TaskPriority) -> None:
        self._task = replace(self._task, priority=priority)
        self._refresh()

    def update_task_text(self, new_text: str) -> None:
        self._cancel_inline_edit()
        self._task = replace(self._task, text=new_text)
        self._refresh()

    def set_completed_silently(self, is_completed: bool) -> None:
        """Update completion without emitting ``completed_toggled``."""
        self._task = replace(self._task, is_completed=is_completed)
        self._refresh()

    def _on_toggled(self, checked: bool) -> None:
        self._task = replace(self._task, is_completed=checked)
        self._refresh()
        self.completed_toggled.emit(self.task_id, checked)

    # -- Inline title editing ----------------------------------------------

    def is_editing_inline(self) -> bool:
        return self._edit_field is not None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self._text_label and not self._read_only:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self._start_inline_edit()
                return True
            if isinstance(event, QKeyEvent) and event.key() in _EDIT_KEYS:
                self._start_inline_edit()
                return True

        elif watched is self._edit_field:
            if isinstance(event, QKeyEvent) and event.key() == Qt.Key.Key_Escape:
                self._cancel_inline_edit()
                return True

        return super().eventFilter(watched, event)

    def _start_inline_edit(self) -> None:
        """Swap the title for an edit field with the text selected."""
        if self._read_only or self._edit_field is not None or self.task_id is None:
            return

        field = QLineEdit(self)
        field.setObjectName("taskTitleEdit")
        field.setText(self._task.text)
        field.setMaxLength(_INLINE_EDIT_MAX_LENGTH)
        field.setFixedHeight(_INLINE_EDIT_HEIGHT)
        field.selectAll()
        field.editingFinished.connect(self._commit_inline_edit)
        field.installEventFilter(self)

        index = self._text_column.indexOf(self._text_label)
        self._text_column.removeWidget(self._text_label)
        self._text_column.insertWidget(index, field)
        self._text_label.hide()

        self._edit_field = field
        field.setFocus()

    def _commit_inline_edit(self) -> None:
        """Persist a non-empty, changed edit; otherwise cancel silently."""
        field = self._edit_field
        if field is None or self.task_id is None:
            return

        cleaned = field.text().strip()
        task_id = self.task_id
        changed = bool(cleaned) and cleaned != self._task.text

        self._finish_inline_edit()
        if changed:
            self.inline_edit_committed.emit(task_id, cleaned)
        self._text_label.setFocus()

    def _cancel_inline_edit(self) -> None:
        if self._edit_field is None:
            return
        self._finish_inline_edit()
        self._text_label.setFocus()

    def _finish_inline_edit(self) -> None:
        field = self._edit_field
        self._edit_field = None

        if field is not None:
            field.removeEventFilter(self)
            index = self._text_column.indexOf(field)
            self._text_column.removeWidget(field)
            self._text_column.insertWidget(max(0, index), self._text_label)
            field.deleteLater()

        self._text_label.show()

    # -- Context menu -------------------------------------------------------

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        if self._read_only:
            event.ignore()
            return

        task_id = self.task_id
        menu = build_task_menu(
            self,
            self._task,
            self._categories,
            self._icon_provider,
            on_edit=lambda: self.edit_requested.emit(task_id),
            on_category=lambda cid: self.category_change_requested.emit(task_id, cid),
            on_priority=lambda p: self.priority_change_requested.emit(task_id, p),
            on_delete=lambda: self.delete_requested.emit(task_id),
        )
        menu.exec(event.globalPos())
        event.accept()