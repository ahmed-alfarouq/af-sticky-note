"""Context menu for a task row."""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QWidget

from app.core.models import Category, Task, TaskPriority
from app.ui.category_icons import CategoryIconProvider
from app.ui.category_presentation import category_label, sort_categories
from app.ui.priority_presentation import PRIORITY_LABELS, PRIORITY_ORDER

__all__ = ["build_task_menu"]


def _submenu(parent: QMenu, title: str) -> QMenu:
    menu = QMenu(title, parent)
    menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    return menu


def build_task_menu(
    parent: QWidget,
    task: Task,
    categories: Sequence[Category],
    icon_provider: Optional[CategoryIconProvider],
    *,
    on_edit: Callable[[], None],
    on_category: Callable[[str], None],
    on_priority: Callable[[TaskPriority], None],
    on_delete: Callable[[], None],
) -> QMenu:
    """Build the edit / category / priority / delete menu for ``task``."""
    menu = QMenu(parent)
    menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    edit_action = QAction("تعديل المهمة", menu)
    edit_action.triggered.connect(lambda: on_edit())
    menu.addAction(edit_action)

    # Active categories only, current one checked. Omitted entirely when the
    # row carries no category choices.
    active = [c for c in sort_categories(categories) if c.is_active]
    if active:
        category_menu = _submenu(menu, "الفئة")
        group = QActionGroup(menu)
        group.setExclusive(True)
        for category in active:
            action = QAction(category_label(category), category_menu)
            if icon_provider is not None:
                action.setIcon(icon_provider.icon_for_category(category))
            action.setCheckable(True)
            action.setChecked(category.id == task.category_id)
            action.triggered.connect(
                lambda checked=False, cid=category.id: on_category(cid)
            )
            group.addAction(action)
            category_menu.addAction(action)
        menu.addMenu(category_menu)

    priority_menu = _submenu(menu, "الأولوية")
    group = QActionGroup(menu)
    group.setExclusive(True)
    for priority in PRIORITY_ORDER:
        action = QAction(PRIORITY_LABELS[priority], priority_menu)
        action.setCheckable(True)
        action.setChecked(priority == task.priority)
        action.triggered.connect(
            lambda checked=False, p=priority: on_priority(p)
        )
        group.addAction(action)
        priority_menu.addAction(action)
    menu.addMenu(priority_menu)

    delete_action = QAction("حذف المهمة", menu)
    delete_action.triggered.connect(lambda: on_delete())
    menu.addAction(delete_action)

    return menu