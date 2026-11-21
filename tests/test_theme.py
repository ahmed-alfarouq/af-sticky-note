"""R-theme: centralized design-token tests (v3 §1).

Runtime assertions over app.ui.theme plus alias-consistency with the live
stylesheet module. No widget appearance is changed by this phase.
"""
from app.ui import theme
from app.ui.styles import app_style


def test_palette_matches_specification():
    assert theme.COLORS == {
        "bg": "#0F141D",
        "surface": "#171E29",
        "surface-raised": "#1c2533",
        "border": "#283241",
        "border-strong": "#3b4859",
        "text": "#F2F5F8",
        "text-secondary": "#98A2B3",
        "text-muted": "#6b778a",
        "text-disabled": "#4a586b",
        "trust": "#4F7CAC",
        "trust-hover": "#5a89ba",
        "trust-pressed": "#46709b",
        "soft": "#8FB8D8",
        "success": "#6FAF8F",
        "amber": "#D9A441",
        "amber-12": "rgba(217,164,65,0.12)",
        "amber-18": "rgba(217,164,65,0.18)",
        "amber-24": "rgba(217,164,65,0.24)",
        "amber-red": "#E57373",
        "amber-24": "rgba(217,164,65,0.24)",
        "focus-glow": "rgba(79,124,172,0.25)",
    }
    assert theme.COLOR_TOKENS == tuple(theme.COLORS.keys())
    assert len(theme.COLOR_TOKENS) == 20


def test_stylesheet_aliases_match_theme():
    """Spec-named COLOR_* in app_style must equal the canonical tokens."""
    assert app_style.COLOR_BACKGROUND == theme.BG
    assert app_style.COLOR_SURFACE == theme.SURFACE
    assert app_style.COLOR_TRUST == theme.TRUST
    assert app_style.COLOR_SOFT == theme.SOFT
    assert app_style.COLOR_TEXT_PRIMARY == theme.TEXT
    assert app_style.COLOR_TEXT_SECONDARY == theme.TEXT_SECONDARY
    assert app_style.COLOR_BORDER == theme.BORDER
    assert app_style.COLOR_SUCCESS == theme.SUCCESS
    assert app_style.COLOR_WARNING_PIN == theme.AMBER
    assert app_style.COLOR_FOCUS_RING == theme.TRUST


def test_typography_roles_match_specification():
    get = theme.TEXT_ROLES.__getitem__
    assert get("weekday").size == 14 and get("weekday").weight == theme.REGULAR
    assert get("hijri-day").size == 56 and get("hijri-day").weight == theme.BOLD
    assert get("task-title").size == 16 and get("task-meta").size == 12
    assert get("input").size == 16 and get("empty-title").weight == theme.BOLD
    assert set(get("ring-counter").color for _ in [0]) == {"text"}
    for role in theme.TEXT_ROLES.values():
        assert role.weight in (theme.REGULAR, theme.BOLD), "only two weights"
        assert role.color in theme.COLORS, "colors reference palette tokens"
        assert "italic" not in role.weight.lower()


def test_spacing_radii_motion_focus_shadow():
    assert theme.SPACING == (2, 4, 6, 8, 12, 16, 24)
    assert theme.RADII == {"tiny": 4, "default": 8, "panel": 12, "window": 16}
    assert theme.RADIUS_CIRCLE == "50%"
    assert theme.MOTION_COLOR_MS == 150
    assert theme.MOTION_CHECKBOX_PRESS_SCALE == 0.88
    assert theme.MOTION_RING_SWEEP_MS == 350
    assert theme.FOCUS_RING_WIDTH == 2 and theme.FOCUS_RING_OFFSET == 2
    assert theme.FOCUS_RING_COLOR == theme.SOFT
    assert theme.INPUT_GLOW_WIDTH == 3 and theme.INPUT_GLOW_COLOR == theme.FOCUS_GLOW
    assert theme.SHADOW_PINNED == "0 8px 24px rgba(0,0,0,.35)"
    assert theme.SHADOW_UNPINNED == "0 24px 60px rgba(0,0,0,.45)"
    assert theme.SHADOW_MENU == "0 12px 32px rgba(0,0,0,.5)"


def test_font_fallback_chain_is_documented():
    assert theme.FONT_FAMILY_FALLBACKS[0] == "Thmanyah"
    assert "Segoe UI" in theme.FONT_FAMILY_FALLBACKS


def test_icon_foundation_untouched():
    from app.ui.icons import GLYPHS, icon

    assert len(GLYPHS) == 11
    assert "pin" in GLYPHS and "plus" in GLYPHS
    assert callable(icon)


def test_font_registration_behavior_unchanged():
    from app.infrastructure import fonts

    assert callable(fonts.load_application_fonts)
    assert "Thmanyah" in fonts.get_default_font_family()
