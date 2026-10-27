"""Visual representation and interaction for an individual task item."""
from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Sequence

from PySide6.QtCore import QEvent, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QContextMenuEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QSizePolicy,
    QWidget,
)

from app.core.models import Category, Task, TaskPriority
from app.ui.category_icons import CategoryIconProvider
from app.ui.category_presentation import category_icon_key, category_label, sort_categories
from app.ui.priority_presentation import PRIORITY_LABELS, PRIORITY_ORDER
from app.ui.widgets.icon_button import IconButton

#: Fixed metadata geometry (Phase 7C). The two indicators share one small
#: footprint so rows never jump between priorities or categories.
CATEGORY_ICON_BOX = 22
CATEGORY_ICON_PIXMAP = 18
PRIORITY_DOT_BOX = 12

#: Checkbox press animation (v3 §1.3/§7.3): the 16 px icon shrinks toward
#: 88% and back over 150 ms. Only the icon paints smaller -- the 32x32 hit
#: area, layout, and row geometry never change.
PRESS_ANIMATION_MS = 150
PRESS_ICON_SIZE = 16
PRESSED_ICON_SIZE = 14

#: Invisible break opportunity for display text (Phase 7C.1). QLabel wraps
#: at whitespace only, so long unbreakable tokens (URLs, paths, repeated
#: characters) would paint past the label edge and clip at the row boundary.
#: Inserting U+200B after breakable punctuation and inside overlong runs
#: gives Qt legal break points *without changing the stored task text*:
#: the model, services, and database never see these characters.
_ZERO_WIDTH_SPACE = "\u200b"
_BREAK_AFTER_CHARS = frozenset("/?\\-_.,;:?&=%#+~")
_MAX_UNBROKEN_RUN = 20

def to_display_text(raw_text: str) -> str:
    """Add invisible wrap opportunities to overlong/unbreakable runs.

    Plain spaced text is returned byte-identical; only punctuation breaks
    and runs longer than ``_MAX_UNBROKEN_RUN`` non-space characters gain
    zero-width spaces. Purely presentational -- never persisted.
    """
    if not raw_text:
        return raw_text
    out: List[str] = []
    run = 0
    for char in raw_text:
        if char.isspace():
            run = 0
            out.append(char)
            continue
        out.append(char)
        run += 1
        if char in _BREAK_AFTER_CHARS:
            out.append(_ZERO_WIDTH_SPACE)
            run = 0
        elif run >= _MAX_UNBROKEN_RUN:
            out.append(_ZERO_WIDTH_SPACE)
            run = 0
    return "".join(out)


def from_display_text(display_text: str) -> str:
    """Recover the stored task text from a display string."""
    return display_text.replace(_ZERO_WIDTH_SPACE, "")


class _TaskTextLabel(QLabel):
    """Task-text label that may always shrink to fit its row.

    QLabel's default minimumSizeHint is the widest unwrappable word, so one
    long token would force the whole TaskList past narrow viewports even
    though the list forbids horizontal scrolling by design (the overflow is
    then clipped and unreachable, potentially hiding row controls). Wrapping
    owns legibility, so the width floor stays compressible while height
    still comes from heightForWidth during layout.
    """

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(0, hint.height())


class TaskItem(QFrame):
    """A single task row containing a checkbox, task text label, and context menu."""

    completed_toggled = Signal(int, bool)  # task_id, is_completed
    edit_requested = Signal(int)           # task_id
    delete_requested = Signal(int)         # task_id
    priority_change_requested = Signal(int, object)  # task_id, TaskPriority
    category_change_requested = Signal(int, str)  # task_id, category_id
    inline_edit_committed = Signal(int, str)  # task_id, trimmed new text

    def __init__(
        self,
        task: Task,
        parent: Optional[QWidget] = None,
        categories: Sequence[Category] = (),
        icon_provider: Optional[CategoryIconProvider] = None,
    ) -> None:
        super().__init__(parent)
        self.task_id = task.id
        self.setObjectName("taskItemFrame")
        self._task = task
        self._categories: List[Category] = list(categories)
        self._icon_provider = icon_provider
        # Interaction state before any widget (event filters installed during
        # _init_ui may fire synchronously, e.g. via style polish).
        self._edit_field: Optional[QLineEdit] = None
        self._hovered = False
        self._press_animation: Optional[QPropertyAnimation] = None
        self._init_ui(task)

    def _init_ui(self, task: Task) -> None:
        # Row order (RTL: first added renders rightmost):
        #   [completion] [expanding text] [category icon] [priority dot]
        # Text owns all flexible space; both metadata widgets are fixed-size
        # so rows align and never resize between priorities/categories.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self._checkbox = QCheckBox(self)
        self._checkbox.setChecked(task.is_completed)
        self._checkbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._checkbox.setAccessibleName(task.text)
        # Fixed 32x32 hit area (v3 §7.2): the icon is centered inside it and
        # never participates in layout, so rows keep stable geometry while
        # the press animation and focus ring play inside the same box.
        self._checkbox.setFixedSize(32, 32)
        # Completion art (Issue 7): the native indicator box is collapsed
        # to zero by QSS, and the real 16px right-icon asset is shown as
        # the button icon instead -- checked state via QIcon On/Off modes,
        # so checking can never recolor any border. Falls back to no icon
        # (native empty box area) when the provider/asset is unavailable.
        self._checkbox.setObjectName("taskCheckBox")
        completion_icon = QIcon()
        if self._icon_provider is not None:
            asset = self._icon_provider.icon_for_key("right-icon")
            if not asset.isNull():
                blank = QPixmap(16, 16)
                blank.fill(Qt.GlobalColor.transparent)
                completion_icon.addPixmap(blank, QIcon.Mode.Normal, QIcon.State.Off)
                completion_icon.addPixmap(
                    asset.pixmap(16, 16), QIcon.Mode.Normal, QIcon.State.On
                )
        if not completion_icon.isNull():
            self._checkbox.setIcon(completion_icon)
            self._checkbox.setIconSize(QSize(16, 16))
        self._checkbox.toggled.connect(self._on_toggled)

        self._text_label = _TaskTextLabel(to_display_text(task.text), self)
        self._text_label.setWordWrap(True)
        # No explicit horizontal alignment: under the app-level RightToLeft
        # direction a QLabel's default already anchors text to the right
        # edge, whereas any explicit AlignRight/AlignTrailing (0x0002)
        # mirrors it onto the left edge -- the defect the date header fixed
        # by deleting its setAlignment calls.  The #taskTextLabel QSS rule
        # still governs while the stylesheet parses; this call only
        # duplicated that value and corrupted the no-stylesheet fallback.
        self._text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._text_label.setToolTip(task.text)
        # The title is a tab stop (v3 §11): Enter/F2 or double-click starts
        # inline editing, handled through the event filter below.
        self._text_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._text_label.installEventFilter(self)
        self._update_label_style(task.is_completed)

        self.setAccessibleName(f"مهمة: {task.text}")
        status_text = "مكتملة" if task.is_completed else "غير مكتملة"
        self.setAccessibleDescription(f"الحالة: {status_text}")

        layout.addWidget(self._checkbox)
        layout.addWidget(self._text_label, 1)

        self._category_icon = QLabel(self)
        self._category_icon.setObjectName("taskCategoryIcon")
        self._category_icon.setFixedSize(CATEGORY_ICON_BOX, CATEGORY_ICON_BOX)
        self._category_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._category_icon.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._category_icon)

        self._priority_dot = QLabel(self)
        self._priority_dot.setFixedSize(PRIORITY_DOT_BOX, PRIORITY_DOT_BOX)
        self._priority_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._priority_dot.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._priority_dot)

        # Hover-revealed delete control (v3 §7.6): icon-only trash button,
        # invisible (opacity 0, space reserved) until the row is hovered or
        # holds keyboard focus. Clicking deletes via the existing service
        # path; it never toggles completion or starts an edit.
        self._delete_btn = IconButton(
            "trash", parent=self, button_size=32, size=18,
        )
        self._delete_btn.setObjectName("rowDeleteButton")
        self._delete_btn.setAccessibleName("حذف المهمة")
        self._delete_btn.setToolTip("حذف المهمة")
        self._delete_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._delete_opacity = QGraphicsOpacityEffect(self._delete_btn)
        self._delete_opacity.setOpacity(0.0)
        self._delete_btn.setGraphicsEffect(self._delete_opacity)
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self._delete_btn)

        # Inline-edit state (v3 §7.4): at most one transient field per row.
        # (_edit_field/_hovered are initialized in __init__.)
        for child in (self._checkbox, self._text_label, self._category_icon,
                      self._priority_dot, self._delete_btn):
            child.installEventFilter(self)

        self._refresh_category_icon()
        self._refresh_priority_dot()
        self._update_delete_visibility()

    @property
    def priority(self) -> TaskPriority:
        """The priority this row currently shows."""
        return self._task.priority

    @property
    def task_text(self) -> str:
        """The task's stored text (display break opportunities stripped)."""
        return from_display_text(self._text_label.text())

    @property
    def category_id(self) -> str:
        """The category id this row currently carries."""
        return self._task.category_id

    def set_categories(
        self,
        categories: Sequence[Category],
        icon_provider: Optional[CategoryIconProvider] = None,
    ) -> None:
        """Refresh the category choices offered by the context menu."""
        self._categories = list(categories)
        if icon_provider is not None:
            self._icon_provider = icon_provider
        # Names/icons may have changed; keep the row's icon truthful.
        if hasattr(self, "_category_icon"):
            self._refresh_category_icon()

    def update_task_category(self, category_id: str) -> None:
        """Refresh the row's carried category without recreating the task.

        Only the category field changes: the record keeps its id, day, source
        task, completion state, text, position and priority. The category
        icon updates in place.
        """
        self._task = replace(self._task, category_id=category_id)
        self._refresh_category_icon()

    def _category_by_id(self, category_id: str) -> Optional[Category]:
        for category in self._categories:
            if category.id == category_id:
                return category
        return None

    def _refresh_category_icon(self) -> None:
        """Show the task's category icon (tooltip carries the Arabic name).

        Icons come from the shared provider cache only -- no filesystem
        access here and none in paint paths. Without a provider the icon
        stays empty rather than inventing artwork.
        """
        category = self._category_by_id(self._task.category_id)
        label = category_label(category) if category is not None else self._task.category_id
        self._category_icon.setToolTip(label)
        self._category_icon.setAccessibleName(f"فئة المهمة: {label}")
        if self._icon_provider is None:
            self._category_icon.setPixmap(QPixmap())
            return
        key = category_icon_key(category) if category is not None else self._task.category_id
        mode = QIcon.Mode.Disabled if self._task.is_completed else QIcon.Mode.Normal
        self._category_icon.setPixmap(
            self._icon_provider.icon_for_key(key).pixmap(
                CATEGORY_ICON_PIXMAP, CATEGORY_ICON_PIXMAP, mode
            )
        )

    def _refresh_priority_dot(self) -> None:
        """Show the compact priority indicator (approved R-rows-c mapping).

        HIGH is a solid amber-red dot, LOW a hollow amber ring, MEDIUM
        paints nothing (its fixed box is kept so rows never shift). Labels,
        tooltips, and accessible names keep the truthful stored level;
        completed rows mute every level to the quiet gray.
        """
        if self._task.priority == TaskPriority.HIGH:
            self._priority_dot.setObjectName("priorityDotHigh")
        elif self._task.priority == TaskPriority.LOW:
            self._priority_dot.setObjectName("priorityDotLow")
        else:
            self._priority_dot.setObjectName("priorityDotMedium")
        self._priority_dot.setProperty("completed", self._task.is_completed)
        label = PRIORITY_LABELS[self._task.priority]
        self._priority_dot.setToolTip(f"الأولوية: {label}")
        self._priority_dot.setAccessibleName(f"أولوية المهمة: {label}")
        self._priority_dot.style().unpolish(self._priority_dot)
        self._priority_dot.style().polish(self._priority_dot)

    def update_task_priority(self, priority: TaskPriority) -> None:
        """Refresh the row for a new priority without recreating the task.

        Only the priority field changes: the record keeps its id, day, source
        task, completion state, text and position.
        """
        self._task = replace(self._task, priority=priority)
        self._refresh_priority_dot()

    def _on_toggled(self, checked: bool) -> None:
        self._task = replace(self._task, is_completed=checked)
        self._update_label_style(checked)
        self._refresh_category_icon()
        self._refresh_priority_dot()
        status_text = "مكتملة" if checked else "غير مكتملة"
        self.setAccessibleDescription(f"الحالة: {status_text}")
        self._play_press_animation()
        self.completed_toggled.emit(self.task_id, checked)

    def _play_press_animation(self) -> None:
        """Shrink the checkbox icon toward 88% and restore it (v3 §7.3).

        One bounded 150 ms run per press; an in-flight run restarts from the
        current size so rapid clicks never stick mid-scale. Parented to the
        row (dies with it); layout and hit area are untouched.
        """
        previous = self._press_animation
        if previous is not None:
            previous.stop()
        animation = QPropertyAnimation(self._checkbox, b"iconSize", self)
        animation.setDuration(PRESS_ANIMATION_MS)
        animation.setStartValue(self._checkbox.iconSize())
        animation.setEndValue(QSize(PRESSED_ICON_SIZE, PRESSED_ICON_SIZE))
        animation.finished.connect(self._restore_press_icon)
        self._press_animation = animation
        animation.start()

    def _restore_press_icon(self) -> None:
        self._checkbox.setIconSize(QSize(PRESS_ICON_SIZE, PRESS_ICON_SIZE))

    def _update_label_style(self, is_completed: bool) -> None:
        if is_completed:
            self._text_label.setObjectName("taskTextLabelCompleted")
        else:
            self._text_label.setObjectName("taskTextLabel")
        self._text_label.style().unpolish(self._text_label)
        self._text_label.style().polish(self._text_label)

    def set_completed_silently(self, is_completed: bool) -> None:
        """Update checkbox state without re-emitting toggled signal."""
        self._task = replace(self._task, is_completed=is_completed)
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(is_completed)
        self._update_label_style(is_completed)
        self._refresh_category_icon()
        self._refresh_priority_dot()
        self._checkbox.blockSignals(False)

    def update_task_text(self, new_text: str) -> None:
        """Update visible task text."""
        self._cancel_inline_edit()
        self._text_label.setText(to_display_text(new_text))
        self._text_label.setToolTip(new_text)
        # Keep the carried Task in step so a later priority update cannot
        # resurrect the old text.
        self._task = replace(self._task, text=new_text)
        self.setAccessibleName(f"مهمة: {new_text}")
        self._checkbox.setAccessibleName(new_text)

    # ------------------------------------------------------------------
    # Inline title editing (v3 §7.4, title only)
    # ------------------------------------------------------------------
    def is_editing_inline(self) -> bool:
        """Whether the transient edit field is currently open."""
        return self._edit_field is not None

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        """Drive hover visibility, edit triggers, and edit-field keys."""
        event_type = event.type()
        if watched is self._text_label:
            if event_type == QEvent.Type.MouseButtonDblClick:
                self._start_inline_edit()
                return True
            if event_type == QEvent.Type.KeyPress:
                key = event.key()
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F2):
                    self._start_inline_edit()
                    return True
        if watched is self._edit_field and event_type == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._cancel_inline_edit()
                return True
        if event_type == QEvent.Type.Enter:
            self._hovered = True
            self._update_delete_visibility()
        elif event_type == QEvent.Type.Leave:
            self._hovered = False
            self._update_delete_visibility()
        elif event_type in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self._update_delete_visibility()
        return super().eventFilter(watched, event)

    def _start_inline_edit(self) -> None:
        """Swap the title label for an edit field with the text selected."""
        if self._edit_field is not None or self.task_id is None:
            return
        field = QLineEdit(self)
        field.setObjectName("taskTitleEdit")
        field.setText(self._task.text)
        field.setMaxLength(200)
        field.setFixedHeight(26)
        field.setAlignment(Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter)
        glow = QGraphicsDropShadowEffect(field)
        glow.setColor(QColor(79, 124, 172, 64))
        glow.setBlurRadius(6)
        glow.setOffset(0, 0)
        field.setGraphicsEffect(glow)
        field.selectAll()
        field.editingFinished.connect(self._commit_inline_edit)
        field.installEventFilter(self)
        layout = self.layout()
        assert layout is not None
        index = layout.indexOf(self._text_label)
        layout.removeWidget(self._text_label)
        layout.insertWidget(index, field, 1)
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
        self._finish_inline_edit()
        if not cleaned or cleaned == self._task.text:
            self._text_label.setFocus()
            return
        self.inline_edit_committed.emit(task_id, cleaned)
        self._text_label.setFocus()

    def _cancel_inline_edit(self) -> None:
        """Close the edit field, restoring focus to the title."""
        if self._edit_field is None:
            return
        self._finish_inline_edit()
        self._text_label.setFocus()

    def _finish_inline_edit(self) -> None:
        field = self._edit_field
        self._edit_field = None
        if field is not None:
            field.removeEventFilter(self)
            layout = self.layout()
            if layout is not None:
                index = layout.indexOf(field)
                layout.removeWidget(field)
                layout.insertWidget(max(0, index), self._text_label, 1)
            field.deleteLater()
        self._text_label.show()

    # ------------------------------------------------------------------
    # Hover-revealed delete (v3 §7.6)
    # ------------------------------------------------------------------
    def _focus_within(self) -> bool:
        """Whether the row or any of its focusable children holds focus."""
        widgets = [self, self._checkbox, self._text_label, self._delete_btn]
        if self._edit_field is not None:
            widgets.append(self._edit_field)
        return any(widget.hasFocus() for widget in widgets)

    def _update_delete_visibility(self) -> None:
        """Show the delete control on hover/focus-within, hide otherwise.

        Local opacity switch only: no relayout, no signals, no writes.
        """
        self._delete_opacity.setOpacity(1.0 if (self._hovered or self._focus_within()) else 0.0)

    def _on_delete_clicked(self) -> None:
        if self.task_id is not None:
            self.delete_requested.emit(self.task_id)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show context menu for editing, changing category/priority, or deleting."""
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        edit_action = QAction("تعديل المهمة", menu)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.task_id))
        menu.addAction(edit_action)

        # Category submenu: active categories only, current one checked.
        # Omitted entirely when the item carries no category choices, so
        # pre-category call sites see the exact historical menu.
        visible_categories = [c for c in sort_categories(self._categories) if c.is_active]
        if visible_categories:
            category_menu = QMenu("الفئة", menu)
            category_menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            category_group = QActionGroup(menu)
            category_group.setExclusive(True)

            for category in visible_categories:
                action = QAction(category_label(category), category_menu)
                if self._icon_provider is not None:
                    action.setIcon(self._icon_provider.icon_for_category(category))
                action.setCheckable(True)
                action.setChecked(category.id == self._task.category_id)
                action.setData(category.id)
                action.triggered.connect(
                    lambda checked=False, cid=category.id: self.category_change_requested.emit(
                        self.task_id, cid
                    )
                )
                category_group.addAction(action)
                category_menu.addAction(action)

            menu.addMenu(category_menu)

        # Priority submenu: checkable actions, current priority checked.
        priority_menu = QMenu("الأولوية", menu)
        priority_menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        priority_group = QActionGroup(menu)
        priority_group.setExclusive(True)

        for priority in PRIORITY_ORDER:
            action = QAction(PRIORITY_LABELS[priority], priority_menu)
            action.setCheckable(True)
            action.setChecked(priority == self._task.priority)
            action.setData(priority)
            action.triggered.connect(
                lambda checked=False, p=priority: self.priority_change_requested.emit(
                    self.task_id, p
                )
            )
            priority_group.addAction(action)
            priority_menu.addAction(action)

        menu.addMenu(priority_menu)

        delete_action = QAction("حذف المهمة", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.task_id))
        menu.addAction(delete_action)

        menu.exec(event.globalPos())
        event.accept()
