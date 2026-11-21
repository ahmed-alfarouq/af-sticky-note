"""R-topbar: pin toggle, header structure, shadow margin, and mask tests.

Qt tests no-op when PySide6 is unavailable. Modal QMessageBox paths are
intercepted with a recording stub (same convention as test_settings.py) so
offscreen runs can never block.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


class _FakeSettings:
    """Dict-backed QSettings stand-in (never touches the real store)."""

    def __init__(self):
        self._data = {}
        self._group = ""
        self.saved = []

    def beginGroup(self, group):
        self._group = group

    def endGroup(self):
        self._group = ""

    def value(self, key, default=None):
        return self._data.get(f"{self._group}/{key}", default)

    def setValue(self, key, value):
        self._data[f"{self._group}/{key}"] = value
        self.saved.append((key, value))


class _FakeController:
    """Recording DesktopWindowController double with scripted outcomes."""

    def __init__(self, ok=True):
        self.ok = ok
        self.calls = []

    def set_pinned(self, hwnd, pinned):
        self.calls.append((hwnd, pinned))
        return self.ok

    def attach_to_desktop(self, hwnd):
        self.calls.append(("attach", hwnd))
        return self.ok

    def detach_from_desktop(self, hwnd):
        self.calls.append(("detach", hwnd))
        return self.ok

    def is_attached(self):
        return False


@contextmanager
def _recorded_warnings():
    import app.ui.windows.main_window as main_module

    calls = []
    real = main_module.QMessageBox

    class _Stub:
        @staticmethod
        def warning(*args, **kwargs):
            calls.append((args, kwargs))
            return None

    main_module.QMessageBox = _Stub
    try:
        yield calls
    finally:
        main_module.QMessageBox = real


def _wiring(db_connection):
    from app.core.services.category_service import CategoryService
    from app.core.services.history_service import HistoryService
    from app.core.services.task_service import TaskService
    from app.database.category_repository import CategoryRepository
    from app.database.day_repository import DayRepository
    from app.database.task_repository import TaskRepository
    from app.ui.category_icons import CategoryIconProvider

    task_repo = TaskRepository(db_connection)
    category_repo = CategoryRepository(db_connection)
    service = TaskService(task_repo=task_repo, category_repo=category_repo)
    category_service = CategoryService(category_repo)
    history = HistoryService(DayRepository(db_connection), task_repo)
    provider = CategoryIconProvider(Path(__file__).resolve().parent.parent / "assets" / "icons")
    return service, category_service, history, provider, DayRepository(db_connection)


def _make_pinned_window(db_connection, controller, pinned=True):
    from app.ui.pin_state import PinStateManager
    from app.ui.windows.main_window import MainWindow

    service, category_service, history, provider, day_repo = _wiring(db_connection)
    day = day_repo.create("2026-10-14")
    settings = _FakeSettingsWith(pinned)
    window = MainWindow(
        day=day,
        quote_text="q",
        task_service=service,
        history_service=history,
        on_exit_requested=MagicMock(),
        category_service=category_service,
        icon_provider=provider,
        window_controller=controller,
        pin_state_manager=PinStateManager(settings),
    )
    return window, settings


class _FakeSettingsWith(_FakeSettings):
    def __init__(self, pinned):
        super().__init__()
        self._data["WindowState/pinned"] = pinned


# ------------------------------------------------------------ pin persistence

def test_pin_defaults_to_pinned_and_round_trips():
    from app.ui.pin_state import PinStateManager

    manager = PinStateManager(_FakeSettings())
    assert manager.is_pinned() is True
    manager.save_pinned(False)
    assert manager.is_pinned() is False
    manager.save_pinned(True)
    assert manager.is_pinned() is True


# ------------------------------------------------------------ header structure

def test_topbar_structure_order_and_accessibility(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    window, _ = _make_pinned_window(db_connection, _FakeController())
    try:
        assert window._pin_btn.icon_key == "pin_active"
        assert window._pin_btn.toolTip() == "إلغاء التثبيت"
        assert window._pin_btn.accessibleName() == "إلغاء التثبيت"
        assert (window._pin_btn.width(), window._pin_btn.height()) == (36, 36)
        assert (window._grip.width(), window._grip.height()) == (32, 4)
        assert window._grip.focusPolicy() == Qt.FocusPolicy.NoFocus
        assert window._archive_btn.accessibleName() == "الأرشيف"
        assert window._settings_btn.accessibleName() == "إعدادات"
        assert window._close_btn.accessibleName() == "إغلاق"
        names = {
            window._pin_btn.accessibleName(),
            window._archive_btn.accessibleName(),
            window._settings_btn.accessibleName(),
            window._close_btn.accessibleName(),
        }
        assert len(names) == 4
        for button in (window._pin_btn, window._archive_btn,
                       window._settings_btn, window._close_btn):
            assert not button.icon().isNull()
    finally:
        window.close()


def test_icon_button_state_contract():
    if _skip_without_qt():
        return
    _qt_app()
    from app.ui.widgets.icon_button import IconButton

    button = IconButton("close")
    try:
        assert (button.width(), button.height()) == (36, 36)
        assert button.icon_key == "close"
        enabled_icon = button.icon()
        assert not enabled_icon.isNull()
        button.setEnabled(False)
        assert button.icon() is not enabled_icon
        button.setEnabled(True)
        button.set_icon_key("plus")
        assert button.icon_key == "plus"
    finally:
        button.close()


# ------------------------------------------------------------ pin transitions

def test_successful_pin_toggle_flips_flags_persists_and_shadows(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    controller = _FakeController(ok=True)
    window, settings = _make_pinned_window(db_connection, controller)
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        assert window.is_pinned() is True
        assert window.windowFlags() & Qt.WindowType.Tool == Qt.WindowType.Tool

        assert window._apply_pin_state(False) is True
        assert window.is_pinned() is False
        assert window.windowFlags() & Qt.WindowType.Tool != Qt.WindowType.Tool
        assert window._pin_btn.icon_key == "pin"
        assert window._pin_btn.toolTip() == "تثبيت على سطح المكتب"
        assert controller.calls[-1][1] is False
        assert settings.saved == [("pinned", False)]
        assert window._shadow_effect.blurRadius() == 60
        assert (window._shadow_effect.xOffset(), window._shadow_effect.yOffset()) == (0, 24)
    finally:
        window.close()


def test_failed_pin_toggle_rolls_back_and_warns(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    controller = _FakeController(ok=False)
    window, settings = _make_pinned_window(db_connection, controller)
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        with _recorded_warnings() as warnings:
            window._on_pin_clicked()
        assert window.is_pinned() is True
        assert window.windowFlags() & Qt.WindowType.Tool == Qt.WindowType.Tool
        assert window._pin_btn.icon_key == "pin_active"
        assert settings.saved == []
        assert len(warnings) == 1
        assert warnings[0][0][1] == "تعذر تغيير التثبيت"
    finally:
        window.close()


def test_unpinned_construction_has_no_tool_flag(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    window, _ = _make_pinned_window(db_connection, _FakeController(), pinned=False)
    try:
        assert window.is_pinned() is False
        assert window.windowFlags() & Qt.WindowType.Tool != Qt.WindowType.Tool
        assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert window._pin_btn.icon_key == "pin"
    finally:
        window.close()


# ------------------------------------------------------------ margin and mask

def test_shadow_margin_frames_paper_and_mask_is_translated(db_connection):
    if _skip_without_qt():
        return
    _qt_app()
    window, _ = _make_pinned_window(db_connection, _FakeController())
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        paper = window._paper_surface.geometry()
        assert (paper.x(), paper.y()) == (32, 32)
        assert (paper.width(), paper.height()) == (380 - 64, 640 - 64)
        mask = window.mask()
        assert not mask.isEmpty()
        x, y, w, h = paper.x(), paper.y(), paper.width(), paper.height()
        assert mask.boundingRect().getCoords() == (x, y, x + w - 1, y + h - 1)
        assert not mask.contains(QPoint(2, 2))
    finally:
        window.close()


def test_resize_edges_follow_the_paper_rect(db_connection):
    if _skip_without_qt():
        return
    _qt_app()

    window, _ = _make_pinned_window(db_connection, _FakeController())
    try:
        window.resize(380, 640)
        window.show()
        QApplication.instance().processEvents()
        paper = window._paper_surface.geometry()
        top_left = window.mapToGlobal(paper.topLeft())
        edges = window._determine_resize_edges(top_left + QPoint(2, 2))
        assert edges & 1 and edges & 4  # left + top at the paper corner
        # The transparent margin itself is click-through: no edges there.
        assert window._determine_resize_edges(QPoint(2, 2)) == 0
    finally:
        window.close()
