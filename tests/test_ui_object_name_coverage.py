"""Static guard: every UI ``objectName`` must have a stylesheet rule (Phase 6E).

Why this file exists
--------------------
A widget that calls ``setObjectName("...")`` but is never named by a QSS rule
renders with Qt's *platform default* look: default font size, default button
chrome, default colours.  Nothing raises, nothing warns, and the result is a
dialog that looks like stock Qt inside an otherwise themed product.

The Phase 6E audit found exactly this in three places:

* ``saveButton`` / ``cancelButton`` / ``taskEditLabel`` -- the task edit
  dialog's two action buttons and both field labels,
* ``historyDualDate`` / ``historyStatsLabel`` -- the history window's
  dual-calendar date and progress summary, the two most informative lines in
  that window,
* ``startupCheckbox`` -- the settings window's startup toggle text.

All of them were measured rendering at Qt's default 9pt while every
neighbouring control used 12-13px.

The check is deliberately **static** (AST + string scan, no PySide6) so it
runs in the backend suite as well, and it deliberately allows a small
allow-list of names that are layout/structural hooks rather than visual
targets.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

from app.ui.styles.app_style import get_application_stylesheet

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = PROJECT_ROOT / "app"

#: Names that are structural or accessibility hooks, not visual targets.
#: Adding an entry here must be justified in the audit report.
STRUCTURAL_NAMES = {
    "centralWidget",   # the QMainWindow's central widget (transparent)
    "headerFrame",     # drag-area frame; styled by its children
    "taskInputRow",    # the row that holds selector + input
    # The settings logo is a QLabel that only ever shows a scaled QPixmap --
    # it has no text, so no font-size rule could apply to it.
    "settingsAppLogo",
}


def _styled_object_names() -> Set[str]:
    """Every ``#name`` the stylesheet actually targets."""
    sheet = get_application_stylesheet()
    names: Set[str] = set()
    for match in re.finditer(r"#([A-Za-z_][A-Za-z0-9_]*)", sheet):
        names.add(match.group(1))
    # Strip the hex colours (#RRGGBB etc.) that the regex above also catches.
    return {n for n in names if not re.fullmatch(r"[0-9A-Fa-f]{3,8}", n)}


def _object_names_in_source() -> Dict[str, List[int]]:
    """``objectName -> [line numbers]`` for every literal setObjectName call."""
    found: Dict[str, List[int]] = {}
    for path in sorted(APP_ROOT.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "setObjectName"):
                continue
            if not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found.setdefault(first.value, []).append(node.lineno)
    return found


def test_no_ui_object_name_is_missing_from_the_stylesheet():
    """Every visual ``objectName`` set in ``app/`` must have a QSS rule.

    Widgets built with a *computed* object name (for example the priority
    badges, whose name depends on the priority) are excluded: the regex-based
    scan only sees literal strings, and those two names are covered by their
    own tests in ``test_app_stylesheet.py``.
    """
    styled = _styled_object_names()
    set_in_code = _object_names_in_source()

    # Object names that are assigned conditionally / dynamically.
    dynamic = {
        "priorityBadgeHigh",   # app/ui/widgets/task_item.py
        "priorityBadgeLow",    # app/ui/widgets/task_item.py
        "taskTextLabelCompleted",  # app/ui/widgets/task_item.py
        "historyEmptyLabel",   # styled inline by history_window.py
    }

    missing = sorted(
        (name, lines)
        for name, lines in set_in_code.items()
        if name not in styled and name not in STRUCTURAL_NAMES and name not in dynamic
    )

    assert not missing, (
        "these objectNames are set in app/ but no stylesheet rule names them, "
        "so those widgets fall back to platform-default Qt styling: "
        + "; ".join(
            f"{name} (line {lines[0]})" for name, lines in missing
        )
    )


def test_the_allow_list_stays_small():
    """Keep the structural allow-list honest.

    Every entry is a layout or accessibility hook, never a widget whose
    appearance the user sees.  If this list grows, the audit report must say
    why.
    """
    assert len(STRUCTURAL_NAMES) <= 6, (
        f"the structural allow-list has grown to {len(STRUCTURAL_NAMES)} "
        "entries -- justify each one in the audit report"
    )
    for name in STRUCTURAL_NAMES:
        assert name in _object_names_in_source(), (
            f"{name!r} is allow-listed but is no longer set anywhere in app/ "
            "-- remove the stale entry"
        )


def test_the_stylesheet_names_every_object_it_is_expected_to():
    """Guard the other direction: the sheet must not name objects that no
    longer exist, which would be dead QSS."""
    set_in_code = _object_names_in_source()
    styled = _styled_object_names()

    dead = sorted(
        name
        for name in styled
        if name not in set_in_code
        and name not in {"priorityBadgeHigh", "priorityBadgeLow"}
    )
    # ``stickyNoteFrame`` is intentionally kept: its comment documents why the
    # paper surface must stay transparent, which stops a future maintainer
    # from giving it a rectangular background.
    allowed_dead = {"stickyNoteFrame"}

    assert not (set(dead) - allowed_dead), (
        "these stylesheet rules name an objectName that is never set in app/: "
        + ", ".join(sorted(set(dead) - allowed_dead))
    )
