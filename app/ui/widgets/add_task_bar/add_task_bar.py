"""The add-task bar: a 52 px input row with a plus button, and two chips.

Layout (RTL: first added renders rightmost)::

    [ text field ............ (+) ]
    [ category chip ][ priority chip ]

The bar owns its parts and its internal tab order; the window only reads the
chosen category/priority and reacts to ``task_submitted``. While a past day
is shown the whole bar is locked: dimmed, disabled, with its own hint.
"""

from __future__ import annotations

from typing import Optional, Sequence, cast

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from app.core.models import Category
from app.ui.category_icons import CategoryIconProvider
from app.ui.styles.add_task_bar_style import (
    BAR_GAP,
    INPUT_GAP,
    INPUT_HEIGHT,
    INPUT_PAD_LEFT,
    INPUT_PAD_RIGHT,
    LOCK_OPACITY,
)
from app.ui.widgets.add_task_bar.plus_button import PlusButton
from app.ui.widgets.category_chip import CategoryChip
from app.ui.widgets.priority_chip import PriorityChip
from app.ui.widgets.task_input import PLACEHOLDER_TEXT, TaskInput

__all__ = ["AddTaskBar"]

LOCKED_PLACEHOLDER_TEXT = "لا يمكن الإضافة ليوم سابق"


class AddTaskBar(QWidget):
    """Input row + category chip + priority chip."""

    #: A non-blank task was submitted (Enter or the plus button).
    task_submitted = Signal(str)

    def __init__(
        self,
        categories: Sequence[Category],
        icon_provider: CategoryIconProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("addTaskBar")

        self._input = TaskInput(self)
        self._plus = PlusButton(self)
        self._category_chip = CategoryChip(categories, self, icon_provider)
        self._priority_chip = PriorityChip(self)

        self._input.task_submitted.connect(self._submit)
        self._plus.clicked.connect(lambda: self._submit(self._input.text()))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BAR_GAP)
        layout.addWidget(self._build_input_row())
        layout.addLayout(self._build_chip_row())

        QWidget.setTabOrder(self._input, self._plus)
        QWidget.setTabOrder(self._plus, self._category_chip)
        QWidget.setTabOrder(self._category_chip, self._priority_chip)

    # -- Construction -------------------------------------------------------

    def _build_input_row(self) -> QFrame:
        row = QFrame(self)
        row.setObjectName("taskInputRow")
        row.setFixedHeight(INPUT_HEIGHT)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(INPUT_PAD_LEFT, 0, INPUT_PAD_RIGHT, 0)
        layout.setSpacing(INPUT_GAP)
        layout.addWidget(self._input, 1)
        layout.addWidget(self._plus, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    def _build_chip_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BAR_GAP)
        layout.addWidget(self._category_chip)
        layout.addWidget(self._priority_chip)
        layout.addStretch(1)  # chips keep their natural width
        return layout

    # -- Parts the window reads ---------------------------------------------

    @property
    def input_field(self) -> TaskInput:
        return self._input

    @property
    def category_chip(self) -> CategoryChip:
        return self._category_chip

    @property
    def priority_chip(self) -> PriorityChip:
        return self._priority_chip

    def text(self) -> str:
        return self._input.text()

    def clear(self) -> None:
        self._input.clear()

    def focus_input(self) -> None:
        self._input.setFocus()

    # -- Submitting ---------------------------------------------------------

    def _submit(self, text: str) -> None:
        """Emit a non-blank task; a blank attempt just returns to the field."""
        if text.strip():
            self.task_submitted.emit(text)
        else:
            self._input.setFocus()

    # -- Locked (past day) ---------------------------------------------------

    def set_locked(self, locked: bool) -> None:
        """Dim and disable the whole bar (past day), or restore it."""
        self.setEnabled(not locked)
        self._input.setPlaceholderText(
            LOCKED_PLACEHOLDER_TEXT if locked else PLACEHOLDER_TEXT
        )
        if locked:
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(LOCK_OPACITY)
            self.setGraphicsEffect(effect)
        else:
            self.setGraphicsEffect(cast(QGraphicsEffect, None))