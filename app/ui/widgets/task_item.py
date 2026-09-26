"""Visual representation and interaction for an individual task item."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QContextMenuEvent, QResizeEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from app.core.models import Task, TaskPriority
from app.ui.layout_metrics import TASK_ROW_GAP, TASK_ROW_MARGIN_H, TASK_ROW_MARGIN_V
from app.ui.priority_presentation import PRIORITY_CHOICES, label_for
from app.ui.widgets.arabic_task_cluster import ArabicTaskCluster


class TaskItem(QFrame):
    """A single task row: checkbox on the physical right, Arabic text beside it.

    Layout direction on this frame is LeftToRight so widget order is physical
    and is not mirrored again by the application RTL direction. The text
    label itself is RightToLeft.
    """

    completed_toggled = Signal(int, bool)  # task_id, is_completed
    edit_requested = Signal(int)           # task_id
    delete_requested = Signal(int)         # task_id
    priority_change_requested = Signal(int, str)  # task_id, TaskPriority value

    def __init__(self, task: Task, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.task_id = task.id
        self.setObjectName("taskItemFrame")
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setMinimumWidth(0)
        self._priority = task.priority if isinstance(task.priority, TaskPriority) else TaskPriority(task.priority)
        self._init_ui(task)

    def _init_ui(self, task: Task) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            TASK_ROW_MARGIN_H,
            TASK_ROW_MARGIN_V,
            TASK_ROW_MARGIN_H,
            TASK_ROW_MARGIN_V,
        )
        layout.setSpacing(TASK_ROW_GAP)
        self._row_layout = layout

        self._checkbox = QCheckBox(self)
        self._checkbox.setObjectName("taskCheckBox")
        self._checkbox.setChecked(task.is_completed)
        self._checkbox.setAccessibleName(f"تحديد إنجاز المهمة: {task.text}")
        self._checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checkbox.toggled.connect(self._on_toggled)

        self._cluster = ArabicTaskCluster(task.text, self._priority, task.is_completed, self)
        self._text_label = self._cluster.text_label
        self._priority_badge = self._cluster.badge

        self.setAccessibleName(f"مهمة: {task.text}")

        # Physical left → right: breathing room, text+badge cluster, checkbox.
        layout.addStretch(1)
        layout.addWidget(self._cluster, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

        self._refresh_accessible_description()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fit_cluster()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fit_cluster()

    def _fit_cluster(self) -> None:
        """Cap the text cluster at the space left of the checkbox.

        Use the scroll-area viewport when the row has been stretched by an
        earlier size hint. Fitting to that stretched width is what pushes
        the badge off-screen and opens a horizontal scrollbar.
        """
        width = self._row_width_limit()
        if width < 80:
            return
        margins = self._row_layout.contentsMargins()
        spacing = self._row_layout.spacing()
        checkbox_w = max(self._checkbox.sizeHint().width(), 18)
        available = width - margins.left() - margins.right() - checkbox_w - spacing
        self._cluster.fit(available)

    def _row_width_limit(self) -> int:
        width = self.width()
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                return min(width, parent.viewport().width())
            parent = parent.parentWidget()
        return width

    def priority(self) -> TaskPriority:
        return self._priority

    def text(self) -> str:
        return self._text_label.text()

    def _on_toggled(self, checked: bool) -> None:
        self._cluster.set_completed(checked)
        self._refresh_accessible_description()
        if self.task_id is not None:
            self.completed_toggled.emit(self.task_id, checked)

    def _refresh_accessible_description(self) -> None:
        status_text = "مكتملة" if self._checkbox.isChecked() else "غير مكتملة"
        self.setAccessibleDescription(
            f"الحالة: {status_text} • الأولوية: {label_for(self._priority)}"
        )

    def set_completed_silently(self, is_completed: bool) -> None:
        """Update checkbox state without re-emitting toggled signal."""
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(is_completed)
        self._cluster.set_completed(is_completed)
        self._refresh_accessible_description()
        self._checkbox.blockSignals(False)

    def update_task_text(self, new_text: str) -> None:
        """Update visible task text."""
        self._cluster.set_text(new_text)
        self.setAccessibleName(f"مهمة: {new_text}")
        self._checkbox.setAccessibleName(f"تحديد إنجاز المهمة: {new_text}")
        self._fit_cluster()

    def set_priority(self, priority: TaskPriority) -> None:
        """Update the visible priority badge. Does not emit or persist."""
        resolved = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
        self._priority = resolved
        self._cluster.set_priority(resolved)
        self._refresh_accessible_description()
        self._fit_cluster()

    def _create_context_menu(self) -> QMenu:
        """Build the task context menu, including the priority section."""
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        edit_action = QAction("تعديل المهمة", menu)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.task_id))
        menu.addAction(edit_action)

        delete_action = QAction("حذف المهمة", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.task_id))
        menu.addAction(delete_action)

        menu.addSeparator()

        priority_menu = QMenu("الأولوية", menu)
        priority_menu.setObjectName("taskPriorityMenu")
        priority_menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.addMenu(priority_menu)

        group = QActionGroup(priority_menu)
        group.setExclusive(True)

        for priority in PRIORITY_CHOICES:
            action = QAction(label_for(priority), priority_menu)
            action.setCheckable(True)
            action.setData(priority.value)
            action.setChecked(priority == self._priority)
            group.addAction(action)
            priority_menu.addAction(action)
            action.triggered.connect(
                lambda checked=False, selected=priority: self._on_priority_action(selected)
            )

        return menu

    def _on_priority_action(self, priority: TaskPriority) -> None:
        """Request a priority change. Selecting the current value is a no-op."""
        if self.task_id is None or priority == self._priority:
            return
        self.priority_change_requested.emit(self.task_id, priority.value)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show context menu for editing, priority, or deleting this task."""
        menu = self._create_context_menu()
        menu.exec(event.globalPos())
        event.accept()
        menu.deleteLater()
