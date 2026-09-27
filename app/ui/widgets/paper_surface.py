"""Qt rendering of the organic sticky-note paper silhouette.

This module is the only place that turns a :class:`NoteShape` into Qt
objects, and the only place that paints the paper:

  * :func:`shape_to_painter_path` — the painted outline (and its border),
  * :func:`shape_to_region` — the window mask, so the *physical* OS window
    follows the same silhouette as the painted paper,
  * :class:`PaperSurface` — the widget that owns both.

Design rules this module follows:

  * The paper is painted from a **cached** path. ``paintEvent`` never
    rebuilds geometry and never touches the window mask; both are refreshed
    by :meth:`MainWindow._update_note_shape` when the window size actually
    changes (see ``app/ui/windows/main_window.py``).
  * Only Daily Sticky's own palette tokens are used — no demo colours.
  * No native/platform shadow code: a Qt drop shadow would fight the window
    mask and the desktop layering, and this phase is about the silhouette.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRegion
from PySide6.QtWidgets import QFrame

from app.ui.note_shape import NoteShape, inset_note_shape
from app.ui.styles.app_style import COLOR_STICKY_BORDER, COLOR_STICKY_PAPER

logger = logging.getLogger(__name__)

#: Width of the paper outline, in logical pixels. Deliberately subtle.
PAPER_BORDER_WIDTH = 1.5

#: How far inside the silhouette the outline is stroked, so the whole stroke
#: stays within the window mask instead of being clipped in half by it.
PAPER_BORDER_INSET = 0.75


def shape_to_painter_path(shape: NoteShape) -> QPainterPath:
    """Convert a :class:`NoteShape` into a ``QPainterPath``."""
    path = QPainterPath()
    for command in shape.commands:
        op = command[0]
        if op == "M":
            path.moveTo(command[1], command[2])
        elif op == "L":
            path.lineTo(command[1], command[2])
        elif op == "C":
            path.cubicTo(command[1], command[2], command[3], command[4], command[5], command[6])
        elif op == "Z":
            path.closeSubpath()
    return path


def shape_to_region(shape: NoteShape) -> QRegion:
    """Convert a :class:`NoteShape` into a ``QRegion`` window mask.

    ``QRegion`` has no ``QPainterPath`` constructor in PySide6, so the path
    is flattened to a polygon first. A region mask is inherently 1-bit, which
    is exactly what a window mask is; the *visual* smoothness of the edge
    comes from the anti-aliased painting, not from the mask.
    """
    polygon = shape_to_painter_path(shape).toFillPolygon().toPolygon()
    return QRegion(polygon)


class PaperSurface(QFrame):
    """The sticky note's paper: paints the organic silhouette and its border.

    Keeps the ``stickyNoteFrame`` object name so the existing stylesheet
    keeps applying (it is explicitly transparent — all paper painting is
    done here, along the shared shape).
    """

    def __init__(self, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.setObjectName("stickyNoteFrame")
        # Never let a background brush fill the rectangular frame behind the
        # paper silhouette: the paper is painted along the path, and anything
        # painted outside it would defeat both the window mask and the
        # anti-aliased edge.
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._shape: Optional[NoteShape] = None
        self._path: Optional[QPainterPath] = None
        self._border_path: Optional[QPainterPath] = None

    # ------------------------------------------------------------------
    # Shape
    # ------------------------------------------------------------------
    @property
    def shape(self) -> Optional[NoteShape]:
        """The silhouette currently painted by this surface."""
        return self._shape

    def set_shape(self, shape: NoteShape) -> None:
        """Adopt ``shape``: rebuild the cached paths and schedule a repaint.

        Called only when the window geometry changes, never per paint.
        """
        self._shape = shape
        self._path = shape_to_painter_path(shape)

        border_shape = inset_note_shape(shape, PAPER_BORDER_INSET)
        if border_shape is not None:
            self._border_path = shape_to_painter_path(border_shape)
        else:
            self._border_path = self._path

        self.update()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._path is None:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # Paper fill along the organic outline.
            painter.fillPath(self._path, QColor(COLOR_STICKY_PAPER))

            # Border follows the very same outline, stroked just inside it.
            border_path = self._border_path if self._border_path is not None else self._path
            pen = QPen(QColor(COLOR_STICKY_BORDER), PAPER_BORDER_WIDTH)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(border_path)
        finally:
            painter.end()
