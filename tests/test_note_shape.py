"""Tests for Phase 6B -- the organic sticky-note paper silhouette.

Two groups of tests:

* Pure geometry tests for :mod:`app.ui.note_shape`. These run everywhere,
  including the backend suite that is executed without PySide6 installed.
* Qt tests for the painting, the window mask and the MainWindow lifecycle.
  These no-op (rather than fail) when PySide6 is unavailable, following the
  convention used by the rest of this project's UI tests.

What is deliberately asserted here:

* the silhouette is deterministic, stays inside the window and never leaves
  the paper (so content and resize edges keep working),
* the bottom edge is irregular (not a uniform waveform) and subtle,
* the window mask follows the painted shape and is refreshed on resize --
  but never while painting,
* the window flags, minimum size, header controls and geometry persistence
  of Phase 5 are untouched by the new shape.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional, Tuple

import pytest

from app.ui.note_shape import (
    DEFAULT_CORNER_RADIUS,
    DEFAULT_SEGMENT_WIDTH,
    DEFAULT_TEAR_DEPTH,
    MAX_SEGMENTS,
    MIN_SEGMENTS,
    NoteShape,
    build_note_shape,
    inset_note_shape,
)

# ---------------------------------------------------------------------------
# Optional Qt support (the backend suite must run without PySide6)
# ---------------------------------------------------------------------------
try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    """Return True when the Qt half of these tests should be skipped."""
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


def _commands(shape: NoteShape) -> List[Tuple]:
    return [tuple(command) for command in shape.commands]


# ---------------------------------------------------------------------------
# Pure geometry
# ---------------------------------------------------------------------------


def test_shape_reports_the_requested_geometry():
    shape = build_note_shape(380.0, 560.0)

    assert shape.width == 380.0
    assert shape.height == 560.0
    assert shape.corner_radius == DEFAULT_CORNER_RADIUS
    assert shape.tear_depth == DEFAULT_TEAR_DEPTH
    # The paper reaches the bottom of the window: the organic edge is cut
    # into the paper from the baseline, never below the window.
    assert shape.baseline_y == 560.0
    assert shape.bounds == (0.0, 0.0, 380.0, 560.0)


def test_shape_is_deterministic_for_the_same_size():
    first = build_note_shape(380.0, 560.0)
    second = build_note_shape(380.0, 560.0)

    assert _commands(first) == _commands(second)
    assert first.tears == second.tears


def test_shape_differs_between_sizes_and_seeds():
    default_shape = build_note_shape(380.0, 560.0)
    other_size = build_note_shape(500.0, 560.0)
    other_seed = build_note_shape(380.0, 560.0, seed=1234)

    assert _commands(default_shape) != _commands(other_size)
    assert _commands(default_shape) != _commands(other_seed)


def test_invalid_dimensions_are_rejected():
    with pytest.raises(ValueError):
        build_note_shape(0.0, 560.0)
    with pytest.raises(ValueError):
        build_note_shape(380.0, -1.0)


def test_corner_radius_is_clamped_for_small_notes():
    shape = build_note_shape(40.0, 30.0, corner_radius=16.0)
    assert shape.corner_radius == 15.0  # min(width, height) / 2
    assert shape.corner_radius <= min(shape.width, shape.height) / 2.0


def test_top_corners_are_rounded_not_sharp():
    shape = build_note_shape(380.0, 560.0)
    commands = _commands(shape)

    # Starts on the top edge, after the left corner radius.
    assert commands[0] == ("M", shape.corner_radius, 0.0)
    assert commands[1] == ("L", shape.width - shape.corner_radius, 0.0)

    # The top-right corner is the first cubic and the top-left corner is the
    # last one before the closing point: both are arcs, not sharp corners.
    assert commands[2][0] == "C"
    assert commands[-2][0] == "C"
    assert commands[2][5:7] == (shape.width, shape.corner_radius)
    assert commands[-2][5:7] == (shape.corner_radius, 0.0)

    # No point of the outline sits on either raw top corner.
    for command in commands:
        if command[0] in ("M", "L"):
            assert (command[1], command[2]) != (0.0, 0.0)
            assert (command[1], command[2]) != (shape.width, 0.0)

    # The top edge is straight between the two corners.
    assert commands[1][1] == shape.width - shape.corner_radius
    assert commands[1][2] == 0.0


def test_vertical_sides_are_straight():
    shape = build_note_shape(380.0, 560.0)
    commands = _commands(shape)

    # Right side: one straight line from the top-right corner down to the
    # bottom edge. Left side: one straight line back up to the top-left
    # corner. Everything else in the outline is a corner arc or bottom edge.
    assert ("L", shape.width, shape.baseline_y) in commands
    assert ("L", 0.0, shape.corner_radius) in commands

    for command in commands:
        if command[0] in ("M", "L"):
            on_side = command[1] in (0.0, shape.width)
            on_top_or_bottom = command[2] in (0.0, shape.baseline_y)
            assert on_side or on_top_or_bottom, command


def test_bottom_edge_is_cut_into_the_paper_and_stays_inside_the_window():
    for size in ((320.0, 420.0), (380.0, 560.0), (700.0, 620.0), (1200.0, 400.0)):
        shape = build_note_shape(*size)
        assert shape.tears, "a note of this size should have at least one tear"

        for left, right, depth in shape.tears:
            assert 0.0 <= left < right <= shape.width
            assert 0.0 < depth <= shape.tear_depth

        # Nothing may be drawn below the window: the outline is bounded by
        # the baseline, which is the bottom of the window.
        for command in shape.commands:
            if command[0] in ("M", "L"):
                assert command[2] <= shape.baseline_y
            elif command[0] == "C":
                assert command[2] <= shape.baseline_y
                assert command[4] <= shape.baseline_y
                assert command[6] <= shape.baseline_y


def test_bottom_edge_is_irregular_not_a_waveform():
    shape = build_note_shape(700.0, 620.0)
    depths = [round(depth, 3) for _, _, depth in shape.tears]
    widths = [round(right - left, 3) for left, right, _ in shape.tears]

    # More than one tear, and no two of them are identical.
    assert len(shape.tears) >= 3
    assert len(set(depths)) > 1
    assert len(set(widths)) > 1

    # Tears never overlap and never touch each other.
    ordered = sorted(shape.tears, key=lambda tear: tear[0])
    for (_, previous_right, _), (next_left, _, _) in zip(ordered, ordered[1:]):
        assert next_left >= previous_right

    # The segment count is derived from the width, within sane bounds.
    assert MIN_SEGMENTS <= shape.segment_count <= MAX_SEGMENTS


def test_bottom_edge_keeps_most_of_its_length_solid():
    """Most of the bottom edge must stay straight, grabbable paper.

    This is what keeps bottom-edge resizing usable once the window mask
    follows the silhouette.
    """
    for size in ((320.0, 420.0), (380.0, 560.0), (700.0, 620.0)):
        shape = build_note_shape(*size)
        torn = sum(right - left for left, right, _ in shape.tears)
        assert torn / shape.width < 0.35, f"too much of the bottom edge is torn: {torn:.0f}/{shape.width:.0f}"


def test_minimum_window_size_produces_a_valid_shape():
    shape = build_note_shape(320.0, 420.0)

    assert shape.commands
    assert shape.commands[0][0] == "M"
    assert shape.commands[-1] == ("Z",)
    assert shape.bounds == (0.0, 0.0, 320.0, 420.0)
    assert 0.0 < shape.corner_radius <= 16.0


def test_path_commands_are_well_formed():
    shape = build_note_shape(380.0, 560.0)
    expected_lengths = {"M": 3, "L": 3, "C": 7, "Z": 1}

    for command in shape.commands:
        op = command[0]
        assert op in expected_lengths
        assert len(command) == expected_lengths[op]
        for value in command[1:]:
            assert isinstance(value, float)

    # Exactly one move, one close, and every line/cubic is reachable.
    ops = [command[0] for command in shape.commands]
    assert ops.count("M") == 1
    assert ops.count("Z") == 1
    assert ops[-1] == "Z"


def test_segment_count_scales_with_width():
    narrow = build_note_shape(200.0, 400.0)
    wide = build_note_shape(2000.0, 400.0)

    assert narrow.segment_count == MIN_SEGMENTS
    assert wide.segment_count == MAX_SEGMENTS


def test_inset_shape_is_strictly_inside_the_original():
    shape = build_note_shape(380.0, 560.0)
    inner = inset_note_shape(shape, 0.75)

    assert inner is not None
    assert inner.width == shape.width - 1.5
    assert inner.height == shape.height - 1.5
    assert inner.corner_radius == shape.corner_radius - 0.75
    assert inner.baseline_y < shape.baseline_y
    assert inner.commands != shape.commands


def test_inset_shape_returns_none_when_the_note_is_too_small():
    tiny = build_note_shape(6.0, 6.0)
    assert inset_note_shape(tiny, 2.0) is None
    # A zero inset is a no-op rather than a failure.
    assert inset_note_shape(build_note_shape(380.0, 560.0), 0.0) is not None


def test_translate_moves_every_command():
    shape = build_note_shape(380.0, 560.0)
    moved = shape.translate(10.0, 20.0)

    assert moved.baseline_y == shape.baseline_y + 20.0
    assert moved.bounds == (0.0, 0.0, 380.0, 580.0)
    for original, shifted in zip(shape.commands, moved.commands):
        assert original[0] == shifted[0]
        if original[0] in ("M", "L"):
            assert (shifted[1], shifted[2]) == (original[1] + 10.0, original[2] + 20.0)
        elif original[0] == "C":
            assert shifted[5] == original[5] + 10.0
            assert shifted[6] == original[6] + 20.0


def test_default_segment_width_is_small_enough_for_fine_tears():
    # A sanity check on the tuning: segments should be narrow enough that a
    # tear stays a small nick rather than a wide bite out of the paper.
    assert DEFAULT_SEGMENT_WIDTH <= 48.0


# ---------------------------------------------------------------------------
# Qt: path, region and painting
# ---------------------------------------------------------------------------


def test_painter_path_follows_the_silhouette():
    if _skip_without_qt():
        return

    from app.ui.widgets.paper_surface import shape_to_painter_path

    shape = build_note_shape(380.0, 560.0)
    path = shape_to_painter_path(shape)

    # Deep inside the paper.
    assert path.contains(QPointF(190.0, 280.0))
    # The rounded top-left corner is not part of the paper.
    assert not path.contains(QPointF(1.0, 1.0))
    assert not path.contains(QPointF(190.0, 1.0)) is False  # top edge is paper
    # Just below the top edge, on the left side.
    assert path.contains(QPointF(2.0, 100.0))
    assert path.contains(QPointF(378.0, 100.0))


def test_window_mask_follows_the_paper_silhouette():
    if _skip_without_qt():
        return

    from app.ui.widgets.paper_surface import shape_to_region

    shape = build_note_shape(380.0, 560.0)
    region = shape_to_region(shape)

    assert region.contains(QPoint(190, 280))       # middle of the paper
    assert not region.contains(QPoint(1, 1))       # rounded top-left corner
    assert not region.contains(QPoint(378, 1))     # rounded top-right corner
    assert region.contains(QPoint(0, 559))         # solid bottom-left corner
    assert region.contains(QPoint(379, 559))       # solid bottom-right corner

    # The tears punch real holes into the mask: the last row of the window is
    # narrower than a row well inside the paper.
    width, height = int(shape.width), int(shape.height)
    last_row = sum(1 for x in range(width) if region.contains(QPoint(x, height - 1)))
    inner_row = sum(1 for x in range(width) if region.contains(QPoint(x, height - 20)))
    assert last_row < inner_row, "the organic bottom edge must not be masked away"


def test_window_mask_keeps_the_resize_bands_usable():
    if _skip_without_qt():
        return

    from app.ui.widgets.paper_surface import shape_to_region

    for width, height in ((320, 420), (380, 560), (700, 620), (1000, 500)):
        shape = build_note_shape(float(width), float(height))
        region = shape_to_region(shape)
        band = 8  # MainWindow.RESIZE_BORDER_WIDTH

        def coverage(x0: int, x1: int, y0: int, y1: int) -> float:
            total = inside = 0
            for y in range(max(0, y0), min(height, y1)):
                for x in range(max(0, x0), min(width, x1)):
                    total += 1
                    inside += 1 if region.contains(QPoint(x, y)) else 0
            return inside / total if total else 0.0

        assert coverage(0, band, 0, height) > 0.9, "left resize band must stay usable"
        assert coverage(width - band, width, 0, height) > 0.9, "right resize band must stay usable"
        assert coverage(0, width, 0, band) > 0.9, "top resize band must stay usable"
        assert coverage(0, width, height - band, height) > 0.9, "bottom resize band must stay usable"


def test_paper_surface_paints_the_paper_along_the_path():
    if _skip_without_qt():
        return

    from app.ui.widgets.paper_surface import PaperSurface
    from app.ui.styles.app_style import COLOR_STICKY_PAPER

    _qt_app()
    surface = PaperSurface()
    surface.resize(380, 560)
    surface.set_shape(build_note_shape(380.0, 560.0))

    image = QImage(380, 560, QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    surface.render(image)

    def pixel(x: int, y: int) -> QColor:
        return QColor(image.pixel(x, y))

    expected = QColor(COLOR_STICKY_PAPER)
    # Paper is painted inside the silhouette ...
    assert pixel(190, 280).getRgb()[:3] == expected.getRgb()[:3]
    # ... and the rounded corner is not painted as part of the paper.
    assert pixel(1, 1).getRgb()[:3] != expected.getRgb()[:3]


def test_paper_surface_keeps_its_object_name_for_the_stylesheet():
    if _skip_without_qt():
        return

    from app.ui.widgets.paper_surface import PaperSurface

    surface = PaperSurface()
    assert surface.objectName() == "stickyNoteFrame"
    assert surface.autoFillBackground() is False


# ---------------------------------------------------------------------------
# Qt: MainWindow integration
# ---------------------------------------------------------------------------


class _FakeGeometryManager:
    """Records geometry writes so persistence can be asserted without QSettings."""

    def __init__(self, geometry: Tuple[int, int, int, int] = (60, 60, 380, 560)) -> None:
        self._geometry = geometry
        self.saved: List[Tuple[int, int, int, int]] = []

    def get_validated_geometry(self) -> Tuple[int, int, int, int]:
        return self._geometry

    def save_geometry(self, x: int, y: int, width: int, height: int) -> None:
        self.saved.append((x, y, width, height))


def _make_window(
    geometry_manager=None,
    on_exit_requested=None,
    width: int = 380,
    height: int = 560,
):
    from unittest.mock import MagicMock

    from app.core.models import Day
    from app.core.services.task_service import TaskService
    from app.ui.windows.main_window import MainWindow

    day = Day(id=1, date="2026-09-27", quote_text="اقتباس", created_at="now", updated_at="now")
    window = MainWindow(
        day=day,
        quote_text=day.quote_text,
        task_service=MagicMock(spec=TaskService),
        geometry_manager=geometry_manager or _FakeGeometryManager(),
        on_exit_requested=on_exit_requested or MagicMock(),
    )
    window.resize(width, height)
    return window


def test_main_window_builds_a_shape_for_its_size():
    if _skip_without_qt():
        return

    _qt_app()
    window = _make_window()
    window.show()
    QApplication.instance().processEvents()

    assert window._note_shape is not None
    assert window._note_shape.width == float(window.width())
    assert window._note_shape.height == float(window.height())
    assert window._paper_surface.shape is window._note_shape


def test_main_window_mask_follows_the_window_size():
    if _skip_without_qt():
        return

    _qt_app()
    window = _make_window()
    window.show()
    QApplication.instance().processEvents()

    mask = window.mask()
    assert mask is not None
    assert mask.boundingRect().getCoords() == (0, 0, window.width() - 1, window.height() - 1)
    assert mask.contains(QPoint(int(window.width() / 2), int(window.height() / 2)))
    assert not mask.contains(QPoint(1, 1))

    # Resize: the mask must be rebuilt for the new size, not left stale.
    window.resize(520, 700)
    QApplication.instance().processEvents()

    resized_mask = window.mask()
    assert resized_mask is not None
    assert resized_mask.boundingRect().getCoords() == (0, 0, 519, 699)
    assert resized_mask.contains(QPoint(260, 350))
    assert resized_mask.contains(QPoint(519, 699))     # solid bottom-right corner
    assert not resized_mask.contains(QPoint(1, 1))     # rounded corner stays outside
    assert window._note_shape.width == 520.0


def test_main_window_shape_regenerates_after_a_resize_but_not_while_painting():
    if _skip_without_qt():
        return

    _qt_app()
    window = _make_window()
    window.show()
    QApplication.instance().processEvents()

    calls: List[object] = []
    original_set_mask = window.setMask

    def spy(mask):  # pragma: no cover - trivial wrapper
        calls.append(mask)
        original_set_mask(mask)

    window.setMask = spy  # type: ignore[method-assign]

    window.resize(600, 640)
    QApplication.instance().processEvents()
    after_resize = len(calls)
    assert after_resize >= 1, "resizing must refresh the window mask"

    shape_after_resize = window._note_shape
    assert shape_after_resize is not None

    # A plain repaint must not rebuild the shape nor re-create the mask.
    window._paper_surface.update()
    window.update()
    QApplication.instance().processEvents()

    assert len(calls) == after_resize, "paintEvent must never touch the window mask"
    assert window._note_shape is shape_after_resize


def test_main_window_keeps_its_minimum_size_and_window_flags():
    if _skip_without_qt():
        return

    _qt_app()
    window = _make_window()

    # Desktop-layer / taskbar behaviour depends on these flags staying put.
    flags = window.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.Tool
    assert not flags & Qt.WindowType.WindowStaysOnTopHint
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # Minimum size is unchanged, and the silhouette is valid at that size.
    assert window.minimumSize().width() == 320
    assert window.minimumSize().height() == 420
    window.show()
    QApplication.instance().processEvents()
    window.resize(320, 420)
    QApplication.instance().processEvents()
    assert window._note_shape.width == 320.0
    assert window._note_shape.height == 420.0
    assert window.mask().contains(QPoint(160, 210))


def test_main_window_content_stays_inside_the_paper():
    if _skip_without_qt():
        return

    _qt_app()
    window = _make_window(width=380, height=560)
    window.show()
    QApplication.instance().processEvents()

    width, height = window.width(), window.height()
    deepest_tear = max((depth for _, _, depth in window._note_shape.tears), default=0.0)
    # Content must stop above the deepest nick in the organic bottom edge.
    bottom_limit = height - deepest_tear

    for attribute in ("_header_frame", "_quote_widget", "_task_list", "_task_input"):
        geometry = getattr(window, attribute).geometry()
        assert geometry.left() >= 0
        assert geometry.right() <= width
        assert geometry.top() >= 0
        assert geometry.bottom() <= bottom_limit, (
            f"{attribute} overlaps the organic bottom edge"
        )


def test_main_window_header_controls_remain_independent_interactions():
    if _skip_without_qt():
        return

    from unittest.mock import MagicMock

    _qt_app()
    exit_callback = MagicMock()
    window = _make_window(on_exit_requested=exit_callback)
    window.show()
    QApplication.instance().processEvents()

    # Header (the drag area) is inside the paper and separate from the buttons.
    header = window._header_frame.geometry()
    assert window._note_shape is not None
    assert header.left() >= 0 and header.right() <= window.width()

    for button in (window._settings_btn, window._history_btn, window._exit_btn):
        assert button.geometry().intersects(header)

    # The three controls are distinct widgets with distinct accessible names.
    names = {window._settings_btn.accessibleName(), window._history_btn.accessibleName(),
             window._exit_btn.accessibleName()}
    assert len(names) == 3

    # Exit still routes through the shared shutdown callback.
    window._on_exit_clicked()
    exit_callback.assert_called_once()
    assert window._allow_window_close is True


def test_main_window_resize_does_not_write_geometry():
    if _skip_without_qt():
        return

    _qt_app()
    geometry_manager = _FakeGeometryManager()
    window = _make_window(geometry_manager=geometry_manager)
    window.show()
    QApplication.instance().processEvents()

    window.resize(500, 660)
    QApplication.instance().processEvents()

    # Geometry is persisted on drag/resize *release* only; a resize must not
    # trigger a settings write by itself.
    assert geometry_manager.saved == []


def test_main_window_restores_geometry_and_derives_the_shape_from_it():
    if _skip_without_qt():
        return

    _qt_app()
    geometry_manager = _FakeGeometryManager(geometry=(120, 80, 420, 640))
    window = _make_window(geometry_manager=geometry_manager, width=420, height=640)
    window.show()
    QApplication.instance().processEvents()

    assert window.geometry().getRect() == (120, 80, 420, 640)
    assert window._note_shape.width == 420.0
    assert window._note_shape.height == 640.0


def test_shape_modules_stay_free_of_platform_specific_code():
    """The silhouette must stay portable: no Win32/ctypes anywhere near it."""
    project_root = Path(__file__).resolve().parent.parent
    for relative in ("app/ui/note_shape.py", "app/ui/widgets/paper_surface.py"):
        source = (project_root / relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "ctypes" not in alias.name
                    assert "win32" not in alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "ctypes" not in module
                assert "win32" not in module


def test_shape_never_schedules_background_work():
    """The silhouette must be event driven: no timers, threads or polling."""
    project_root = Path(__file__).resolve().parent.parent
    source = (project_root / "app/ui/note_shape.py").read_text(encoding="utf-8")
    for forbidden in ("QTimer", "threading", "Thread(", "time.sleep", "while True"):
        assert forbidden not in source
