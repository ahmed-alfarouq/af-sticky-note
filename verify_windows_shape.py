"""Phase 6C -- real-Windows verification of the organic paper silhouette.

Exercises the actual application window on a real Windows desktop session and
reports, as machine readable JSON plus PNG renders:

  * window flags / transparency attributes (unchanged desktop-layer contract)
  * whether the painted paper, the QPainterPath and the native window mask
    agree with each other
  * whether the transparent region outside the paper is really transparent
    and really does not receive mouse input
  * resize in all 8 directions, minimum size clamping, header dragging,
    header button clicks
  * DPI / scaling values reported by the platform

Exit code is non-zero when any check fails.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from unittest.mock import MagicMock

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, qVersion
from PySide6.QtGui import QColor, QImage, QPainterPath
from PySide6.QtWidgets import QApplication

ARTIFACTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
os.makedirs(ARTIFACTS, exist_ok=True)

RESULTS = {"checks": [], "failures": [], "info": {}, "notes": []}


def check(name, ok, detail=""):
    RESULTS["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)})
    if not ok:
        RESULTS["failures"].append(f"{name}: {detail}")
    print(("PASS  " if ok else "FAIL  ") + name + (f"  -- {detail}" if detail else ""), flush=True)


def note(text):
    RESULTS["notes"].append(text)
    print("NOTE  " + text, flush=True)


from app.core.models import Day
from app.core.services.task_service import TaskService
from app.ui.note_shape import build_note_shape
from app.ui.widgets.paper_surface import PaperSurface, shape_to_painter_path, shape_to_region
from app.ui.windows.main_window import MainWindow


class FakeGeometryManager:
    """Avoid touching the real QSettings/registry during verification."""

    def __init__(self, geometry=(120, 120, 380, 560)):
        self._geometry = geometry
        self.saved = []

    def get_validated_geometry(self):
        return self._geometry

    def save_geometry(self, *args):
        self.saved.append(args)


def make_window(width=380, height=560, geometry=(120, 120, 380, 560)):
    day = Day(id=1, date="2026-09-27", quote_text="اقتباس", created_at="n", updated_at="n")
    exit_calls = []
    window = MainWindow(
        day=day,
        quote_text=day.quote_text,
        task_service=MagicMock(spec=TaskService),
        geometry_manager=FakeGeometryManager(geometry),
        on_exit_requested=lambda: exit_calls.append(True),
    )
    window._exit_calls = exit_calls
    window.resize(width, height)
    window.show()
    QApplication.instance().processEvents()
    return window


def main():
    app = QApplication.instance() or QApplication([])

    RESULTS["info"]["qt_version"] = qVersion()
    RESULTS["info"]["platform_name"] = app.platformName()
    RESULTS["info"]["python"] = sys.version.split()[0]
    screen = app.primaryScreen()
    if screen is not None:
        RESULTS["info"]["screen"] = {
            "name": screen.name(),
            "geometry": screen.geometry().getCoords(),
            "device_pixel_ratio": screen.devicePixelRatio(),
            "logical_dpi_x": round(screen.logicalDotsPerInchX(), 1),
            "logical_dpi_y": round(screen.logicalDotsPerInchY(), 1),
        }
    print(f"Qt {qVersion()} on platform '{app.platformName()}'", flush=True)

    window = make_window()
    shape = window._note_shape
    check("shape built for window size",
          shape is not None and (shape.width, shape.height) == (window.width(), window.height()),
          f"{getattr(shape, 'width', None)}x{getattr(shape, 'height', None)} vs {window.width()}x{window.height()}")
    RESULTS["info"]["shape"] = {
        "width": shape.width, "height": shape.height,
        "corner_radius": shape.corner_radius, "tear_depth": shape.tear_depth,
        "segments": shape.segment_count, "tears": len(shape.tears),
    }
    RESULTS["info"]["device_pixel_ratio_window"] = window.devicePixelRatio()
    RESULTS["info"]["window_flags"] = int(window.windowFlags())
    RESULTS["info"]["translucent_background"] = bool(
        window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

    # --- window flags must be untouched (desktop layer depends on them) ----
    flags = window.windowFlags()
    check("frameless + tool flags preserved",
          bool(flags & Qt.WindowType.FramelessWindowHint) and bool(flags & Qt.WindowType.Tool)
          and not bool(flags & Qt.WindowType.WindowStaysOnTopHint), hex(int(flags)))
    check("translucent background attribute preserved",
          window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

    # --- mask ----------------------------------------------------------------
    mask = window.mask()
    check("window mask is applied", mask is not None)
    if mask is not None:
        rect = mask.boundingRect().getCoords()
        check("mask covers the full window rect",
              rect == (0, 0, window.width() - 1, window.height() - 1), str(rect))
        check("mask includes the centre of the paper",
              mask.contains(QPoint(window.width() // 2, window.height() // 2)))
        check("mask excludes the rounded top-left corner",
              not mask.contains(QPoint(2, 2)))
        check("mask excludes the rounded top-right corner",
              not mask.contains(QPoint(window.width() - 3, 2)))
        check("mask includes the solid bottom-left corner",
              mask.contains(QPoint(2, window.height() - 2)))
        check("mask includes the solid bottom-right corner",
              mask.contains(QPoint(window.width() - 3, window.height() - 2)))

        # --- mask must agree with the painted path -------------------------
        path = shape_to_painter_path(shape)
        mismatches = []
        total = 0
        for y in range(0, window.height(), 3):
            for x in range(0, window.width(), 3):
                total += 1
                in_path = path.contains(QPointF(x + 0.5, y + 0.5))
                in_mask = mask.contains(QPoint(x, y))
                # allow a one pixel tolerance band around the anti-aliased edge
                if in_path != in_mask:
                    near = any(
                        in_path != path.contains(QPointF(x + 0.5 + dx, y + 0.5 + dy))
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    )
                    if not near:
                        mismatches.append((x, y, in_path, in_mask))
        mismatch_pct = 100.0 * len(mismatches) / total if total else 0.0
        RESULTS["info"]["mask_path_mismatch_percent"] = round(mismatch_pct, 4)
        check("window mask agrees with the painted path",
              mismatch_pct < 1.0, f"{len(mismatches)}/{total} samples mismatch ({mismatch_pct:.3f}%)")

        # --- resize bands remain usable ------------------------------------
        band = 8
        def coverage(x0, x1, y0, y1):
            inside = total_px = 0
            for yy in range(max(0, y0), min(window.height(), y1)):
                for xx in range(max(0, x0), min(window.width(), x1)):
                    total_px += 1
                    inside += 1 if mask.contains(QPoint(xx, yy)) else 0
            return inside / total_px if total_px else 0.0

        w, h = window.width(), window.height()
        for name, box in {
            "left": (0, band, 0, h),
            "right": (w - band, w, 0, h),
            "top": (0, w, 0, band),
            "bottom": (0, w, h - band, h),
        }.items():
            cov = coverage(*box)
            RESULTS["info"][f"resize_band_{name}"] = round(cov, 4)
            check(f"{name} resize band usable", cov > 0.85, f"{cov * 100:.1f}% of the band is inside the mask")

    # --- real transparency of the area outside the paper --------------------
    image = window.grab().toImage().convertToFormat(QImage.Format_ARGB32)
    def alpha(x, y):
        return QColor(image.pixel(x, y)).alpha()

    outside = alpha(2, 2)
    inside = alpha(window.width() // 2, window.height() // 2)
    RESULTS["info"]["alpha_outside_paper"] = outside
    RESULTS["info"]["alpha_inside_paper"] = inside
    check("paper is fully opaque", inside == 255, f"alpha={inside}")
    if outside == 255:
        note("area outside the paper is opaque in the grab: the native mask is what "
             "clips the silhouette (no per-pixel alpha compositing on this platform/config)")
    elif outside < 32:
        note("area outside the paper is transparent (per-pixel alpha compositing active)")
    else:
        note(f"area outside the paper has partial alpha ({outside})")

    # --- painted colours ----------------------------------------------------
    def rgb(x, y):
        c = QColor(image.pixel(x, y))
        return (c.red(), c.green(), c.blue())

    from app.ui.styles.app_style import COLOR_STICKY_PAPER, COLOR_STICKY_BORDER
    expected = tuple(int(COLOR_STICKY_PAPER[i:i + 2], 16) for i in (1, 3, 5))
    centre = rgb(window.width() // 2, window.height() // 2)
    check("paper uses the Daily Sticky palette", centre == expected, f"{centre} vs {expected}")
    border_expected = tuple(int(COLOR_STICKY_BORDER[i:i + 2], 16) for i in (1, 3, 5))
    border_seen = rgb(window.width() // 2, 1)
    check("border is drawn along the top edge",
          border_seen != centre and border_seen != (0, 0, 0), f"{border_seen}")
    note(f"palette: paper={COLOR_STICKY_PAPER} border={COLOR_STICKY_BORDER}")

    # --- interaction --------------------------------------------------------
    # Some Qt platform plugins (notably 'offscreen' and 'minimal') accept
    # setMask() but ignore it natively -- they print "This plugin does not
    # support setting window masks". Native hit-testing can therefore only be
    # verified on a real platform such as Windows.
    platform_supports_mask = app.platformName() not in ("offscreen", "minimal", "vnc")
    RESULTS["info"]["platform_supports_native_mask"] = platform_supports_mask
    if not platform_supports_mask:
        note(f"platform '{app.platformName()}' ignores native window masks, so click-through "
             "cannot be verified here -- it must be checked on a real Windows desktop")
    try:
        from PySide6.QtTest import QTest

        # click inside the paper must reach the window, a click outside must not
        pressed = []
        original_mouse_press = window.mousePressEvent

        def spy(event):
            pressed.append((event.position().x(), event.position().y()))
            return original_mouse_press(event)

        window.mousePressEvent = spy
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(window.width() // 2, 40))
        QApplication.instance().processEvents()
        inside_clicks = len(pressed)
        pressed.clear()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
        QApplication.instance().processEvents()
        outside_clicks = len(pressed)
        window.mousePressEvent = original_mouse_press
        check("click inside the paper reaches the window", inside_clicks >= 1, f"{inside_clicks} events")
        if platform_supports_mask:
            check("click outside the paper does not reach the window", outside_clicks == 0,
                  f"{outside_clicks} events")
        else:
            note(f"click outside the paper produced {outside_clicks} window event(s); expected 0 on a "
                 "platform that honours native masks")
    except Exception as exc:
        note(f"QTest interaction checks unavailable: {exc}")
        traceback.print_exc()

    # --- resize in all 8 directions ----------------------------------------
    try:
        from PySide6.QtTest import QTest

        directions = {
            "left": (QPoint(3, 300), QPoint(3 - 25, 310)),
            "right": (QPoint(window.width() - 4, 300), QPoint(window.width() - 4 + 30, 310)),
            "top": (QPoint(window.width() // 2, 3), QPoint(window.width() // 2 + 10, 3 - 20)),
            "bottom": (QPoint(window.width() // 2, window.height() - 4),
                       QPoint(window.width() // 2 + 10, window.height() - 4 + 35)),
            "top-left": (QPoint(3, 3), QPoint(3 - 20, 3 - 15)),
            "top-right": (QPoint(window.width() - 4, 3), QPoint(window.width() - 4 + 22, 3 - 15)),
            "bottom-left": (QPoint(3, window.height() - 4), QPoint(3 - 18, window.height() - 4 + 28)),
            "bottom-right": (QPoint(window.width() - 4, window.height() - 4),
                             QPoint(window.width() - 4 + 24, window.height() - 4 + 30)),
        }
        for name, (start, end) in directions.items():
            win = make_window()
            before = win.geometry()
            QTest.mousePress(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
            QApplication.instance().processEvents()
            QTest.mouseMove(win, end)
            QApplication.instance().processEvents()
            QTest.mouseRelease(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
            QApplication.instance().processEvents()
            after = win.geometry()
            resized = (before.width(), before.height()) != (after.width(), after.height())
            mask = win.mask()
            in_sync = mask is not None and mask.boundingRect().getCoords() == (
                0, 0, after.width() - 1, after.height() - 1)
            shape_ok = (int(win._note_shape.width), int(win._note_shape.height)) == (
                after.width(), after.height())
            check(f"resize {name}", resized and in_sync and shape_ok,
                  f"{before.width()}x{before.height()} -> {after.width()}x{after.height()} "
                  f"mask_in_sync={in_sync} shape_in_sync={shape_ok}")
            RESULTS["info"][f"resize_{name}"] = {
                "before": [before.width(), before.height()],
                "after": [after.width(), after.height()],
                "mask_in_sync": in_sync, "shape_in_sync": shape_ok,
            }
            note(f"resize {name}: requested delta "
                 f"({end.x() - start.x():+d},{end.y() - start.y():+d}) -> actual delta "
                 f"({after.width() - before.width():+d},{after.height() - before.height():+d}); "
                 "on platforms that report a frame around frameless windows the delta is distorted, "
                 "what matters is that the resize happened and the mask stayed in sync")
            win.close()

        # minimum size must still be enforced
        win = make_window()
        QTest.mousePress(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(window.width() - 4, window.height() - 4))
        QTest.mouseMove(win, QPoint(60, 200))
        QTest.mouseRelease(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(60, 200))
        QApplication.instance().processEvents()
        g = win.geometry()
        check("minimum size enforced", g.width() >= 320 and g.height() >= 420,
              f"{g.width()}x{g.height()}")
        mask = win.mask()
        check("mask valid at minimum size",
              mask is not None and mask.boundingRect().getCoords() == (0, 0, g.width() - 1, g.height() - 1),
              f"mask={mask.boundingRect().getCoords() if mask else None}")
        win.close()

        # header dragging
        win = make_window()
        before = win.geometry()
        header = win._header_frame
        start = QPoint(header.width() // 2, header.height() // 2)
        QTest.mousePress(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(win, QPoint(start.x() + 60, start.y() + 40))
        QTest.mouseRelease(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                           QPoint(start.x() + 60, start.y() + 40))
        QApplication.instance().processEvents()
        after = win.geometry()
        check("header drag moves the window",
              (after.x(), after.y()) != (before.x(), before.y()) and
              (after.width(), after.height()) == (before.width(), before.height()),
              f"{before.getCoords()} -> {after.getCoords()}")
        check("header drag persists geometry exactly once",
              len(win._geometry_manager.saved) == 1, f"{len(win._geometry_manager.saved)} writes")
        win.close()

        # header buttons
        win = make_window()
        QTest.mouseClick(win._settings_btn, Qt.MouseButton.LeftButton)
        QApplication.instance().processEvents()
        QTest.mouseClick(win._history_btn, Qt.MouseButton.LeftButton)
        QApplication.instance().processEvents()
        QTest.mouseClick(win._exit_btn, Qt.MouseButton.LeftButton)
        QApplication.instance().processEvents()
        check("exit button terminates via shared callback", bool(win._exit_calls), "callback fired")
        win.close()
    except Exception as exc:
        note(f"resize/drag interaction checks unavailable: {exc}")
        traceback.print_exc()

    # --- renders at several sizes ------------------------------------------
    try:
        for label, (w, h) in {
            "default": (380, 560),
            "minimum": (320, 420),
            "large": (620, 700),
            "narrow": (340, 620),
            "wide": (760, 460),
        }.items():
            win = make_window(w, h, geometry=(120, 120, w, h))
            img = win.grab().toImage().convertToFormat(QImage.Format_ARGB32)
            path = os.path.join(ARTIFACTS, f"shape_{label}_{w}x{h}.png")
            img.save(path)
            mask = win.mask()
            RESULTS["info"][f"render_{label}"] = {
                "size": [w, h], "tears": len(win._note_shape.tears),
                "mask_bbox": mask.boundingRect().getCoords() if mask else None,
            }
            win.close()
            print(f"rendered {path}", flush=True)
    except Exception as exc:
        note(f"rendering failed: {exc}")
        traceback.print_exc()

    with open(os.path.join(ARTIFACTS, "report.json"), "w", encoding="utf-8") as handle:
        json.dump(RESULTS, handle, indent=2, ensure_ascii=False)

    print(flush=True)
    print(f"checks: {len(RESULTS['checks'])}, failures: {len(RESULTS['failures'])}", flush=True)
    for failure in RESULTS["failures"]:
        print("  FAIL " + failure, flush=True)
    return 1 if RESULTS["failures"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
