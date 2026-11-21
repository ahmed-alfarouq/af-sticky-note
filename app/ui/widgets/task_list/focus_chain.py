"""Keyboard tab chain through the task rows."""

from __future__ import annotations

from typing import List, Optional, Sequence

from PySide6.QtWidgets import QWidget

from app.ui.widgets.task_item import TaskItem

__all__ = ["build_focus_sequence", "apply_tab_order"]


def _row_widgets(rows: Sequence[TaskItem]) -> List[QWidget]:
    return [widget for row in rows for widget in row.focus_widgets()]


def build_focus_sequence(
    open_rows: Sequence[TaskItem],
    done_rows: Sequence[TaskItem],
    header: QWidget,
) -> List[QWidget]:
    """Focusable widgets in visual order.

    Open rows, then the group header (only when completed rows exist), then
    completed rows. Hidden rows are skipped by Qt traversal itself.
    """
    sequence = _row_widgets(open_rows)
    if done_rows:
        sequence.append(header)
        sequence.extend(_row_widgets(done_rows))
    return sequence


def apply_tab_order(
    sequence: Sequence[QWidget],
    before: Optional[QWidget],
    after: Optional[QWidget],
) -> None:
    """Link ``before -> sequence -> after`` with ``QWidget.setTabOrder``.

    With no rows, ``before`` links straight to ``after`` when both exist.
    """
    chain: List[QWidget] = list(sequence)

    if chain:
        if before is not None:
            chain.insert(0, before)
        if after is not None:
            chain.append(after)
    elif before is not None and after is not None:
        chain = [before, after]

    for current, following in zip(chain, chain[1:]):
        QWidget.setTabOrder(current, following)
