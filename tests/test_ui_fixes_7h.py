"""Phase 7H: minimal UI bug-fix regression tests (issues 1-7 + RTL audit).

Covers behavior (not pixels) for every fix: input alignment, list
spacing, date hierarchy, selector placement, popup sizing, priority
indicators, completion icon/border stability. Qt tests no-op when
PySide6 is unavailable, per project convention.
"""
from __future__ import annotations

from pathlib import Path

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFrame

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


def _wiring(db_connection):
    from app.core.services.category_service import CategoryService
    from app.core.services.task_service import TaskService
    from app.database.category_repository import CategoryRepository
    from app.database.day_repository import DayRepository
    from app.database.task_repository import TaskRepository
    from app.ui.category_icons import CategoryIconProvider

    task_repo = TaskRepository(db_connection)
    category_repo = CategoryRepository(db_connection)
    service = TaskService(task_repo=task_repo, category_repo=category_repo)
    category_service = CategoryService(category_repo)
    provider = CategoryIconProvider(Path(__file__).resolve().parent.parent / "assets" / "icons")
    return service, category_service, provider, DayRepository(db_connection)


_TASK_ID_COUNTER = [0]


def _make_task(text="مهمة", completed=False, position=0, task_id=None):
    from app.core.models import Task, TaskPriority

    if task_id is None:
        _TASK_ID_COUNTER[0] += 1
        task_id = _TASK_ID_COUNTER[0]
    return Task(
        id=task_id, day_id=1, text=text, is_completed=completed, position=position,
        created_at="t", updated_at="t",
        priority=TaskPriority.MEDIUM, category_id="general",
    )


# ------------------------------------------------------------ Issue 1: input

def test_task_input_alignment_is_right_and_vcenter():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_input import TaskInput

    field = TaskInput()
    assert field.alignment() == (
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    field.close()


def test_task_input_inherits_rtl_without_own_assignment():
    if _skip_without_qt():
        return
    _qt_app()
    from PySide6.QtWidgets import QWidget
    from app.ui.widgets.task_input import TaskInput

    parent = QWidget()
    parent.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    field = TaskInput(parent=parent)
    assert field.layoutDirection() == Qt.LayoutDirection.RightToLeft
    parent.close()


def test_task_input_cursor_starts_right_when_empty():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_input import TaskInput

    field = TaskInput()
    field.resize(260, 40)
    field.show()
    QApplication.instance().processEvents()
    assert field.cursorRect().center().x() > field.width() // 2
    field.close()


def test_task_input_text_roundtrip_and_submit():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.task_input import TaskInput

    field = TaskInput()
    submitted = []
    field.task_submitted.connect(submitted.append)
    for text in ("مهمة عربية", "English task", "مهمة mixed 123",
                 "https://example.com/x", ""):
        field.setText(text)
        assert field.text() == text  # never reversed or mangled
        field.selectAll()
        assert field.selectedText() == text
        field._on_return_pressed()
    assert submitted == ["مهمة عربية", "English task", "مهمة mixed 123",
                         "https://example.com/x", ""]
    field.close()


# ------------------------------------------------------------ Issue 2: spacing

def _make_list():
    from app.ui.widgets.task_list import TaskList

    listing = TaskList()
    listing.resize(340, 400)
    listing.show()
    QApplication.instance().processEvents()
    return listing


def test_two_tasks_stack_from_top_without_gap():
    if _skip_without_qt():
        return
    _qt_app()
    listing = _make_list()
    try:
        listing.set_tasks([_make_task("one", position=0), _make_task("two", position=1)])
        QApplication.instance().processEvents()
        items = [listing._layout.itemAt(i).widget()
                 for i in range(listing._layout.count() - 1)]
        assert len(items) == 2
        assert items[0].y() == 4  # container top margin: no gap above
        assert items[1].y() == items[0].y() + items[0].height() + 8
    finally:
        listing.close()


def test_toggle_delete_and_clear_reflow_without_gaps():
    if _skip_without_qt():
        return
    _qt_app()
    listing = _make_list()
    try:
        t1 = _make_task("one", position=0, task_id=1)
        t2 = _make_task("two", position=1, task_id=2)
        listing.set_tasks([t1, t2])
        QApplication.instance().processEvents()

        listing._items[1].set_completed_silently(True)
        listing.refresh_task_order()
        QApplication.instance().processEvents()
        first = listing._layout.itemAt(0).widget()
        assert first.task_id == 2 and first.y() == 4

        listing._items[1].set_completed_silently(False)
        listing.refresh_task_order()
        QApplication.instance().processEvents()
        assert listing._layout.itemAt(0).widget().task_id == 1

        listing.remove_task(2)
        QApplication.instance().processEvents()
        assert listing._layout.itemAt(0).widget().y() == 4
        assert listing._layout.count() == 2  # row + stretch only

        listing.set_tasks([])
        QApplication.instance().processEvents()
        assert listing._layout.count() == 1  # stretch only, no stale space
        assert listing._section_label.isHidden()
    finally:
        listing.close()


# ------------------------------------------------------------ Issue 3: date header

def test_date_header_three_line_hierarchy_and_geometry():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.date_header import DateHeaderWidget

    header = DateHeaderWidget("2026-10-10")  # Saturday
    header.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    header.resize(340, 80)
    header.show()
    QApplication.instance().processEvents()
    try:
        assert header._day_number.text() == "10"
        assert header._weekday_label.text() == "السبت"
        assert "هـ" in header._hijri_label.text()
        assert header._gregorian_label.text() == "أكتوبر 2026"
        # Physical RTL order: day number rightmost, ring leftmost.
        assert header._day_number.x() > header._weekday_label.x()
        assert header._ring.x() < header._weekday_label.x()
        # Required vertical order: weekday, Hijri, Gregorian.
        assert header._weekday_label.y() < header._hijri_label.y()
        assert header._hijri_label.y() < header._gregorian_label.y()
    finally:
        header.close()


# ------------------------------------------------------------ Issue 4: dock layout

def _make_window(service, category_service, provider, day):
    from unittest.mock import MagicMock

    from app.ui.windows.main_window import MainWindow

    return MainWindow(
        day=day, quote_text=day.quote_text, task_service=service,
        on_exit_requested=MagicMock(), category_service=category_service,
        icon_provider=provider,
    )


def test_selectors_outside_input_card_on_its_left(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-10")
    window = _make_window(service, category_service, provider, day)
    try:
        # Mirror production, where main() sets app-global RTL.
        window.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        window.resize(380, 560)
        window.show()
        QApplication.instance().processEvents()
        dock = window.findChild(QFrame, "taskInputDock")
        card = window.findChild(QFrame, "taskInputCard")
        assert dock is not None and card is not None
        # Card holds exactly input + add button.
        assert window._task_input.parent() is card
        assert window._add_btn.parent() is card
        # Selectors are direct dock children, outside the card...
        assert window._category_selector.parent() is dock
        assert window._priority_selector.parent() is dock
        # ...on the card's physical left side (RTL: smaller x).
        card_geo = card.geometry()
        cat_geo = window._category_selector.geometry()
        pri_geo = window._priority_selector.geometry()
        # Same dock row: shared parent layout, no drift.
        assert window._priority_selector.parent() is window._category_selector.parent()
        assert cat_geo.right() <= card_geo.left()
        assert pri_geo.right() <= cat_geo.left()
        # Values and submission still work through the new structure.
        window._category_selector.set_category("work")
        window._task_input.setText("مهمة")
        window._on_add_button_clicked()
        tasks = service.get_today_tasks(day.id)
        assert [(t.text, t.category_id) for t in tasks] == [("مهمة", "work")]
    finally:
        window.close()


# ------------------------------------------------------------ Issue 5: popups

def test_category_popup_fits_widest_label(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.services.category_service import CategoryService
    from app.database.category_repository import CategoryRepository
    from app.ui.category_icons import CategoryIconProvider
    from app.ui.widgets.category_selector import CategorySelector
    from app.ui.widgets.combo_popup import popup_content_width

    categories = CategoryService(CategoryRepository(db_connection)).list_active_categories()
    selector = CategorySelector(categories, CategoryIconProvider(
        Path(__file__).resolve().parent.parent / "assets" / "icons"))
    closed_width = selector.sizeHint().width()
    try:
        selector.showPopup()
        QApplication.instance().processEvents()
        view = selector.view()
        assert view.minimumWidth() >= view.sizeHintForColumn(0)
        assert view.minimumWidth() >= popup_content_width(selector)
        selector.hidePopup()
        # Closed control stays compact; popup sizing is view-only.
        assert selector.sizeHint().width() == closed_width
    finally:
        selector.close()


def test_priority_popup_fits_all_labels():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.combo_popup import popup_content_width
    from app.ui.widgets.priority_selector import PrioritySelector

    selector = PrioritySelector()
    try:
        selector.showPopup()
        QApplication.instance().processEvents()
        view = selector.view()
        assert view.minimumWidth() >= view.sizeHintForColumn(0)
        assert view.minimumWidth() >= popup_content_width(selector)
        assert selector.view().textElideMode() == Qt.TextElideMode.ElideNone
        selector.hidePopup()
    finally:
        selector.close()


# ------------------------------------------------------------ Issue 6: priority dots

def test_priority_dot_icon_mapping_and_cache():
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority
    from app.ui.widgets.priority_selector import priority_dot_icon

    def center_rgb(icon):
        img = icon.pixmap(12, 12).toImage()
        c = img.pixelColor(6, 6)
        return (c.red(), c.green(), c.blue(), c.alpha())

    r = center_rgb(priority_dot_icon(TaskPriority.HIGH))
    assert r[0] > 150 and r[0] > r[1] + 30 and r[0] > r[2] + 30  # red
    m = center_rgb(priority_dot_icon(TaskPriority.MEDIUM))
    assert m[2] > m[0] + 30 and m[2] > m[1] + 20  # calm blue
    low = center_rgb(priority_dot_icon(TaskPriority.LOW))
    assert 130 < low[0] < 175 and 140 < low[1] < 185 and 160 < low[2] < 200  # muted blue-gray
    assert low[3] == 255
    assert priority_dot_icon(TaskPriority.HIGH) is priority_dot_icon(TaskPriority.HIGH)
    # Labels, roles, and selection behavior untouched.
    from app.ui.widgets.priority_selector import PrioritySelector

    selector = PrioritySelector()
    try:
        assert [selector.itemText(i) for i in range(3)] == ["عاجل", "عادي", "منخفض"]
        assert all(not selector.itemIcon(i).isNull() for i in range(3))
        selector.set_priority(TaskPriority.LOW)
        assert selector.selected_priority() is TaskPriority.LOW
    finally:
        selector.close()


# ------------------------------------------------------------ Issue 7: completion icon

def test_right_icon_asset_is_valid_16px():
    from PySide6.QtGui import QPixmap

    path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "right-icon.png"
    assert path.is_file()
    pixmap = QPixmap(str(path))
    assert not pixmap.isNull()
    assert (pixmap.width(), pixmap.height()) == (16, 16)
    assert pixmap.toImage().hasAlphaChannel()


def test_checked_box_uses_real_asset_icon(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon, QPixmap

    from app.core.models import Task as _Task
    from app.ui.widgets.task_item import TaskItem

    _, _, provider, _ = _wiring(db_connection)
    from app.database.category_repository import CategoryRepository
    from app.core.services.category_service import CategoryService

    categories = CategoryService(CategoryRepository(db_connection)).list_active_categories()
    base = dict(id=1, day_id=1, text="m", is_completed=False, position=0,
                created_at="t", updated_at="t", category_id="general")
    item = TaskItem(_Task(**base), categories=categories, icon_provider=provider)
    try:
        box = item._checkbox
        assert box.objectName() == "taskCheckBox"
        assert box.iconSize() == QSize(16, 16)
        on_px = box.icon().pixmap(16, 16, QIcon.Mode.Normal, QIcon.State.On).toImage()
        off_px = box.icon().pixmap(16, 16, QIcon.Mode.Normal, QIcon.State.Off).toImage()

        def green_dominant(img):
            return sum(
                1 for y in range(img.height()) for x in range(img.width())
                if (lambda c: c.green() > 120 and c.green() > c.red() + 30
                    and c.green() > c.blue())(img.pixelColor(x, y)))

        # Checked state shows the real green asset...
        assert green_dominant(on_px) > 3
        # ...unchecked state is fully transparent (no residue, no border box).
        assert off_px.width() == 16
        assert all(off_px.pixelColor(x, y).alpha() == 0
                   for y in range(16) for x in range(16))
        # Matches the shipped asset pixel-for-pixel.
        asset = QPixmap(str(
            Path(__file__).resolve().parent.parent / "assets" / "icons" / "right-icon.png"))
        assert on_px == asset.toImage()
    finally:
        item.close()


def test_checkbox_without_provider_stays_functional():
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import Task as _Task
    from app.ui.widgets.task_item import TaskItem

    item = TaskItem(_Task(id=1, day_id=1, text="m", is_completed=False, position=0,
                          created_at="t", updated_at="t", category_id="general"))
    try:
        assert item._checkbox.objectName() == "taskCheckBox"
        assert item._checkbox.icon().isNull()  # no invented artwork
        fired = []
        item.completed_toggled.connect(lambda i, c: fired.append((i, c)))
        item._checkbox.click()
        assert fired == [(1, True)]
    finally:
        item.close()


def test_checkbox_toggle_and_a11y_preserved(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import Task as _Task
    from app.ui.widgets.task_item import TaskItem

    item = TaskItem(_Task(id=1, day_id=1, text="م", is_completed=False, position=0,
                          created_at="t", updated_at="t", category_id="general"))
    try:
        fired = []
        item.completed_toggled.connect(lambda i, c: fired.append((i, c)))
        item._checkbox.click()
        assert fired == [(1, True)]
        assert "تحديد إنجاز المهمة" in item._checkbox.accessibleName()
        item._checkbox.click()
        assert fired[-1] == (1, False)
    finally:
        item.close()
