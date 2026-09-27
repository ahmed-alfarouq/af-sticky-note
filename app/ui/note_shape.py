"""Organic paper silhouette geometry for the Daily Sticky note window.

Pure geometry: no Qt, no SQL, no filesystem, no I/O. The silhouette is
described as a small tuple of path commands so that

  * the painted paper (PaperSurface),
  * the border stroke that follows it, and
  * the window mask that makes the OS window follow the same shape

all consume exactly the same description of the note's outline, and so the
whole shape algorithm can be unit tested without a GUI toolkit installed
(this project's backend suite deliberately runs without PySide6).

The silhouette is:

  * a straight top edge with moderately rounded top corners,
  * straight vertical left and right sides,
  * a bottom edge that is *not* a straight line: the baseline is straight
    and is interrupted by a handful of shallow, smooth, non-repeating
    "tears", so it reads as a torn sheet of paper rather than a sine wave
    or a sawtooth.

Design notes
------------
The bottom edge deliberately stays *on* the baseline wherever there is no
tear. That matters for two reasons:

  * it keeps the silhouette subtle and calm (the organic edge is a detail,
    never the main visual element), and
  * it keeps the bottom edge of the note grabbable: the window mask is
    derived from this exact outline, so every part of the edge that is not
    torn remains part of the window and can still be used to resize.

Each tear is a single cubic Bézier whose end tangents are horizontal, so it
blends into the straight baseline with no corner at all, and no two tears
share a width, a depth or a position.

Nothing here is exposed to the user; the tuning constants below are
internal implementation details of the paper look.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Tuning constants (internal only -- never surfaced as user configuration)
# ---------------------------------------------------------------------------

#: Radius of the two top corners. Moderate on purpose: the note must stay
#: recognisably the same sticky note as previous versions.
DEFAULT_CORNER_RADIUS = 16.0

#: Maximum depth of a bottom-edge tear, in logical pixels. Kept small so the
#: organic edge is noticeable but never becomes the main visual element, and
#: so most of the bottom edge stays solid, grabbable paper.
DEFAULT_TEAR_DEPTH = 6.0

#: Target width of one paper segment along the bottom edge.
DEFAULT_SEGMENT_WIDTH = 36.0

#: Bounds on the number of bottom-edge segments (a very narrow or very wide
#: window still gets a natural looking edge).
MIN_SEGMENTS = 6
MAX_SEGMENTS = 18

#: How often a bottom-edge segment carries a tear, and how big it may get.
TEAR_PROBABILITY = 0.5
TEAR_MIN_WIDTH = 0.24          # narrowest tear, as a fraction of its segment
TEAR_MAX_WIDTH = 0.5           # widest tear
TEAR_MIN_DEPTH = 0.35          # shallowest tear, as a fraction of tear depth
TEAR_MAX_DEPTH = 1.0           # deepest tear

#: Random spacing of the segments (uniform spacing would read as a waveform).
_MIN_SPACING = 0.7
_MAX_SPACING = 1.3

#: Fixed seed: the silhouette must be reproducible for a given window size.
SHAPE_SEED = 0x5A17

#: Quarter-circle -> cubic Bezier control point constant.
_KAPPA = 0.5522847498307936

#: One path command: ``("M", x, y)``, ``("L", x, y)``,
#: ``("C", c1x, c1y, c2x, c2y, x, y)`` or ``("Z",)``.
PathCommand = Tuple[float, ...]

#: A single bottom-edge tear: ``(left_x, right_x, depth)``.
Tear = Tuple[float, float, float]


@dataclass(frozen=True)
class NoteShape:
    """A fully resolved paper silhouette for one window size.

    ``commands`` is the single source of truth consumed by the Qt layer;
    ``tears`` describes the organic part of the bottom edge in a form that
    is easy to reason about (and to assert on in tests).
    """

    width: float
    height: float
    corner_radius: float
    tear_depth: float
    baseline_y: float
    segment_count: int
    tears: Tuple[Tear, ...]
    commands: Tuple[PathCommand, ...]
    seed: int = SHAPE_SEED

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Return ``(left, top, right, bottom)`` of the silhouette."""
        return (0.0, 0.0, self.width, self.baseline_y)

    def translate(self, dx: float, dy: float) -> "NoteShape":
        """Return a copy of this shape moved by ``(dx, dy)``."""
        return NoteShape(
            width=self.width,
            height=self.height,
            corner_radius=self.corner_radius,
            tear_depth=self.tear_depth,
            baseline_y=self.baseline_y + dy,
            segment_count=self.segment_count,
            tears=tuple((left + dx, right + dx, depth) for left, right, depth in self.tears),
            commands=tuple(_translate_command(command, dx, dy) for command in self.commands),
            seed=self.seed,
        )


def _translate_command(command: PathCommand, dx: float, dy: float) -> PathCommand:
    op = command[0]
    if op in ("M", "L"):
        return (op, command[1] + dx, command[2] + dy)
    if op == "C":
        return (
            op,
            command[1] + dx,
            command[2] + dy,
            command[3] + dx,
            command[4] + dy,
            command[5] + dx,
            command[6] + dy,
        )
    return command


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp_radius(corner_radius: float, width: float, height: float) -> float:
    """Never let the corner radius exceed what the note can physically show."""
    limit = min(width, height) / 2.0
    return _clamp(float(corner_radius), 0.0, limit)


def _segment_count(width: float) -> int:
    return int(_clamp(int(width / DEFAULT_SEGMENT_WIDTH), MIN_SEGMENTS, MAX_SEGMENTS))


def _segment_boundaries(width: float, count: int, rng: random.Random) -> List[float]:
    """Monotonic x boundaries across ``[0, width]`` with non-uniform spacing."""
    weights = [rng.uniform(_MIN_SPACING, _MAX_SPACING) for _ in range(count)]
    total = sum(weights)
    boundaries: List[float] = [0.0]
    accumulated = 0.0
    for weight in weights:
        accumulated += weight
        boundaries.append(width * (accumulated / total))
    boundaries[-1] = width  # guard against float drift at the right edge
    return boundaries


def _make_tear(
    segment_start: float,
    segment_end: float,
    tear_depth: float,
    rng: random.Random,
) -> Optional[Tear]:
    """Describe one shallow paper tear inside a bottom-edge segment.

    Returns ``None`` when this segment stays perfectly straight, which is
    what keeps most of the bottom edge (and therefore the bottom resize
    band) solid paper.
    """
    if rng.random() > TEAR_PROBABILITY:
        return None

    span = segment_end - segment_start
    tear_width = span * rng.uniform(TEAR_MIN_WIDTH, TEAR_MAX_WIDTH)
    slack = span - tear_width
    left = segment_start + (slack * rng.random() if slack > 0 else 0.0)
    depth = tear_depth * rng.uniform(TEAR_MIN_DEPTH, TEAR_MAX_DEPTH)
    return (left, left + tear_width, depth)


def _bottom_edge_commands(
    boundaries: Sequence[float],
    baseline: float,
    tear_depth: float,
    rng: random.Random,
) -> Tuple[List[PathCommand], Tuple[Tear, ...]]:
    """Build the bottom edge: straight baseline plus smooth paper tears.

    The outline is walked right -> left. Each segment either contributes a
    plain line along the baseline, or a line down to the tear followed by a
    single cubic Bezier dip. Because every tear starts and ends with a
    horizontal tangent, the dip joins the straight baseline without any
    corner, so the edge never looks like a sawtooth.
    """
    commands: List[PathCommand] = []
    tears: List[Tear] = []

    for index in range(len(boundaries) - 1, 0, -1):
        segment_start = boundaries[index - 1]
        segment_end = boundaries[index]
        tear = _make_tear(segment_start, segment_end, tear_depth, rng)

        if tear is None:
            commands.append(("L", segment_start, baseline))
            continue

        left, right, depth = tear
        tears.append(tear)
        span = right - left
        # Control points sit above the baseline (smaller y == further into
        # the paper) and a little past the tear depth, so the nick reads as a
        # rounded bite out of the paper rather than a flat-bottomed slot.
        control_y = baseline - depth * 1.15
        commands.append(("L", right, baseline))
        commands.append(
            (
                "C",
                right - span * 0.3,
                control_y,
                left + span * 0.3,
                control_y,
                left,
                baseline,
            )
        )

    # Land exactly on the left edge so the straight side can take over.
    commands.append(("L", 0.0, baseline))
    return commands, tuple(sorted(tears, key=lambda tear: tear[0]))


def _assemble_commands(
    width: float,
    height: float,
    radius: float,
    bottom_commands: Sequence[PathCommand],
) -> Tuple[PathCommand, ...]:
    """Build the closed outline: rounded top corners, straight sides, paper bottom."""
    kappa_radius = _KAPPA * radius
    baseline = height

    commands: List[PathCommand] = [
        ("M", radius, 0.0),
        ("L", width - radius, 0.0),
        # Top-right corner
        ("C", width - radius + kappa_radius, 0.0, width, radius - kappa_radius, width, radius),
        # Right side, straight down to the bottom edge
        ("L", width, baseline),
    ]
    commands.extend(bottom_commands)
    commands.extend(
        [
            # Left side, straight back up
            ("L", 0.0, radius),
            # Top-left corner
            ("C", 0.0, radius - kappa_radius, radius - kappa_radius, 0.0, radius, 0.0),
            ("Z",),
        ]
    )
    return tuple(commands)


def build_note_shape(
    width: float,
    height: float,
    corner_radius: float = DEFAULT_CORNER_RADIUS,
    tear_depth: float = DEFAULT_TEAR_DEPTH,
    seed: int = SHAPE_SEED,
    segments: Optional[int] = None,
) -> NoteShape:
    """Build the organic paper silhouette for a note of ``width`` x ``height``.

    The path is expressed in the note's own coordinate space (origin at the
    top-left of the window, y growing downwards), in logical pixels -- no
    physical-pixel or DPI assumptions are made here; the Qt layer applies its
    own device pixel ratio when painting.

    Deterministic: the same arguments always produce the same silhouette.
    """
    note_width = float(width)
    note_height = float(height)
    if note_width <= 0 or note_height <= 0:
        raise ValueError(f"Note shape requires positive dimensions, got {note_width}x{note_height}")

    radius = _clamp_radius(corner_radius, note_width, note_height)
    depth = max(0.0, float(tear_depth))
    baseline = note_height

    rng = random.Random(seed)
    count = _segment_count(note_width) if segments is None else int(segments)
    count = max(1, count)
    boundaries = _segment_boundaries(note_width, count, rng)
    bottom_commands, tears = _bottom_edge_commands(boundaries, baseline, depth, rng)
    commands = _assemble_commands(note_width, note_height, radius, bottom_commands)

    return NoteShape(
        width=note_width,
        height=note_height,
        corner_radius=radius,
        tear_depth=depth,
        baseline_y=baseline,
        segment_count=count,
        tears=tears,
        commands=commands,
        seed=seed,
    )


def inset_note_shape(shape: NoteShape, inset: float) -> Optional[NoteShape]:
    """Return ``shape`` shrunk inwards by ``inset`` logical pixels.

    Used to draw the paper border *inside* the silhouette, so the stroke is
    never clipped by the window mask and the border still follows the exact
    same outline (rounded corners and organic bottom edge included).

    Returns ``None`` when the note is too small to be inset any further.
    """
    amount = float(inset)
    if amount <= 0:
        return shape

    width = shape.width - 2.0 * amount
    height = shape.height - 2.0 * amount
    radius = shape.corner_radius - amount
    if width <= 2.0 or height <= 2.0 or radius <= 1.0:
        return None

    inner = build_note_shape(
        width,
        height,
        corner_radius=radius,
        tear_depth=shape.tear_depth,
        seed=shape.seed,
        segments=shape.segment_count,
    )
    return inner.translate(amount, amount)
