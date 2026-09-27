"""Regression guard for the global application stylesheet (Phase 6D.1).

Why this file exists
--------------------
An unquoted flag combination in a ``qproperty-*`` value -- for example::

    qproperty-alignment: AlignRight | AlignVCenter;

makes Qt's QSS parser reject the declaration and then **discard the entire
application stylesheet**, not just that one rule.  Every widget silently falls
back to default Qt styling: the dark theme, the badges, the buttons, the inputs
and the priority selector all lose their intended look, and nothing in the test
suite notices because no widget raises an error.

Qt's own diagnostic is a single line on stderr -- ``Could not parse application
stylesheet`` -- which is easy to miss, so these tests assert on **behaviour**:
stylesheet-derived properties that are only correct if the whole sheet was
accepted.  If the sheet is ever rejected again, every one of these assertions
fails.

The Qt half no-ops (rather than fails) when PySide6 is unavailable, following
the convention used by the rest of this project's UI tests.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from app.ui.styles.app_style import get_application_stylesheet

# ---------------------------------------------------------------------------
# Optional Qt support (the backend suite must run without PySide6)
# ---------------------------------------------------------------------------
try:  # pragma: no cover - environment dependent
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QWidget,
    )

    QT_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    QT_AVAILABLE = False


def _skip_without_qt() -> bool:
    return not QT_AVAILABLE


def _qt_app():
    return QApplication.instance() or QApplication([])


# ===========================================================================
# 1. Static guards -- these run everywhere, including the backend suite
# ===========================================================================
def _qproperty_declarations() -> List[Tuple[int, str]]:
    """Every ``qproperty-*: value;`` declaration as ``(line_number, text)``."""
    found = []
    for number, line in enumerate(
        get_application_stylesheet().splitlines(), start=1
    ):
        stripped = line.strip()
        if stripped.startswith("qproperty-") and stripped.endswith(";"):
            found.append((number, stripped))
    return found


def test_alignment_declarations_are_quoted():
    """The three alignment values must be quoted, and must be the right value.

    Qt accepts a single flag unquoted (``AlignRight``) but rejects a *pair*
    (``AlignRight | AlignVCenter``) and throws the whole sheet away.  Quoting
    is the Qt-supported representation for a flag combination.
    """
    declarations = _qproperty_declarations()
    assert declarations, "expected the stylesheet to set qproperty-alignment"

    for line_number, declaration in declarations:
        assert "|" not in declaration or "'" in declaration, (
            f"line {line_number}: an unquoted flag combination makes Qt discard "
            f"the ENTIRE stylesheet -- quote the value: {declaration}"
        )

    values = {d.split(":", 1)[1].strip().rstrip(";").strip() for _, d in declarations}
    assert values == {"'AlignRight | AlignVCenter'"}, (
        f"unexpected qproperty-alignment value(s): {sorted(values)}"
    )


def test_no_qproperty_declaration_uses_dotted_qt_syntax():
    """``qproperty-orientation: Qt.Horizontal`` is also rejected by Qt.

    Nothing in the sheet uses it today; this keeps it that way.
    """
    for line_number, declaration in _qproperty_declarations():
        assert "Qt." not in declaration, (
            f"line {line_number}: the dotted 'Qt.X' form is not valid QSS -- "
            f"use the bare enum name, quoted when it is a combination: {declaration}"
        )


# ===========================================================================
# 2. Behavioural guard -- only runs when Qt is available
# ===========================================================================
def _styled_probe(object_name: str, factory=None):
    """Create a widget carrying one of the stylesheet's object names.

    ``factory`` defaults to ``QLabel`` but is resolved lazily: this module is
    also imported by the backend suite, where PySide6 is absent.
    """
    if factory is None:
        factory = QLabel
    widget = factory()
    widget.setObjectName(object_name)
    widget.show()
    return widget


def test_application_stylesheet_reaches_the_widgets_it_targets():
    """The whole stylesheet must be accepted, not silently discarded.

    Detection strategy: a *marker* stylesheet that deliberately does not touch
    the probes is installed first.  If the real sheet is then rejected, Qt
    keeps the marker and the probes keep their default values -- so every
    assertion below fails.  There is no need to scrape stderr.
    """
    if _skip_without_qt():
        return
    app = _qt_app()

    app.setStyleSheet("QLabel#__qss_probe_marker { color: #000000; }")

    probes = [
        _styled_probe("taskTextLabel"),
        _styled_probe("priorityBadgeHigh"),
    ]
    combo = QComboBox()
    combo.setObjectName("prioritySelector")
    combo.addItems(["عاجل", "عادي", "منخفض"])
    combo.show()
    probes.append(combo)

    # A widget the sheet must NOT restyle, proving the sheet is selective
    # rather than merely "setting a font on everything".
    control = _styled_probe("someWidgetTheSheetDoesNotName")

    try:
        app.setStyleSheet(get_application_stylesheet())
        for widget in probes + [control]:
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        # font-size comes from the sheet; the Qt default leaves pixelSize() at -1.
        assert probes[0].font().pixelSize() == 14, (
            "QLabel#taskTextLabel should get font-size 14px from the stylesheet "
            f"(got {probes[0].font().pixelSize()}) -- the stylesheet was probably "
            "discarded by the QSS parser"
        )
        assert probes[1].font().pixelSize() == 11, (
            "QLabel#priorityBadgeHigh should get font-size 11px from the stylesheet "
            f"(got {probes[1].font().pixelSize()}) -- the stylesheet was probably "
            "discarded by the QSS parser"
        )
        assert combo.font().pixelSize() == 12, (
            "QComboBox#prioritySelector should get font-size 12px from the "
            f"stylesheet (got {combo.font().pixelSize()}) -- the stylesheet was "
            "probably discarded by the QSS parser"
        )

        # Negative control: the sheet must not blanket-restyle everything.
        assert control.font().pixelSize() == -1, (
            "a widget the stylesheet does not name should keep Qt's default font"
        )
    finally:
        for widget in probes + [control]:
            widget.close()
        app.setStyleSheet("")


def test_task_text_alignment_is_right_and_vcenter():
    """The quoted alignment value must actually be honoured by Qt.

    This is what stops someone from "fixing" the parse error by deleting the
    declaration instead of quoting it, which would silently left-align the
    Arabic task text.
    """
    if _skip_without_qt():
        return
    app = _qt_app()
    app.setStyleSheet("QLabel#__qss_probe_marker { color: #000000; }")

    label = QLabel("مهمة")
    label.setObjectName("taskTextLabel")
    label.show()
    try:
        app.setStyleSheet(get_application_stylesheet())
        label.style().unpolish(label)
        label.style().polish(label)

        expected = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        assert label.alignment() == expected, (
            f"expected AlignRight | AlignVCenter ({int(expected):#x}), got "
            f"{int(label.alignment()):#x} -- the qproperty-alignment value is not "
            "being applied"
        )
    finally:
        label.close()
        app.setStyleSheet("")


def test_priority_selector_stays_compact_under_the_real_stylesheet():
    """The selector must stay a small, quiet control next to the task text.

    Phase 6D sized it with ``QSizePolicy.Maximum`` + ``AdjustToContents``; the
    stylesheet adds padding, border and font size.  What is asserted here is
    the actual requirement -- the control must not dominate the input row and
    must never clip an Arabic label -- rather than a specific pixel count,
    because Qt reads QSS ``min-width`` / ``max-width`` as the *content* width
    and then adds the padding and border on top.
    """
    if _skip_without_qt():
        return
    from app.ui.widgets.priority_selector import PrioritySelector

    app = _qt_app()
    app.setStyleSheet("QLabel#__qss_probe_marker { color: #000000; }")

    selector = PrioritySelector()
    selector.show()
    try:
        app.setStyleSheet(get_application_stylesheet())
        selector.style().unpolish(selector)
        selector.style().polish(selector)

        # Lay out exactly as the main window does: selector, then a stretching
        # text field beside it.
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        field = QLineEdit()
        row.addWidget(selector)
        row.addWidget(field, 1)
        host.resize(380, 60)
        host.show()

        try:
            # 1. It must not dominate the row: the task text field keeps more
            #    space than the selector.  This holds for any font or DPI,
            #    unlike a fixed pixel budget.
            assert selector.width() < field.width(), (
                f"priority selector ({selector.width()}px) is as wide as or wider "
                f"than the task input ({field.width()}px) -- it must stay secondary "
                "to the task text"
            )

            # 2. It must never be squeezed below its own minimum, which is what
            #    would clip an Arabic label.
            assert selector.width() >= selector.minimumSizeHint().width(), (
                f"priority selector is {selector.width()}px but needs at least "
                f"{selector.minimumSizeHint().width()}px -- a label is being clipped"
            )

            # 3. It must stay comfortably clickable.
            assert selector.height() >= 20, (
                f"priority selector is only {selector.height()}px tall"
            )
        finally:
            host.close()
    finally:
        selector.close()
        app.setStyleSheet("")


def test_stylesheet_keeps_the_priority_badges_secondary():
    """Badges stay small: 11px text and a light border, never a filled block."""
    if _skip_without_qt():
        return
    app = _qt_app()
    app.setStyleSheet("QLabel#__qss_probe_marker { color: #000000; }")

    badges = [
        _styled_probe("priorityBadgeHigh"),
        _styled_probe("priorityBadgeLow"),
    ]
    try:
        app.setStyleSheet(get_application_stylesheet())
        for badge in badges:
            badge.style().unpolish(badge)
            badge.style().polish(badge)
            assert badge.font().pixelSize() == 11, (
                f"{badge.objectName()} should render at 11px (got "
                f"{badge.font().pixelSize()})"
            )
    finally:
        for badge in badges:
            badge.close()
        app.setStyleSheet("")
