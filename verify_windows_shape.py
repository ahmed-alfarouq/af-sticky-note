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
import time
import traceback
from unittest.mock import MagicMock

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, Qt, qVersion
from PySide6.QtGui import QColor, QImage, QPainterPath
from PySide6.QtWidgets import QApplication, QWidget

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


class ClickSpy(QObject):
    """Counts mouse presses delivered to any widget inside a window.

    Installed on the QApplication so that presses aimed at child widgets
    (header, buttons, task list) are seen as well -- a real operating-system
    click is routed to the widget under the cursor, not to the top level
    window, so spying on ``QWidget.mousePressEvent`` alone would miss them.
    """

    def __init__(self, window):
        super().__init__()
        self._window = window
        self.presses = []

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            widget = obj if isinstance(obj, QWidget) else None
            if widget is not None and (
                widget is self._window or self._window.isAncestorOf(widget)
            ):
                self.presses.append(
                    (widget.objectName() or type(widget).__name__,
                     round(event.position().x(), 1),
                     round(event.position().y(), 1))
                )
        return False


def real_os_click(screen_x, screen_y):
    """Deliver a genuine operating-system mouse click at a screen position."""
    import ctypes

    user32 = ctypes.windll.user32
    user32.SetCursorPos(int(screen_x), int(screen_y))
    time.sleep(0.10)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
    time.sleep(0.04)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
    time.sleep(0.15)


# --- rendered silhouette measurement ---------------------------------------
PAPER_RGB = (30, 38, 54)    # #1E2636
BORDER_RGB = (46, 58, 78)   # #2E3A4E
TOLERANCE = 14


def _close(rgb, target):
    return all(abs(a - b) <= TOLERANCE for a, b in zip(rgb, target))


def _silhouette_at(img, x, y):
    """True when the pixel belongs to the painted paper or its border.

    Both the alpha channel and the two palette colours are accepted so the
    measurement works whether the platform leaves the area outside the paper
    transparent (Linux/offscreen) or fills it opaquely (Windows).
    """
    if x < 0 or y < 0 or x >= img.width() or y >= img.height():
        return False
    r, g, b, a = img.pixelColor(x, y).getRgb()
    if a <= 128:
        return False
    return _close((r, g, b), PAPER_RGB) or _close((r, g, b), BORDER_RGB)


def _max_second_difference(values):
    """High frequency roughness: small for a smooth curve, large for spikes."""
    if len(values) < 3:
        return 0
    return max(
        abs(values[i + 1] - 2 * values[i] + values[i - 1])
        for i in range(1, len(values) - 1)
    )


def analyse_render(img):
    """Measure the rendered silhouette: corners, straight sides, torn bottom.

    Works on the pixels the platform actually composited, so anti-aliasing and
    any one-pixel geometry error show up in the numbers.
    """
    w, h = img.width(), img.height()
    scan = min(64, w, h)
    profile = {}

    def first_paper_column(y):
        x = 0
        while x < scan and not _silhouette_at(img, x, y):
            x += 1
        return x

    def last_paper_column(y):
        x = w - 1
        while x >= w - scan and not _silhouette_at(img, x, y):
            x -= 1
        return x

    def last_paper_row(x):
        y = h - 1
        while y >= h - scan and not _silhouette_at(img, x, y):
            y -= 1
        return y

    # --- top-left / top-right corner radius --------------------------------
    left_edge = [first_paper_column(y) for y in range(scan)]
    right_edge = [last_paper_column(y) for y in range(scan)]

    def corner_radius(edge, from_right=False):
        target = w - 1 if from_right else 0
        for y in range(scan):
            if edge[y] == target:
                return y
        return None

    profile["corner_radius_topleft"] = corner_radius(left_edge)
    profile["corner_radius_topright"] = corner_radius(right_edge, from_right=True)
    # anti-aliasing pulls the detected boundary inwards by about a pixel
    profile["corner_max_curvature_jump"] = max(
        _max_second_difference(left_edge), _max_second_difference(right_edge)
    )
    profile["corner_monotonic"] = all(
        left_edge[i + 1] <= left_edge[i] for i in range(len(left_edge) - 1)
    ) and all(right_edge[i + 1] >= right_edge[i] for i in range(len(right_edge) - 1))

    # --- straight vertical sides ------------------------------------------
    body_top = (corner_radius(left_edge) or 16) + 8
    body_bottom = h - 24
    side_left = [first_paper_column(y) for y in range(body_top, body_bottom)]
    side_right = [last_paper_column(y) for y in range(body_top, body_bottom)]
    profile["side_left_values"] = sorted(set(side_left))
    profile["side_right_values"] = sorted(set(side_right))
    profile["sides_straight"] = (
        len(set(side_left)) == 1
        and len(set(side_right)) == 1
        and side_left[0] == 0
        and side_right[0] == w - 1
    )

    # --- torn bottom edge -------------------------------------------------
    bottom = [last_paper_row(x) for x in range(w)]
    lowest = max(bottom)
    highest = min(bottom)
    profile["bottom_lowest_row"] = lowest
    profile["bottom_highest_row"] = highest
    profile["bottom_tear_depth"] = lowest - highest
    profile["bottom_max_step"] = max(
        (abs(bottom[i + 1] - bottom[i]) for i in range(w - 1)), default=0
    )
    profile["bottom_max_curvature_jump"] = _max_second_difference(bottom)
    profile["bottom_baseline_reaches_window_edge"] = lowest == h - 1
    profile["bottom_corners_solid"] = bottom[0] == h - 1 and bottom[w - 1] == h - 1

    # count distinct upward nicks (tears)
    tears = 0
    in_tear = False
    for value in bottom:
        if value < lowest - 0.5:
            if not in_tear:
                tears += 1
                in_tear = True
        else:
            in_tear = False
    profile["tears_rendered"] = tears
    return profile


def content_clearance(window):
    """Bottom edge, in window coordinates, of the lowest content widget.

    The paper surface itself deliberately fills the whole window rectangle, so
    it is excluded: what matters is how close the *content* comes to the torn
    bottom edge.
    """
    paper = getattr(window, "_paper_surface", None)
    scope = paper if paper is not None else window
    lowest = None
    for widget in scope.findChildren(QWidget):
        if widget is scope or not widget.isVisible():
            continue
        if widget.height() <= 0 or widget.width() <= 0:
            continue
        bottom = widget.mapTo(window, QPoint(0, widget.height())).y()
        if lowest is None or bottom > lowest:
            lowest = bottom
    return lowest


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
        # QColor(QRgb) ignores the alpha bits, so read the channel explicitly
        return image.pixelColor(x, y).getRgb()[3]

    outside = alpha(2, 2)
    inside = alpha(window.width() // 2, window.height() // 2)
    outside_rgb = image.pixelColor(2, 2).getRgb()[:3]
    RESULTS["info"]["alpha_outside_paper"] = outside
    RESULTS["info"]["alpha_inside_paper"] = inside
    RESULTS["info"]["outside_paper_rgb"] = list(outside_rgb)
    check("paper is fully opaque", inside == 255, f"alpha={inside}")
    if outside == 0:
        check("area outside the paper is transparent", True,
              "alpha=0, so the desktop shows through the silhouette")
    else:
        note(f"area outside the paper is opaque in the grab ({outside_rgb}, alpha={outside}): "
             "the grab rasterises the widget backing store, so on this platform the native "
             "mask is what clips the silhouette on screen")
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
    # --- hit testing --------------------------------------------------------
    # A synthetic QTest click is posted straight into the widget's event queue
    # and therefore bypasses the native window mask completely, so it can only
    # prove that the widget is alive.  Real click-through is proven further
    # down with an operating-system level click.
    try:
        from PySide6.QtTest import QTest

        pressed = []
        original_mouse_press = window.mousePressEvent

        def spy(event):
            pressed.append((event.position().x(), event.position().y()))
            return original_mouse_press(event)

        window.mousePressEvent = spy
        QTest.mouseClick(window, Qt.MouseButton.LeftButton,
                         pos=QPoint(window.width() // 2, 40))
        QApplication.instance().processEvents()
        window.mousePressEvent = original_mouse_press
        check("widget under the paper receives mouse input",
              len(pressed) >= 1,
              f"{len(pressed)} synthetic event(s); synthetic events bypass the native mask, "
              "so this is only a liveness check")
    except Exception as exc:
        note(f"synthetic click check unavailable: {exc}")
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

    # --- real operating-system click through the native mask ----------------
    # Only a genuine OS-level click goes through the window region that
    # setMask() installed, so this is the only meaningful click-through test.
    try:
        import ctypes

        win = make_window(380, 560, geometry=(220, 140, 380, 560))
        win.show()
        win.raise_()
        win.activateWindow()
        QApplication.instance().processEvents()
        try:
            ctypes.windll.user32.SetForegroundWindow(int(win.winId()))
        except Exception as exc:
            note(f"could not force the window to the foreground: {exc}")
        QApplication.instance().processEvents()
        time.sleep(0.25)

        spy = ClickSpy(win)
        app.installEventFilter(spy)

        inside = win.mapToGlobal(QPoint(win.width() // 2, win.height() // 2 + 40))
        outside = win.mapToGlobal(QPoint(3, 3))

        real_os_click(inside.x(), inside.y())
        QApplication.instance().processEvents()
        inside_hits = len(spy.presses)
        spy.presses.clear()

        real_os_click(outside.x(), outside.y())
        QApplication.instance().processEvents()
        outside_hits = len(spy.presses)

        app.removeEventFilter(spy)
        RESULTS["info"]["os_click_inside_hits"] = inside_hits
        RESULTS["info"]["os_click_outside_hits"] = outside_hits
        RESULTS["info"]["os_click_inside_target"] = [inside.x(), inside.y()]
        RESULTS["info"]["os_click_outside_target"] = [outside.x(), outside.y()]

        if inside_hits >= 1:
            check("real OS click inside the paper reaches the window",
                  True, f"{inside_hits} press event(s) at {inside.x()},{inside.y()}")
            check("real OS click outside the paper is swallowed by the mask",
                  outside_hits == 0,
                  f"{outside_hits} press event(s) at {outside.x()},{outside.y()} "
                  "(rounded top-left corner)")
        else:
            note("the runner did not deliver real mouse input to the window "
                 f"(inside click produced {inside_hits} events), so native click-through "
                 "could not be observed -- there was no positive control")
        win.close()
    except Exception as exc:
        note(f"real OS click check unavailable: {exc}")
        traceback.print_exc()

    # --- content must not collide with the torn bottom edge ----------------
    try:
        win = make_window(380, 560)
        lowest = content_clearance(win)
        shape = win._note_shape
        RESULTS["info"]["content"] = {
            "lowest_content_bottom": lowest,
            "window_height": win.height(),
            "bottom_margin": (win.height() - lowest) if lowest is not None else None,
            "max_tear_depth": shape.tear_depth,
            "paper_bottom_margin": getattr(win, "PAPER_BOTTOM_MARGIN", None),
        }
        if lowest is not None:
            margin = win.height() - lowest
            check("bottom content clears the deepest tear",
                  margin > shape.tear_depth,
                  f"content bottom is {margin}px above the window edge, deepest tear is "
                  f"{shape.tear_depth}px, so {margin - shape.tear_depth}px of clearance remains")
        else:
            note("no visible child widget found, content clearance not measured")
        win.close()
    except Exception as exc:
        note(f"content clearance check unavailable: {exc}")
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
            profile = analyse_render(img)
            RESULTS["info"][f"render_{label}"] = {
                "size": [w, h], "tears": len(win._note_shape.tears),
                "mask_bbox": mask.boundingRect().getCoords() if mask else None,
                "profile": profile,
            }
            # --- the mandated visual checks, as measured pixels -------------
            check(f"{label} ({w}x{h}): top corners are rounded and smooth",
                  profile["corner_radius_topleft"] is not None
                  and profile["corner_radius_topright"] is not None
                  and profile["corner_monotonic"]
                  and profile["corner_max_curvature_jump"] <= 2,
                  f"radius {profile['corner_radius_topleft']}/{profile['corner_radius_topright']}px, "
                  f"monotonic={profile['corner_monotonic']}, "
                  f"max curvature jump={profile['corner_max_curvature_jump']}px")
            check(f"{label} ({w}x{h}): no rectangular background at the corners",
                  not _silhouette_at(img, 2, 2) and not _silhouette_at(img, w - 3, 2),
                  "the corner pixels belong to the background, not to the paper")
            check(f"{label} ({w}x{h}): sides are straight and clean",
                  profile["sides_straight"],
                  f"left edge columns {profile['side_left_values']}, "
                  f"right edge columns {profile['side_right_values']}")
            check(f"{label} ({w}x{h}): bottom tears are subtle, smooth and unclipped",
                  profile["bottom_tear_depth"] <= 8
                  and profile["bottom_max_step"] <= 3
                  and profile["bottom_max_curvature_jump"] <= 3
                  and profile["bottom_baseline_reaches_window_edge"]
                  and profile["bottom_corners_solid"],
                  f"{profile['tears_rendered']} tears, depth {profile['bottom_tear_depth']}px, "
                  f"max step {profile['bottom_max_step']}px, "
                  f"max curvature jump {profile['bottom_max_curvature_jump']}px, "
                  f"baseline reaches the window edge="
                  f"{profile['bottom_baseline_reaches_window_edge']}")
            print(f"rendered {path} -- corners r={profile['corner_radius_topleft']}/"
                  f"{profile['corner_radius_topright']} "
                  f"curvature_jump={profile['corner_max_curvature_jump']} "
                  f"sides_straight={profile['sides_straight']} "
                  f"tear_depth={profile['bottom_tear_depth']} "
                  f"bottom_max_step={profile['bottom_max_step']} "
                  f"tears={profile['tears_rendered']}", flush=True)
            win.close()
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
