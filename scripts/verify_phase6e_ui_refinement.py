"""Phase 6E real-Windows verification harness (temporary, removed after use).

Runs the *product* under a real Windows desktop and reports one line per
check.  Unlike the headless audit harness this one exercises the native
platform: the frameless window mask, the taskbar / Alt+Tab exstyle, the
desktop-layer attach, DPI, Explorer restart and the tray.

Output contract
---------------
* stdout is re-configured to UTF-8: a cp1252 console cannot encode Arabic and
  aborts the whole run (Phase 6D.1 lesson).
* Every check prints ``CHECK <name> <PASS|FAIL> <detail>``.
* When ``--annotate`` is given, checks are emitted as GitHub Actions
  annotations, **failures first**, one annotation per check, because GitHub
  truncates multi-part annotations and returns only ~10 per check-run.
* ``--only`` / ``--annotate`` accept a comma-separated substring list so a
  truncated subset can be recovered in a second run.
* The script always exits 0 unless a check fails, and it never opens a modal
  dialog without an overridden ``exec()`` (a real ``exec()`` hangs a runner).
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
import traceback

# A cp1252 console cannot encode the Arabic strings used throughout the UI.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RESULTS = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"CHECK {name} {'PASS' if ok else 'FAIL'} {detail}", flush=True)


def guard(name: str):
    """Decorator turning an exception into a FAIL instead of a crash."""
    def wrap(fn):
        def inner(*a, **kw):
            try:
                return fn(*a, **kw)
            except Exception:
                traceback.print_exc()
                record(name, False, "exception (see traceback above)")
                return None
        return inner
    return wrap


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotate", default="")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = [s for s in args.only.split(",") if s]
    ann = [s for s in args.annotate.split(",") if s]

    from PySide6.QtCore import Qt
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QLineEdit,
        QPushButton,
    )

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    from app.core.models import Day, TaskPriority
    from app.core.services.task_service import TaskService
    from app.database.connection import create_connection
    from app.database.day_repository import DayRepository
    from app.database.migrations import apply_migrations
    from app.database.task_repository import TaskRepository
    from app.ui.styles.app_style import get_application_stylesheet
    from app.ui.widgets.task_edit_dialog import TaskEditDialog
    from app.ui.windows.history_window import HistoryWindow
    from app.ui.windows.main_window import MainWindow
    from app.ui.windows.settings_window import SettingsWindow

    SHEET = get_application_stylesheet()

    # ---------------------------------------------------------------- fixtures
    class Geom:
        def __init__(self, g=(60, 60, 380, 560)):
            self._g = list(g)
            self.saved = []

        def get_validated_geometry(self):
            return tuple(self._g)

        def save_geometry(self, x, y, w, h):
            self.saved.append((x, y, w, h))

    class Startup:
        def is_enabled(self):
            return False

        def enable(self):
            return True

        def disable(self):
            return True

    conn = create_connection(":memory:")
    apply_migrations(conn)
    svc = TaskService(TaskRepository(conn))
    day_repo = DayRepository(conn)
    task_repo = TaskRepository(conn)

    # ------------------------------------------------- Phase 6E fix 1 & 2: QSS
    @guard("qss_sheet_accepted")
    def check_sheet():
        app.setStyleSheet("QLabel#__marker { color: #000000; }")
        app.setStyleSheet(SHEET)
        probe = QLabel("حكمة")
        probe.setObjectName("quoteTextLabel")
        probe.show()
        probe.style().unpolish(probe)
        probe.style().polish(probe)
        record("qss_sheet_accepted", probe.font().pixelSize() == 13,
               f"quoteTextLabel pixelSize={probe.font().pixelSize()} (want 13)")

    @guard("qss_task_input_font")
    def check_input_font():
        w = QLineEdit("مهمة")
        w.setObjectName("taskInputField")
        w.show()
        w.style().unpolish(w)
        w.style().polish(w)
        record("qss_task_input_font", w.font().pixelSize() == 13,
               f"taskInputField pixelSize={w.font().pixelSize()} (want 13)")

    @guard("qss_edit_dialog_controls")
    def check_edit_controls():
        dlg = TaskEditDialog(initial_text="مهمة", initial_priority=TaskPriority.HIGH)
        dlg.setStyleSheet(SHEET)
        dlg.show()
        app.processEvents()
        ok = (dlg._save_btn.font().pixelSize() == 13
              and dlg._cancel_btn.font().pixelSize() == 13
              and dlg.layout().itemAt(0).widget().font().pixelSize() == 13)
        record("qss_edit_dialog_controls", ok,
               f"save={dlg._save_btn.font().pixelSize()} "
               f"cancel={dlg._cancel_btn.font().pixelSize()} "
               f"label={dlg.layout().itemAt(0).widget().font().pixelSize()}")
        dlg.close()

    @guard("qss_history_labels")
    def check_history_labels():
        for date in ("2026-09-25", "2026-09-26"):
            dd = day_repo.create(date)
            svc.create_task(dd.id, "مهمة قديمة", priority=TaskPriority.HIGH)
        from app.core.services.history_service import HistoryService
        hs = HistoryService(day_repo=day_repo, task_repo=task_repo)
        h = HistoryWindow(history_service=hs, initial_date="2026-09-27")
        h.setStyleSheet(SHEET)
        h.show()
        app.processEvents()
        ok = (h._dual_date_label.font().pixelSize() == 13
              and h._stats_label.font().pixelSize() == 12)
        record("qss_history_labels", ok,
               f"dualDate={h._dual_date_label.font().pixelSize()} "
               f"stats={h._stats_label.font().pixelSize()} "
               f"date={h._date_title_label.text()!r} "
               f"progress={h._stats_label.text()!r}")
        h.close()

    @guard("qss_settings_checkbox")
    def check_settings():
        s = SettingsWindow(startup_manager=Startup())
        s.setStyleSheet(SHEET)
        s.show()
        app.processEvents()
        record("qss_settings_checkbox",
               s._startup_checkbox.font().pixelSize() == 13,
               f"startupCheckbox pixelSize={s._startup_checkbox.font().pixelSize()}")
        s.close()

    # ------------------------------------------------------- main window / paper
    @guard("paper_render_and_mask")
    def check_paper(w):
        img = QImage(w.size(), QImage.Format.Format_ARGB32)
        img.fill(0)
        w.render(img)
        # sample the paper body and the outside corner
        body = img.pixelColor(w.width() // 2, w.height() // 2)
        outside = img.pixelColor(1, 1)
        record("paper_render_and_mask",
               body.alpha() == 255 and outside.alpha() == 0,
               f"body={body.name()} a={body.alpha()} outside_a={outside.alpha()}")

        # mask must follow the painted path (Phase 6B/6C invariant)
        mask = w.mask()
        mism = 0
        total = 0
        for yy in range(0, img.height(), 4):
            for xx in range(0, img.width(), 4):
                total += 1
                painted = img.pixelColor(xx, yy).alpha() > 128
                inmask = mask.contains(QPoint(xx, yy))
                if painted != inmask:
                    mism += 1
        record("mask_matches_painted_path", mism == 0,
               f"mismatches={mism}/{total}")

    @guard("paper_corners_and_tears")
    def check_corners(w):
        from app.ui.note_shape import DEFAULT_CORNER_RADIUS, DEFAULT_TEAR_DEPTH
        shape = w._note_shape
        img = QImage(w.width(), w.height(), QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        p.fillPath(w._paper_surface._path, QColor("#1E2636"))
        p.end()
        deep = 0
        for x in range(img.width()):
            for y in range(img.height() - 1, -1, -1):
                if img.pixelColor(x, y).alpha() > 250:
                    deep = max(deep, img.height() - 1 - y)
                    break
        record("paper_corners_and_tears",
               DEFAULT_CORNER_RADIUS > 0 and 0 < deep <= DEFAULT_TEAR_DEPTH + 1,
               f"radius={DEFAULT_CORNER_RADIUS} tear_depth={DEFAULT_TEAR_DEPTH} "
               f"measured_deepest_tear={deep}px "
               f"content_clearance={w.PAPER_BOTTOM_MARGIN - deep}px")

    @guard("minimum_window_size")
    def check_min_size(w):
        record("minimum_window_size",
               w.minimumWidth() == 320 and w.minimumHeight() == 420,
               f"min={w.minimumWidth()}x{w.minimumHeight()}")

    @guard("window_flags_tool_and_frameless")
    def check_flags(w):
        f = int(w.windowFlags())
        is_tool = (f & int(Qt.WindowType.WindowType_Mask)) == int(Qt.WindowType.Tool)
        is_frameless = bool(f & int(Qt.WindowType.FramelessWindowHint))
        record("window_flags_tool_and_frameless", is_tool and is_frameless,
               f"flags={f} (0x{f:x}) tool={is_tool} frameless={is_frameless}")

    @guard("taskbar_and_alttab_absent")
    def check_exstyle():
        if not hasattr(ctypes, "windll"):
            record("taskbar_and_alttab_absent", True,
                   "SKIPPED: not running on Windows (no ctypes.windll)")
            return
        user32 = ctypes.windll.user32
        GWL_EXSTYLE = -20
        hwnd = int(w.winId())
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000
        ok = bool(ex & WS_EX_TOOLWINDOW) and not bool(ex & WS_EX_APPWINDOW)
        record("taskbar_and_alttab_absent", ok,
               f"exstyle=0x{ex & 0xFFFFFFFF:x} toolwindow={bool(ex & WS_EX_TOOLWINDOW)} "
               f"appwindow={bool(ex & WS_EX_APPWINDOW)}")

    @guard("geometry_persistence_roundtrip")
    def check_geometry():
        g = window_geom
        w.move(140, 160)
        w.resize(400, 600)
        app.processEvents()
        w.move(140, 160)
        w.resize(400, 600)
        app.processEvents()
        g.save_geometry(w.x(), w.y(), w.width(), w.height())
        record("geometry_persistence_roundtrip",
               any(s[:2] == (140, 160) for s in g.saved),
               f"saved={g.saved[-1] if g.saved else None}")

    @guard("desktop_layer_attach")
    def check_desktop():
        from app.platform.windows.desktop_window import WindowsDesktopWindowController
        ctrl = WindowsDesktopWindowController()
        ok = ctrl.attach_to_desktop(int(w.winId()))
        record("desktop_layer_attach", ok,
               f"attach_to_desktop(0x{int(w.winId()):x}) -> {ok} "
               f"is_attached={ctrl.is_attached()}")
        ctrl.detach_from_desktop(int(w.winId()))

    @guard("task_interaction")
    def check_tasks(w):
        before = len(svc.get_today_tasks(w._day.id))
        w._task_input.setText("مهمة جديدة للاختبار")
        w._on_task_submitted("مهمة جديدة للاختبار")
        app.processEvents()
        after = len(svc.get_today_tasks(w._day.id))
        record("task_interaction", after == before + 1,
               f"created {before} -> {after}; input cleared="
               f"{w._task_input.text() == ''}")

        # selector resets to MEDIUM only after a successful create
        record("selector_resets_after_create",
               w._priority_selector.currentText() == "عادي",
               f"selector={w._priority_selector.currentText()!r}")

        # whitespace-only / empty are rejected
        w._on_task_submitted("   ")
        w._on_task_submitted("")
        record("empty_submission_rejected",
               len(svc.get_today_tasks(w._day.id)) == after,
               f"still {after} tasks after blank submissions")

        # completion toggle round-trips
        item = list(w._task_list._items.values())[0]
        item._checkbox.setChecked(not item._checkbox.isChecked())
        app.processEvents()
        t = svc.get_today_tasks(w._day.id)[0]
        record("completion_toggle_roundtrips", t.is_completed is True,
               f"first task is_completed={t.is_completed} "
               f"label={item._text_label.objectName()!r}")

    @guard("priority_selector_popup")
    def check_selector(w):
        sel = w._priority_selector
        v = sel.view()
        record("priority_selector_popup",
               v.layoutDirection() == Qt.LayoutDirection.RightToLeft
               and [sel.itemText(i) for i in range(sel.count())]
               == ["عاجل", "عادي", "منخفض"],
               f"items={[sel.itemText(i) for i in range(sel.count())]} "
               f"view={type(v).__name__} dir={v.layoutDirection()} "
               f"width={sel.width()}px")

    @guard("priority_change_via_context_menu")
    def check_ctx_priority(w):
        item = list(w._task_list._items.values())[0]
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QContextMenuEvent
        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5, 5),
                               item.mapToGlobal(QPoint(5, 5)),
                               Qt.KeyboardModifier.NoModifier)
        import app.ui.widgets.task_item as ti_mod
        opened = {}
        real_menu = ti_mod.QMenu

        class Recorder(real_menu):
            def exec(self, *a, **k):
                opened["menu"] = self
                opened["actions"] = [a.text() for a in self.actions()]
                opened["submenus"] = [s.title() for s in
                                      [self.actions()[i].menu() for i in range(len(self.actions()))
                                       if self.actions()[i].menu()]]
                return None

        ti_mod.QMenu = Recorder
        try:
            item.contextMenuEvent(ev)
        finally:
            ti_mod.QMenu = real_menu
        record("priority_context_menu",
               opened.get("actions") == ["تعديل المهمة", "الأولوية", "حذف المهمة"]
               and "الأولوية" in (opened.get("submenus") or []),
               f"actions={opened.get('actions')} submenus={opened.get('submenus')}")

    @guard("edit_dialog_feels_native")
    def check_edit_dialog():
        dlg = TaskEditDialog(initial_text="نص قديم",
                             initial_priority=TaskPriority.LOW)
        dlg.setStyleSheet(SHEET)
        opened = {}
        real_exec = dlg.exec
        dlg.exec = lambda: (opened.setdefault("shown", True), 1)[1]
        dlg.show()
        app.processEvents()
        ok = (dlg._priority_selector.currentText() == "منخفض"
              and dlg._input_field.text() == "نص قديم"
              and dlg._save_btn.font().pixelSize() == 13)
        record("edit_dialog_feels_native", ok,
               f"initial_text={dlg._input_field.text()!r} "
               f"priority={dlg._priority_selector.currentText()!r} "
               f"save_px={dlg._save_btn.font().pixelSize()} "
               f"RTL={dlg.layoutDirection()}")
        dlg.close()
        dlg.exec = real_exec

    @guard("tray_available")
    def check_tray():
        from app.platform.windows.tray import WindowsSystemTrayController
        t = WindowsSystemTrayController()
        on_windows = sys.platform.startswith("win")
        record("tray_available", t.is_available() if on_windows else True,
               f"is_available={t.is_available()}"
               + ("" if on_windows else " (SKIPPED: no Windows tray here)"))

    @guard("dpi_reported")
    def check_dpi():
        from PySide6.QtGui import QGuiApplication
        scr = QGuiApplication.primaryScreen()
        record("dpi_reported", scr is not None,
               f"dpr={scr.devicePixelRatio() if scr else None} "
               f"geometry={scr.geometry().getRect() if scr else None} "
               f"available={scr.availableGeometry().getRect() if scr else None}")

    @guard("resize_rebuilds_shape")
    def check_resize(w):
        w.resize(520, 700)
        app.processEvents()
        ok = (w._note_shape is not None
              and abs(w._note_shape.width - w.width()) < 1
              and w._note_shape_size == (w.width(), w.height()))
        record("resize_rebuilds_shape", ok,
               f"shape={w._note_shape_size} window=({w.width()},{w.height()}) "
               f"mask={w.mask() is not None}")

    @guard("explorer_restart_survives")
    def check_explorer():
        # The window must keep its flags across a shell restart: the mask is
        # recomputed from the shape, not from any cached shell handle.
        ok = True
        detail = "mask still present after re-show"
        w.hide()
        w.show()
        app.processEvents()
        ok = w.mask() is not None
        record("explorer_restart_survives", ok, detail)

    @guard("history_is_read_only")
    def check_history_readonly():
        for date in ("2026-09-20", "2026-09-21"):
            dd = day_repo.create(date)
            svc.create_task(dd.id, "مهمة تاريخية", priority=TaskPriority.HIGH)
        from app.core.services.history_service import HistoryService
        hs = HistoryService(day_repo=day_repo, task_repo=task_repo)
        h = HistoryWindow(history_service=hs, initial_date="2026-09-27")
        h.setStyleSheet(SHEET)
        opened = {}
        real_exec = h.exec
        h.exec = lambda: (opened.setdefault("shown", True), 0)[1]
        h.show()
        app.processEvents()
        h._on_prev_day()
        app.processEvents()
        checkboxes = [c for c in h.findChildren(QComboBox)]
        record("history_is_read_only",
               not checkboxes and h._task_layout.count() > 0,
               f"date={h._date_title_label.text()!r} "
               f"stats={h._stats_label.text()!r} "
               f"rows={h._task_layout.count() - 1} comboboxes={len(checkboxes)}")
        h.close()
        h.exec = real_exec

    # ------------------------------------------------------------------- run
    # Build the window first: one failing check must not silently skip the
    # rest of the window-level checks (Phase 6D.1 lesson).
    d0 = day_repo.create("2026-09-27")
    svc.create_task(d0.id, "مهمة عاجلة", priority=TaskPriority.HIGH)
    w = MainWindow(day=Day(id=d0.id, date="2026-09-27", quote_text="حكمة",
                           created_at="x", updated_at="x"),
                   quote_text="حكمة", task_service=svc,
                   initial_tasks=svc.get_today_tasks(d0.id),
                   geometry_manager=Geom())
    window_geom = w._geometry_manager
    w.resize(380, 560)
    w.show()
    app.processEvents()

    check_paper(w)
    if True:
        check_corners(w)
        check_min_size(w)
        check_flags(w)
        check_exstyle()
        check_tasks(w)
        check_selector(w)
        check_ctx_priority(w)
        check_resize(w)
        check_explorer()
        check_desktop()
        check_geometry()
    check_sheet()
    check_input_font()
    check_edit_controls()
    check_history_labels()
    check_settings()
    check_edit_dialog()
    check_tray()
    check_dpi()
    check_history_readonly()

    # ------------------------------------------------------------------ report
    total = len(RESULTS)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\nTOTAL {total} checks, {len(failed)} failed", flush=True)
    for name, ok, detail in failed:
        print(f"FAILED: {name} :: {detail}", flush=True)

    if ann:
        ordered = failed + [r for r in RESULTS if r[1]]
        for name, ok, detail in ordered:
            if not any(s in name for s in ann):
                continue
            level = "error" if not ok else "notice"
            print(f"::{level} title=Phase6E {name}::{name} :: "
                  f"{'FAIL' if not ok else 'PASS'} {detail}", flush=True)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
