"""Centralized v3 design tokens (single source of truth).

Values come verbatim from ``docs/specs/daily-sticky-ui-v3.md`` §1 (colors,
typography, spacing, radii, motion, shadows, focus). Widgets and stylesheets
read from here instead of duplicating literals; later UI phases bind the
remaining hardcoded values to these tokens without changing behavior in
this phase.

Legacy ``COLOR_*`` names in :mod:`app.ui.styles.app_style` that match a
spec token are aliases of the values below. Names with no spec equivalent
(paper/card surfaces, completed text, input background, navy) stay defined
in ``app_style.py`` and are documented there as pre-v3 legacy until their
owning widget phases reconcile them -- they are intentionally *not*
duplicated here, so every value keeps exactly one home.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Palette (§1.1 -- the complete palette; nothing outside it for new work)
# ---------------------------------------------------------------------------

BG = "#0F141D"
SURFACE = "#171E29"
SURFACE_RAISED = "#1c2533"
BORDER = "#283241"
BORDER_STRONG = "#3b4859"
TEXT = "#F2F5F8"
TEXT_SECONDARY = "#98A2B3"
TEXT_MUTED = "#6b778a"
TEXT_DISABLED = "#4a586b"
TRUST = "#4F7CAC"
TRUST_HOVER = "#5a89ba"
TRUST_PRESSED = "#46709b"
SOFT = "#8FB8D8"
SUCCESS = "#6FAF8F"
AMBER = "#D9A441"
AMBER_12 = "rgba(217,164,65,0.12)"
AMBER_18 = "rgba(217,164,65,0.18)"
AMBER_24 = "rgba(217,164,65,0.24)"

#: Amber-red urgent tone (approved R-rows-c extension, not spec palette):
#: HIGH must read distinctly hotter than LOW's plain amber ring. Same value
#: already marks HIGH in the priority selector, so no new hue is invented.
AMBER_RED = "#E57373"
FOCUS_GLOW = "rgba(79,124,172,0.25)"

COLORS: Dict[str, str] = {
    "bg": BG,
    "surface": SURFACE,
    "surface-raised": SURFACE_RAISED,
    "border": BORDER,
    "border-strong": BORDER_STRONG,
    "text": TEXT,
    "text-secondary": TEXT_SECONDARY,
    "text-muted": TEXT_MUTED,
    "text-disabled": TEXT_DISABLED,
    "trust": TRUST,
    "trust-hover": TRUST_HOVER,
    "trust-pressed": TRUST_PRESSED,
    "soft": SOFT,
    "success": SUCCESS,
    "amber": AMBER,
    "amber-12": AMBER_12,
    "amber-18": AMBER_18,
    "amber-24": AMBER_24,
    "amber-red": AMBER_RED,
    "focus-glow": FOCUS_GLOW,
}

#: Spec palette token names, in document order (completeness checks).
COLOR_TOKENS: Tuple[str, ...] = tuple(COLORS.keys())

# ---------------------------------------------------------------------------
# Typography (§1.2 -- Thmanyah Regular/Bold only; never italic Arabic)
# ---------------------------------------------------------------------------

REGULAR = "Regular"
BOLD = "Bold"

#: Fallback chain from the spec (informational: registration behavior in
#: app/infrastructure/fonts.py is unchanged by this module).
FONT_FAMILY_FALLBACKS: Tuple[str, ...] = (
    "Thmanyah",
    "IBM Plex Sans Arabic",
    "Segoe UI",
    "sans-serif",
)


@dataclass(frozen=True)
class TextRole:
    """One typography row: pixel size, line height (0 when unspecified),
    weight from {Regular, Bold}, and palette-token name for color."""

    size: int
    line_height: int
    weight: str
    color: str


TEXT_ROLES: Dict[str, TextRole] = {
    "weekday": TextRole(14, 22, REGULAR, "soft"),
    "hijri-day": TextRole(56, 56, BOLD, "text"),
    "hijri-month-year": TextRole(16, 21, BOLD, "text"),
    "gregorian": TextRole(14, 22, REGULAR, "text-secondary"),
    "ring-counter": TextRole(12, 0, BOLD, "text"),
    "quote": TextRole(14, 27, REGULAR, "text-secondary"),
    "task-title": TextRole(16, 24, REGULAR, "text"),
    "task-meta": TextRole(12, 19, REGULAR, "text-secondary"),
    "group-header": TextRole(12, 19, BOLD, "text-secondary"),
    "input": TextRole(16, 0, REGULAR, "text"),
    "chip": TextRole(14, 22, REGULAR, "text"),
    "menu-item": TextRole(14, 22, REGULAR, "text"),
    "empty-title": TextRole(16, 0, BOLD, "text"),
    "empty-body": TextRole(14, 22, REGULAR, "text-secondary"),
}

# ---------------------------------------------------------------------------
# Spacing, radii (§1.3)
# ---------------------------------------------------------------------------

SPACING: Tuple[int, ...] = (2, 4, 6, 8, 12, 16, 24)

RADII: Dict[str, int] = {
    "tiny": 4,      # tiny text buttons
    "default": 8,   # buttons, rows, chips, menu items
    "panel": 12,    # input field, menu panel
    "window": 16,   # window
}

#: Circles use a 50% radius (expressed by the widget, not a px value).
RADIUS_CIRCLE = "50%"

# ---------------------------------------------------------------------------
# Motion (§1.3 -- durations in ms; 0 when the OS disables animations)
# ---------------------------------------------------------------------------

MOTION_COLOR_MS = 150
MOTION_CHECKBOX_PRESS_SCALE = 0.88
MOTION_CHECKBOX_PRESS_MS = 150
MOTION_RING_SWEEP_MS = 350
MOTION_RING_SWEEP_CURVE = "OutCubic"

# ---------------------------------------------------------------------------
# Focus, glow, shadows (§1.3, §§4-9)
# ---------------------------------------------------------------------------

FOCUS_RING_WIDTH = 2
FOCUS_RING_COLOR = SOFT
FOCUS_RING_OFFSET = 2

INPUT_GLOW_WIDTH = 3
INPUT_GLOW_COLOR = FOCUS_GLOW

SHADOW_PINNED = "0 8px 24px rgba(0,0,0,.35)"
SHADOW_UNPINNED = "0 24px 60px rgba(0,0,0,.45)"
SHADOW_MENU = "0 12px 32px rgba(0,0,0,.5)"

__all__ = [
    "AMBER",
    "AMBER_12",
    "AMBER_18",
    "AMBER_24",
    "AMBER_RED",
    "BG",
    "BOLD",
    "BORDER",
    "BORDER_STRONG",
    "COLORS",
    "COLOR_TOKENS",
    "FOCUS_GLOW",
    "FOCUS_RING_COLOR",
    "FOCUS_RING_OFFSET",
    "FOCUS_RING_WIDTH",
    "FONT_FAMILY_FALLBACKS",
    "INPUT_GLOW_COLOR",
    "INPUT_GLOW_WIDTH",
    "MOTION_CHECKBOX_PRESS_MS",
    "MOTION_CHECKBOX_PRESS_SCALE",
    "MOTION_COLOR_MS",
    "MOTION_RING_SWEEP_CURVE",
    "MOTION_RING_SWEEP_MS",
    "RADII",
    "RADIUS_CIRCLE",
    "REGULAR",
    "SHADOW_MENU",
    "SHADOW_PINNED",
    "SHADOW_UNPINNED",
    "SOFT",
    "SPACING",
    "SUCCESS",
    "SURFACE",
    "SURFACE_RAISED",
    "TEXT",
    "TEXT_DISABLED",
    "TEXT_MUTED",
    "TEXT_ROLES",
    "TEXT_SECONDARY",
    "TRUST",
    "TRUST_HOVER",
    "TRUST_PRESSED",
    "TextRole",
]
