"""R-dropdown: custom category popup + chip trigger (v3 §8.2, §9).

Covers stable-id selection in amended order, dismissal semantics, keyboard
map, focus restoration, placement/clamping (pure geometry), lifecycle
safety, and R-dock preservation (category-kept submit, priority reset).
Priority widgets and semantics are untouched.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

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


def _make_window(service, category_service, provider, day):
    from app.ui.windows.main_window import MainWindow

    return MainWindow(
        day=day,
        quote_text=day.quote_text,
        task_service=service,
        on_exit_requested=MagicMock(),
        category_service=category_service,
        icon_provider=provider,
    )


EXPECTED_IDS = [
    "general", "work", "personal", "study", "health", "home", "religion", "life",
]


# ------------------------------------------------------------ placement (pure)

def test_place_popup_prefers_above_and_clamps():
    from PySide6.QtCore import QRect, QSize

    from app.ui.widgets.category_popup import place_popup

    window = QRect(0, 0, 380, 640)
    trigger = QRect(200, 500, 120, 32)
    size = QSize(240, 394)
    above = place_popup(trigger, size, window, prefer_above=True)
    assert above.right() == trigger.right()
    assert above.bottom() <= trigger.top() - 6
    assert above.top() >= window.top() + 8

    cramped_top = QRect(200, 40, 120, 32)
    flipped = place_popup(cramped_top, size, window, prefer_above=True)
    assert flipped.top() == cramped_top.bottom() + 6

    tiny = QRect(0, 0, 380, 200)
    clamped = place_popup(QRect(200, 100, 120, 32), size, tiny, prefer_above=True)
    assert tiny.left() + 8 <= clamped.left()
    assert clamped.right() <= tiny.right() - 8
    # Taller than the window: best effort pins to the top margin.
    assert clamped.top() == tiny.top() + 8


# ------------------------------------------------------------ popup content

def test_popup_content_from_live_database(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.services.category_service import CategoryService
    from app.database.category_repository import CategoryRepository

    from app.ui.widgets.category_popup import CategoryPopup

    categories = CategoryService(CategoryRepository(db_connection)).list_active_categories()
    popup = CategoryPopup()
    try:
        popup.set_categories(categories)
        assert popup.category_ids() == EXPECTED_IDS
        assert popup._list.count() == 8
        for index in range(8):
            item = popup._list.item(index)
            assert item.data(Qt.ItemDataRole.UserRole) == EXPECTED_IDS[index]
            assert item.textAlignment() & Qt.AlignmentFlag.AlignRight
    finally:
        popup.close()


# ------------------------------------------------------------ chip + popup flow

def test_chip_opens_chooses_and_restores(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, provider, day)
    chip = window._category_selector
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        assert chip.selected_category_id() == "general"
        assert chip.selected_label() == "عام"
        assert chip.accessibleName() == "الفئة"
        assert not chip.is_popup_open()

        assert chip.open_popup() is True
        assert chip.is_popup_open()
        popup = chip._popup
        assert popup._list.hasFocus()

        popup._list.setCurrentRow(4)
        popup._choose_current()
        QApplication.instance().processEvents()
        assert chip.selected_category_id() == "health"
        assert chip.selected_label() == "صحة"
        assert not chip.is_popup_open()
    finally:
        window.close()


def test_escape_and_outside_dismissal_preserve_selection(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, provider, day)
    chip = window._category_selector
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        chip.set_category("work")
        assert chip.open_popup() is True
        popup = chip._popup
        popup._list.setCurrentRow(6)  # move, do not choose
        popup._list.keyPressEvent(
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        )
        QApplication.instance().processEvents()
        assert chip.selected_category_id() == "work"
        assert not chip.is_popup_open()

        assert chip.open_popup() is True
        popup = chip._popup
        popup.hide()  # outside-click path: native hide, no choice
        QApplication.instance().processEvents()
        assert chip.selected_category_id() == "work"
        assert not chip.is_popup_open()
    finally:
        window.close()


def test_keyboard_map_wraps_home_end_tab(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, provider, day)
    chip = window._category_selector

    def _key(key):
        from PySide6.QtGui import QKeyEvent as _QKeyEvent

        chip._popup._list.keyPressEvent(
            _QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
        )

    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        assert chip.open_popup() is True
        rows = chip._popup._list
        assert rows.currentRow() == 0
        _key(Qt.Key.Key_Up)  # wraps to last
        assert rows.currentRow() == 7
        _key(Qt.Key.Key_Down)  # wraps to first
        assert rows.currentRow() == 0
        _key(Qt.Key.Key_End)
        assert rows.currentRow() == 7
        _key(Qt.Key.Key_Home)
        assert rows.currentRow() == 0
        _key(Qt.Key.Key_Down)
        _key(Qt.Key.Key_Down)
        assert rows.currentRow() == 2
        _key(Qt.Key.Key_Space)  # choose personal
        QApplication.instance().processEvents()
        assert chip.selected_category_id() == "personal"
    finally:
        window.close()


def test_trigger_toggle_and_unknown_fallback(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, provider, day)
    chip = window._category_selector
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        assert chip.open_popup() is True
        assert chip.open_popup() is False  # re-click closes
        assert not chip.is_popup_open()
        chip.set_category("nope")
        assert chip.selected_category_id() == "general"
        chip.set_category(None)
        assert chip.selected_category_id() == "general"
    finally:
        window.close()


def test_popup_singleton_and_parent_lifecycle(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, provider, day)
    chip = window._category_selector
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        chip.open_popup()
        first = chip._popup
        chip._popup.hide()
        QApplication.instance().processEvents()
        chip.open_popup()
        assert chip._popup is first  # reused, never rebuilt per open
        assert first.parent() is chip
    finally:
        window.close()


# ------------------------------------------------------------ R-dock preservation

def test_submit_keeps_chip_category_and_resets_priority(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    from app.core.models import TaskPriority

    service, category_service, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-08")
    window = _make_window(service, category_service, provider, day)
    try:
        window._category_selector.set_category("study")
        window._priority_selector.set_priority(TaskPriority.HIGH)
        window._on_task_submitted("مهمة دراسة")
        tasks = service.get_today_tasks(day.id)
        assert [(t.text, t.category_id, t.priority) for t in tasks] == [
            ("مهمة دراسة", "study", TaskPriority.HIGH)
        ]
        assert window._category_selector.selected_category_id() == "study"
        assert window._priority_selector.selected_priority() == TaskPriority.MEDIUM
        assert window._task_input.text() == ""
    finally:
        window.close()
