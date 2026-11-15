"""The settings screen's sections, and what each control does.

Working: calendar, first day of the week, default category and priority,
daily message, pin window, and start with Windows. The theme and automatic
archive controls only animate for now; they are not connected to anything.
"""

from __future__ import annotations

import logging
from typing import Callable, List, Sequence

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox, QWidget

from app.core.models import TaskPriority
from app.infrastructure.clock import ARABIC_WEEKDAYS
from app.ui.category_presentation import category_label
from app.ui.date_presentation import CalendarKind
from app.ui.priority_presentation import priority_label
from app.ui.settings_presentation import weekday_sheet_options
from app.ui.sheet_presentation import SheetOption, category_sheet_options, priority_sheet_options
from app.ui.widgets.option_sheet import OptionSheet
from app.ui.widgets.settings.context import SettingsContext
from app.ui.widgets.settings.segmented_control import SegmentedControl
from app.ui.widgets.settings.settings_rows import ChoiceRow, SettingsRow, SettingsSection
from app.ui.widgets.settings.toggle_switch import ToggleSwitch

__all__ = ["SettingsContent"]

logger = logging.getLogger(__name__)

#: Segment order of the calendar control.
CALENDARS = (CalendarKind.HIJRI, CalendarKind.GREGORIAN)

STARTUP_TITLE = "تشغيل مع بدء تشغيل Windows"
STARTUP_DESCRIPTION = "تشغيل تطبيق الملاحظة اليومية تلقائياً عند تسجيل الدخول إلى Windows"


def _switch_row(title: str, on: bool = False, hint: str = "") -> tuple[SettingsRow, ToggleSwitch]:
    switch = ToggleSwitch()
    switch.setAccessibleName(title)
    switch.set_checked_silently(on, animate=False)
    return SettingsRow(title, switch, hint), switch


def _segment_row(title: str, labels: List[str]) -> tuple[SettingsRow, SegmentedControl]:
    control = SegmentedControl(labels)
    control.setAccessibleName(title)
    return SettingsRow(title, control), control


class SettingsContent(QObject):
    """Builds the sections and keeps their controls in step with the app."""

    def __init__(
        self,
        context: SettingsContext,
        option_sheet: OptionSheet,
        dialog_parent: QWidget,
    ) -> None:
        super().__init__(dialog_parent)
        self._context = context
        self._preferences = context.preferences
        self._option_sheet = option_sheet
        self._dialog_parent = dialog_parent

        self.sections: List[SettingsSection] = [
            self._calendar_section(),
            self._tasks_section(),
            self._display_section(),
        ]

    # -- Sections -----------------------------------------------------------

    def _calendar_section(self) -> SettingsSection:
        calendar_row, self._calendar_control = _segment_row("التقويم الأساسي", ["هجري", "ميلادي"])
        self._calendar_control.selection_changed.connect(self._on_calendar_selected)

        self._week_row = ChoiceRow("أول يوم في الأسبوع")
        self._week_row.clicked.connect(self._choose_week_start)

        return SettingsSection("التقويم", [calendar_row, self._week_row])

    def _tasks_section(self) -> SettingsSection:
        self._category_row = ChoiceRow("التصنيف الافتراضي")
        self._category_row.clicked.connect(self._choose_default_category)

        self._priority_row = ChoiceRow("الأولوية الافتراضية")
        self._priority_row.clicked.connect(self._choose_default_priority)

        archive_row, _ = _switch_row("أرشفة المكتملة تلقائياً", on=True, hint="بعد يوم واحد")  # UI only

        return SettingsSection("المهام", [self._category_row, self._priority_row, archive_row])

    def _display_section(self) -> SettingsSection:
        theme_row, _ = _segment_row("المظهر", ["داكن", "فاتح", "تلقائي"])  # UI only

        daily_row, self._daily_switch = _switch_row("الرسالة اليومية")
        self._daily_switch.toggled.connect(self._preferences.set_daily_message)

        pin_row, self._pin_switch = _switch_row("تثبيت النافذة")
        self._pin_switch.toggled.connect(self._on_pin_toggled)

        startup_row, self._startup_switch = _switch_row(STARTUP_TITLE)
        self._startup_switch.setAccessibleDescription(STARTUP_DESCRIPTION)
        self._startup_switch.toggled.connect(self._on_startup_toggled)

        return SettingsSection("العرض", [theme_row, daily_row, pin_row, startup_row])

    # -- Showing the current state -------------------------------------------

    def sync(self) -> None:
        """Show the saved state in every working control (no animation, no signals)."""
        self._calendar_control.set_current_index(CALENDARS.index(self._preferences.calendar))
        self._refresh_choice_values()
        self._daily_switch.set_checked_silently(self._preferences.daily_message, animate=False)
        self.sync_pin(animate=False)
        self._sync_startup()

    def sync_pin(self, *, animate: bool) -> None:
        self._pin_switch.set_checked_silently(self._context.is_pinned(), animate=animate)

    def _refresh_choice_values(self) -> None:
        self._week_row.set_value(ARABIC_WEEKDAYS[self._preferences.week_start])
        self._category_row.set_value(self._category_name(self._preferences.default_category_id))
        self._priority_row.set_value(priority_label(self._preferences.default_priority))

    def _category_name(self, category_id: str) -> str:
        for category in self._context.categories:
            if category.id == category_id:
                return category_label(category)
        return category_id

    # -- Calendar and defaults -----------------------------------------------

    def _on_calendar_selected(self, index: int) -> None:
        self._preferences.set_calendar(CALENDARS[index])

    def _choose_week_start(self) -> None:
        self._pick(
            "أول يوم في الأسبوع",
            weekday_sheet_options(),
            str(self._preferences.week_start),
            self._week_row,
            lambda key: self._preferences.set_week_start(int(key)),
        )

    def _choose_default_category(self) -> None:
        self._pick(
            "التصنيف الافتراضي",
            category_sheet_options(self._context.categories),
            self._preferences.default_category_id,
            self._category_row,
            self._preferences.set_default_category_id,
        )

    def _choose_default_priority(self) -> None:
        self._pick(
            "الأولوية الافتراضية",
            priority_sheet_options(),
            self._preferences.default_priority.value,
            self._priority_row,
            lambda key: self._preferences.set_default_priority(TaskPriority(key)),
        )

    def _pick(
        self,
        title: str,
        options: Sequence[SheetOption],
        selected_key: str,
        row: ChoiceRow,
        apply_choice: Callable[[str], None],
    ) -> None:
        """Let the user choose from ``options``, then save and show the choice."""
        if not options:
            return

        def chosen(key: str) -> None:
            apply_choice(key)
            self._refresh_choice_values()

        self._option_sheet.present(
            title, options, selected_key, on_chosen=chosen, return_focus=row
        )

    # -- Pin window ------------------------------------------------------------

    def _on_pin_toggled(self, pinned: bool) -> None:
        if not self._context.set_pinned(pinned):
            # The window reported why; slide the switch back to the real state.
            self.sync_pin(animate=True)

    # -- Start with Windows ------------------------------------------------------

    def _sync_startup(self) -> None:
        try:
            enabled = self._context.startup_manager.is_enabled()
        except Exception as exc:
            logger.error("Failed to query startup manager state: %s", exc)
            enabled = False
        self._startup_switch.set_checked_silently(enabled, animate=False)

    def _on_startup_toggled(self, checked: bool) -> None:
        manager = self._context.startup_manager
        try:
            success = manager.enable() if checked else manager.disable()
            if not success:
                self._revert_startup(checked)
                QMessageBox.warning(
                    self._dialog_parent,
                    "خطأ في الإعدادات",
                    "تعذر تعديل إعداد بدء التشغيل التلقائي مع Windows.",
                )
        except Exception as exc:
            logger.error("Error setting startup to %s: %s", checked, exc)
            self._revert_startup(checked)
            QMessageBox.warning(
                self._dialog_parent,
                "خطأ في الإعدادات",
                f"حدث خطأ أثناء حفظ الإعداد:\n{exc}",
            )

    def _revert_startup(self, attempted: bool) -> None:
        """Slide the switch back to the state before the failed change."""
        self._startup_switch.set_checked_silently(not attempted, animate=True)