"""Weekly reporting dashboard window (Phase 7F).

On-demand Arabic RTL dialog over the Phase 7E reporting foundation:
range presets + custom range, summary metrics, per-category cards, and a
Qt-native daily activity chart. Presentation only -- ``ReportService``
remains the sole data source; widgets never touch SQL. A report loads only
when the range changes or the dialog opens; chart repaints never re-query.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional, Tuple

from PySide6.QtCore import QDate, QSettings, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.daily_reports import DateRangeReport, validate_range
from app.core.services.report_service import ReportService
from app.infrastructure.paths import get_logo_path
from app.ui.category_icons import CategoryIconProvider
from app.ui.styles.app_style import get_application_stylesheet
from app.ui.widgets.category_card import CategoryCard
from app.ui.widgets.daily_chart import DailyChart

logger = logging.getLogger(__name__)

PRESET_THIS_WEEK = "week"
PRESET_LAST_7 = "last7"
PRESET_LAST_14 = "last14"

#: QSettings group for the dashboard (same mechanism as geometry).
DASHBOARD_SETTINGS_GROUP = "Dashboard"

__all__ = [
    "WeeklyDashboardWindow",
    "preset_range",
    "PRESET_THIS_WEEK",
    "PRESET_LAST_7",
    "PRESET_LAST_14",
    "DASHBOARD_SETTINGS_GROUP",
]


def preset_range(preset: str, today: date) -> Tuple[str, str]:
    """Inclusive ``(start_iso, end_iso)`` for a preset ending today.

    - ``week``: Monday of the current week through today (actuals only).
    - ``last7``: today minus 6 days through today.
    - ``last14``: today minus 13 days through today.
    Unknown presets raise ValueError. Pure function (no Qt) for tests.
    """
    if preset == PRESET_THIS_WEEK:
        start = today - timedelta(days=today.weekday())
    elif preset == PRESET_LAST_7:
        start = today - timedelta(days=6)
    elif preset == PRESET_LAST_14:
        start = today - timedelta(days=13)
    else:
        raise ValueError(f"Unknown dashboard preset: {preset!r}")
    return start.isoformat(), today.isoformat()


class WeeklyDashboardWindow(QDialog):
    """On-demand weekly report viewer; closing never touches the sticky note."""

    def __init__(
        self,
        report_service: ReportService,
        icon_provider: Optional[CategoryIconProvider] = None,
        initial_preset: str = PRESET_LAST_7,
        parent: Optional[QWidget] = None,
        qsettings: Optional[QSettings] = None,
    ) -> None:
        super().__init__(parent)
        self._report_service = report_service
        self._icon_provider = icon_provider
        self._settings = qsettings
        self._current_range: Tuple[str, str] = ("", "")
        self._active_preset: Optional[str] = None
        self._load_count = 0  # diagnostics: one load per range change

        self.setWindowTitle("لوحة التقارير الأسبوعية")
        self.setObjectName("dashboardWindow")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(400, 600)
        self.setMinimumSize(340, 480)

        try:
            from PySide6.QtGui import QIcon
            logo_path = get_logo_path()
            if logo_path.exists() and logo_path.is_file():
                self.setWindowIcon(QIcon(str(logo_path)))
        except Exception:
            pass

        self._init_ui()
        self.setStyleSheet(get_application_stylesheet())
        self._open_initial_range(initial_preset)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setObjectName("dashboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        content = QWidget(scroll)
        content.setObjectName("dashboardContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        scroll.setWidget(content)

        # 1. Title + selected range.
        self._title_label = QLabel("لوحة التقارير الأسبوعية", content)
        self._title_label.setObjectName("dashboardTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        self._range_label = QLabel("", content)
        self._range_label.setObjectName("dashboardRangeLabel")
        self._range_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._range_label)

        # 2. Presets + custom range.
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        self._preset_group = QButtonGroup(self)
        self._preset_group.setExclusive(True)
        self._preset_buttons = {}
        for preset, text in (
            (PRESET_THIS_WEEK, "هذا الأسبوع"),
            (PRESET_LAST_7, "آخر 7 أيام"),
            (PRESET_LAST_14, "آخر 14 يوما"),
        ):
            button = QPushButton(text, content)
            button.setObjectName("dashboardPresetButton")
            button.setCheckable(True)
            button.setProperty("preset", preset)
            button.clicked.connect(self._on_preset_clicked)
            self._preset_group.addButton(button)
            self._preset_buttons[preset] = button
            preset_row.addWidget(button)
        layout.addLayout(preset_row)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        self._start_edit = QDateEdit(content)
        self._start_edit.setObjectName("dashboardDateEdit")
        self._start_edit.setDisplayFormat("yyyy-MM-dd")
        self._start_edit.setCalendarPopup(True)
        self._end_edit = QDateEdit(content)
        self._end_edit.setObjectName("dashboardDateEdit")
        self._end_edit.setDisplayFormat("yyyy-MM-dd")
        self._end_edit.setCalendarPopup(True)
        self._apply_btn = QPushButton("عرض", content)
        self._apply_btn.setObjectName("dashboardApplyButton")
        self._apply_btn.clicked.connect(self._on_custom_apply)
        custom_row.addWidget(QLabel("من:", content))
        custom_row.addWidget(self._start_edit)
        custom_row.addWidget(QLabel("إلى:", content))
        custom_row.addWidget(self._end_edit)
        custom_row.addWidget(self._apply_btn)
        layout.addLayout(custom_row)

        # 3. Error feedback (hidden unless a load fails).
        self._error_label = QLabel("", content)
        self._error_label.setObjectName("dashboardErrorLabel")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # 4. Summary metrics.
        summary = QFrame(content)
        summary.setObjectName("dashboardSummary")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(6)
        self._stat_values = {}
        for key, caption in (
            ("total", "إجمالي"),
            ("completed", "مكتملة"),
            ("incomplete", "متبقية"),
            ("percent", "نسبة الإنجاز"),
        ):
            cell = QVBoxLayout()
            cell.setSpacing(2)
            value = QLabel("0", summary)
            value.setObjectName("dashboardStatValue")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption_label = QLabel(caption, summary)
            caption_label.setObjectName("dashboardStatLabel")
            caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.addWidget(value)
            cell.addWidget(caption_label)
            summary_layout.addLayout(cell)
            self._stat_values[key] = value
        layout.addWidget(summary)

        # 5. Category cards (rebuilt only when the range changes).
        self._cards_container = QWidget(content)
        self._cards_layout = QGridLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        layout.addWidget(self._cards_container)

        # 6. Daily chart + legend.
        legend_row = QHBoxLayout()
        legend_row.setSpacing(12)
        self._legend_done = QLabel("■ مكتملة", content)
        self._legend_done.setObjectName("dashboardLegendDone")
        self._legend_todo = QLabel("■ متبقية", content)
        self._legend_todo.setObjectName("dashboardLegendTodo")
        legend_row.addStretch(1)
        legend_row.addWidget(self._legend_done)
        legend_row.addWidget(self._legend_todo)
        layout.addLayout(legend_row)

        self._chart = DailyChart(content)
        layout.addWidget(self._chart)

        self._empty_label = QLabel("لا توجد مهام في هذه الفترة", content)
        self._empty_label.setObjectName("dashboardEmptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label)

        layout.addStretch(1)

        # 7. Close (never closes the main window).
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("إغلاق", content)
        close_btn.setObjectName("historyCloseButton")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    # ------------------------------------------------------------------
    # Range handling (one report load per change)
    # ------------------------------------------------------------------
    def _open_initial_range(self, initial_preset: str) -> None:
        """Restore the persisted range when valid, else the initial preset."""
        restored = self._read_persisted_range()
        if restored is not None:
            preset, start, end = restored
            if preset is not None:
                self._select_preset(preset)
            else:
                self._sync_custom_edits(start, end)
                self._load_range(start, end)
            return
        self._select_preset(initial_preset)

    def _read_persisted_range(self) -> Optional[Tuple[Optional[str], str, str]]:
        """Stored ``(preset, start, end)`` or None when absent/invalid.

        Reads once per dialog open; never raises (falls back to default).
        """
        if self._settings is None:
            return None
        try:
            self._settings.beginGroup(DASHBOARD_SETTINGS_GROUP)
            try:
                preset = self._settings.value("preset", PRESET_LAST_7)
                start = self._settings.value("start", "")
                end = self._settings.value("end", "")
            finally:
                self._settings.endGroup()
            if preset in (PRESET_THIS_WEEK, PRESET_LAST_7, PRESET_LAST_14):
                return (str(preset), "", "")
            # Custom ranges restore only with two valid ISO dates.
            validate_range(str(start), str(end))
            return (None, str(start), str(end))
        except Exception:
            return None

    def _persist_range(self, preset: Optional[str], start_iso: str, end_iso: str) -> None:
        """Remember the range once per successful load (no polling/reads)."""
        if self._settings is None:
            return
        try:
            self._settings.beginGroup(DASHBOARD_SETTINGS_GROUP)
            try:
                self._settings.setValue("preset", preset or "custom")
                self._settings.setValue("start", start_iso)
                self._settings.setValue("end", end_iso)
            finally:
                self._settings.endGroup()
            self._settings.sync()
        except Exception as exc:
            logger.warning("Dashboard state persistence failed: %s", exc)

    def _select_preset(self, preset: str) -> None:
        button = self._preset_buttons.get(preset)
        if button is not None:
            button.setChecked(True)
        start, end = preset_range(preset, date.today())
        self._active_preset = preset
        self._sync_custom_edits(start, end)
        self._load_range(start, end)

    def _on_preset_clicked(self) -> None:
        button = self._preset_group.checkedButton()
        if button is None:
            return
        preset = str(button.property("preset"))
        try:
            start, end = preset_range(preset, date.today())
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self._active_preset = preset
        self._sync_custom_edits(start, end)
        self._load_range(start, end)

    def _on_custom_apply(self) -> None:
        start = self._start_edit.date().toString("yyyy-MM-dd")
        end = self._end_edit.date().toString("yyyy-MM-dd")
        checked = self._preset_group.checkedButton()
        if checked is not None:
            self._preset_group.setExclusive(False)
            checked.setChecked(False)
            self._preset_group.setExclusive(True)
        self._active_preset = None
        self._load_range(start, end)

    def _sync_custom_edits(self, start_iso: str, end_iso: str) -> None:
        self._start_edit.setDate(QDate.fromString(start_iso, "yyyy-MM-dd"))
        self._end_edit.setDate(QDate.fromString(end_iso, "yyyy-MM-dd"))

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setVisible(True)

    def _load_range(self, start_iso: str, end_iso: str) -> None:
        """Load one report; invalid ranges show feedback, never crash."""
        try:
            report = self._report_service.get_range_report(start_iso, end_iso)
        except ValueError as exc:
            logger.warning("Dashboard range rejected: %s", exc)
            self._show_error(f"نطاق التاريخ غير صالح: {exc}")
            return
        except Exception as exc:  # never break the window on a load failure
            logger.error("Dashboard report failed for %s..%s: %s", start_iso, end_iso, exc)
            self._show_error("تعذر تحميل التقرير، حاول مرة أخرى")
            return
        self._load_count += 1
        self._error_label.setVisible(False)
        self._current_range = (report.start_date, report.end_date)
        self._persist_range(self._active_preset, report.start_date, report.end_date)
        self._render(report)

    def _render(self, report: DateRangeReport) -> None:
        self._range_label.setText(f"الفترة: {report.start_date} إلى {report.end_date}")
        self._stat_values["total"].setText(str(report.total_tasks))
        self._stat_values["completed"].setText(str(report.completed_tasks))
        self._stat_values["incomplete"].setText(str(report.incomplete_tasks))
        self._stat_values["percent"].setText(f"{report.completion_percentage}٪")

        # Category cards: rebuild on range change only (bounded by category count).
        while self._cards_layout.count():
            child = self._cards_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
        for index, category in enumerate(report.category_reports):
            card = CategoryCard(category, self._icon_provider, self._cards_container)
            self._cards_layout.addWidget(card, index // 2, index % 2)

        self._chart.set_data(report.daily_reports)
        self._empty_label.setVisible(report.total_tasks == 0)

    # ------------------------------------------------------------------
    # Introspection (tests / diagnostics)
    # ------------------------------------------------------------------
    def current_range(self) -> Tuple[str, str]:
        """Last successfully loaded ``(start, end)`` range."""
        return self._current_range

    def load_count(self) -> int:
        """Number of successful report loads (one per range change)."""
        return self._load_count

    def category_cards(self) -> List[CategoryCard]:
        """Current cards in layout order."""
        cards = []
        for index in range(self._cards_layout.count()):
            widget = self._cards_layout.itemAt(index).widget()
            if isinstance(widget, CategoryCard):
                cards.append(widget)
        return cards
