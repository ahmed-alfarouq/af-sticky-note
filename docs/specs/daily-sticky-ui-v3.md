# Daily Sticky — UI Implementation Spec (v3) — Canonical Copy

> **Provenance:** faithful transcription of the user-supplied original
> specification (`docs/specs/daily-sticky-ui-v3-source.md`, as delivered
> into the repository). Only this header is added; the body below preserves
> the original title, sections, values, strings, tables, code examples, and
> acceptance checklist without rewriting. The original six-category wording
> is retained as written; the approved eight-category decision lives
> separately in `amendment-01-eight-categories.md` and takes precedence for
> category data and behavior.

---

# Daily Sticky — UI Implementation Spec (v3)

- **Units:** logical px at 100% scale. Qt handles HiDPI; never multiply by hand.
- **RTL:** the entire UI is right-to-left. **Start = right edge, End = left edge.** Every "visual order" list below reads **right → left**. Call `QApplication.setLayoutDirection(Qt.RightToLeft)`. In a `QHBoxLayout` the first widget added appears at the right. Never hardcode left/right unless the text says *physical*.
- **Physical padding** is written T/R/B/L (top/right/bottom/left) as the viewer sees it on screen.
- **Digits:** Western digits (0-9) everywhere, including dates and counters.
- **Language:** all Arabic strings in this document are literal and final. Code identifiers stay English.
- **State words:** *default, hover, pressed, focus* (keyboard focus ring), *disabled*, *active* (toggled on).
- **Icons:** vector glyphs from the Phosphor set, loaded through the `qtawesome` library (see §1.4) and colored per state in code. Do not ship or load image files for icons: the old PNG icon files are retired. Every glyph name in this spec was checked against qtawesome 1.4.2.
- **Forbidden:** italic Arabic text (it breaks letter joins), emoji as icons, native `QComboBox`/`QMenu` styling for the category dropdown, letter-spacing on Arabic text, any color not listed in §1.

## 1. Design tokens

### 1.1 Colors (the complete palette)

| Token | Hex | Used for |
| --- | --- | --- |
| bg | `#0F141D` | Window background, input inside chips, edit field |
| surface | `#171E29` | Row hover, input field, button hover, group hover |
| surface-raised | `#1c2533` | Dropdown/context menu panel, button pressed |
| border | `#283241` | Window border, dock divider, field border, ring track, grip, chip border |
| border-strong | `#3b4859` | Idle (unchecked) task circle ring |
| text | `#F2F5F8` | Primary text, hover icons |
| text-secondary | `#98A2B3` | Secondary text, idle icons, quote, Gregorian date |
| text-muted | `#6b778a` | Input placeholder, neutral priority dot, disabled add-button icon |
| text-disabled | `#4a586b` | Disabled icons, strikethrough line color |
| trust | `#4F7CAC` | Primary action, progress arc, quote accent rule, focus border |
| trust-hover | `#5a89ba` | Add button hover |
| trust-pressed | `#46709b` | Add button pressed |
| soft | `#8FB8D8` | Weekday label, focus ring, hover on circle/category, check icon in menu |
| success | `#6FAF8F` | Completed circle fill, ring at 100% |
| amber | `#D9A441` | Pin active, priority markers |
| amber-12 | `rgba(217,164,65,0.12)` | Pin active background |
| amber-18 | `rgba(217,164,65,0.18)` | Pin active hover background |
| focus-glow | `rgba(79,124,172,0.25)` | 3 px glow around focused input/edit field |

The palette is the original navy system plus four derived neutrals (`border-strong`, `text-muted`, `text-disabled`, `surface-raised`). No red, no coral, no gradients.

### 1.2 Typography

Font: **Thmanyah** (bundled `.woff2` in `fonts/thmanyah/`, load with `QFontDatabase.addApplicationFont`, use the returned family name). Only two weights are used: **Regular** and **Bold**. Mapping from the prototype: 500 → Regular, 600 → Bold, 700 → Bold. Fallback family list: `Thmanyah, "IBM Plex Sans Arabic", "Segoe UI", sans-serif`.

| Role | Size / line-height | Weight | Color |
| --- | --- | --- | --- |
| Weekday label | 14 / 22 | Regular | soft |
| Hijri day numeral | 56 / 56 | Bold, tracking -2% (digits only) | text |
| Hijri month + year | 16 / 21 | Bold | text |
| Gregorian date (subtext) | 14 / 22 | Regular | text-secondary |
| Ring counter | 12 | Bold | text |
| Quote | 14 / 27 | Regular | text-secondary |
| Task title | 16 / 24 | Regular | text (done: text-secondary) |
| Task meta | 12 / 19 | Regular (priority label Bold) | text-secondary (priority: amber) |
| Completed-group header | 12 / 19 | Bold | text-secondary |
| Input text | 16 | Regular | text (placeholder text-muted) |
| Chip label, menu item | 14 / 22 | Regular | text |
| Empty-state title | 16 | Bold | text |
| Empty-state body | 14 / 22 | Regular | text-secondary |

### 1.3 Spacing, radius, motion, shadow

- **Spacing scale:** 2, 4, 6, 8, 12, 16, 24. Use nothing else.
- **Radius:** 4 (tiny text buttons), 8 (buttons, rows, chips, menu items), 12 (input field, menu panel), 16 (window), 50% (circles).
- **Motion:** color/background changes 150 ms ease; checkbox press scale 0.88 over 150 ms; progress ring sweep 350 ms ease-out. Nothing else animates. If the OS "animations" setting is off, all durations become 0.
- **Window shadow:** pinned `0 8px 24px rgba(0,0,0,.35)`; unpinned `0 24px 60px rgba(0,0,0,.45)`. Menu shadow `0 12px 32px rgba(0,0,0,.5)`.

### 1.4 Icon system: qtawesome with the Phosphor set

Icons are vector glyphs, not image files. Use **qtawesome** (MIT), which bundles the Phosphor icon font (MIT) and works with PySide6 through its `qtpy` dependency. Verified against qtawesome 1.4.2 (it bundles Phosphor 1.3.0): every glyph name below exists in it. Colors are applied in code, so one glyph serves every state.

Add one line to `requirements.txt`:

```text
PySide6>=6.7,<7.0
pyinstaller>=6.5,<7.0
qtawesome>=1.4,<2.0
```

Rules:

- In `main.py`, set `os.environ["QT_API"] = "pyside6"` before anything imports `qtawesome` or `qtpy`, so the Qt binding is never guessed.
- Call `qta.icon(...)` only after the `QApplication` exists (it loads its font on first use).
- Use the **bold** weight of every glyph (about 1.7 px stroke at 18 px, matching the design). The one exception is the active pin, which uses the **fill** weight.
- Do not rely on `QIcon` Active/Selected modes for hover; custom-styled buttons do not receive them reliably. Each icon button picks its own color for its state (§13.2).
- Build each icon once per (key, color) and cache it. Never call `qta.icon` inside `paintEvent`.

| Where | Key | qtawesome name | Size |
| --- | --- | --- | --- |
| Pin, inactive | `pin` | `ph.push-pin-bold` | 18 |
| Pin, active | `pin_active` | `ph.push-pin-fill` | 18 |
| Archive | `archive` | `ph.archive-bold` | 18 |
| Settings | `settings` | `ph.gear-six-bold` (alternative: `ph.sliders-horizontal-bold`) | 18 |
| Close | `close` | `ph.x-bold` | 18 |
| Delete task | `trash` | `ph.trash-bold` | 18 |
| Task checkmark | `check` | `ph.check-bold` | 11 |
| Dropdown selected mark | `check` | `ph.check-bold` | 16 |
| Category tag (row meta / chip) | `tag` | `ph.tag-bold` | 12 / 16 |
| Chevron, expanded group and chips | `caret_down` | `ph.caret-down-bold` | 14 / 16 |
| Chevron, collapsed group | `caret_left` | `ph.caret-left-bold` | 14 |
| Add | `plus` | `ph.plus-bold` | 18 |

```python
# app/ui/icons.py
from functools import lru_cache
import qtawesome as qta
from PySide6.QtGui import QIcon

GLYPHS = {
    "pin": "ph.push-pin-bold", "pin_active": "ph.push-pin-fill",
    "archive": "ph.archive-bold", "settings": "ph.gear-six-bold",
    "close": "ph.x-bold", "trash": "ph.trash-bold", "check": "ph.check-bold",
    "tag": "ph.tag-bold", "caret_down": "ph.caret-down-bold",
    "caret_left": "ph.caret-left-bold", "plus": "ph.plus-bold",
}

@lru_cache(maxsize=None)
def icon(key: str, color: str) -> QIcon:
    return qta.icon(GLYPHS[key], color=color)
```

**PyInstaller:** qtawesome keeps its font (`.ttf`) and name-map (`.json`) files inside the package as data files, and I found no built-in PyInstaller hook for it in `pyinstaller-hooks-contrib` 2026.8. Collect them explicitly: `--collect-data qtawesome` on the command line, or `datas += collect_data_files("qtawesome")` in the `.spec` file. After every build, run the packaged exe and confirm icons render; a missing font shows blank buttons.

**Alternative considered:** shipping Lucide SVG files and tinting them with `QtSvg`. It matches the prototype's stroke exactly but needs asset files plus custom tinting code, so qtawesome is the simpler default.

## 2. Window shell

- **Size:** default 380×640 (excluding shadow margin). Minimum 320×480. Resizable; the task list is the only region that grows.
- **Frame:** frameless, translucent top-level window with a transparent outer margin of 32 px so the shadow can paint. All measurements in this document are inside that margin.
- **Surface:** background `#0F141D` flat, 1 px border `#283241`, radius 16. Content is clipped to the rounded shape.
- **Pinned (desktop widget):** shadow is the smaller one. Stays below normal windows, no taskbar icon, does not steal focus on click of non-input areas.
- **Unpinned (normal window):** larger, softer shadow to look raised. Normal taskbar behavior.
- **Moving:** drag the grip (§4.2) or any empty part of the top bar or hero. Cursor becomes closed-hand while dragging. Position is persisted on release (both states).
- **Resizing:** 6 px invisible resize border on all edges; persist size on release.
- **No** title text, no native title bar, no window icon visible.

## 3. Vertical layout map (top → bottom)

| Block | Height | Notes |
| --- | --- | --- |
| Top bar | 44 | 8 top padding + 36 button height, 12 side padding |
| Date hero | 147 | 12 top padding + ≈135 text column |
| Quote | 16 margin + 27 per line | usually 1-2 lines |
| Task list | flexible | 8 margin-top, 12 side margin |
| Input dock | 115 | 1 divider + 12 + 50 field + 8 + 32 chips + 12 |

All blocks are full width. Horizontal text edge is **24 px** from the window edge (hero, quote, row content). Row highlight, dock field and divider share a **12 px** edge.

## 4. Top bar

A single horizontal bar, height 44, padding T8 R12 B0 L12. Three children in visual order **right → left: Pin button, Grip, Actions group**, spread with space-between so the grip is optically centered. Bar background is transparent (shows window bg).

### 4.1 Pin button (rightmost)

- **Size:** 36×36, radius 8, icon 18×18 centered. Right edge sits 12 px from the window's inner right edge.
- **Meaning:** it is the PINNED/UNPINNED toggle. *Active* = pinned.
- **Icon:** pushpin. Inactive uses `ph.push-pin-bold` (outline). Active uses `ph.push-pin-fill` (same shape, solid).

| State | Icon color | Background | Extra |
| --- | --- | --- | --- |
| Inactive (unpinned), default | `#98A2B3` | transparent | outline icon |
| Inactive, hover | `#F2F5F8` | `#171E29` |  |
| Inactive, pressed | `#F2F5F8` | `#1c2533` |  |
| **Active (pinned), default** | `#D9A441` | `rgba(217,164,65,.12)` | solid icon |
| Active, hover | `#D9A441` | `rgba(217,164,65,.18)` | solid icon |
| Active, pressed | `#D9A441` | `rgba(217,164,65,.24)` | solid icon |
| Focus (any) | unchanged | unchanged | 2 px ring `#8FB8D8`, offset 2 px, radius 8 |

- **Click / Space / Enter:** toggles pinned state through the platform layer (not from UI code), swaps icon, swaps tooltip and accessible name, swaps window shadow (§2). State persists across restarts.
- **Tooltip:** active → `إلغاء التثبيت`; inactive → `تثبيت على سطح المكتب`. Delay 500 ms.
- **Never disabled.** If the platform layer fails, revert the visual state and show an Arabic error message (logged in English).

### 4.2 Grip (center)

- A **32×4 px** pill, radius 2, color `#283241`, vertically centered with the buttons (center at y = 26 from window top), horizontally centered in the window.
- **Purely a drag affordance.** No hover change, no click action. Cursor over it: open-hand; while dragging: closed-hand. Not focusable, hidden from accessibility.

### 4.3 Actions group (leftmost)

Three 36×36 icon buttons, radius 8, gap 2 px between them, left edge 12 px from the window's inner left edge. **Visual order right → left: Archive, Settings, Close** (so on screen from the far left: ✕, settings, archive).

All three share these states:

| State | Icon color | Background |
| --- | --- | --- |
| default | `#98A2B3` | transparent |
| hover | `#F2F5F8` | `#171E29` |
| pressed | `#F2F5F8` | `#1c2533` |
| focus | unchanged | 2 px ring `#8FB8D8`, offset 2, radius 8 |
| disabled | `#4A586B` | transparent (no hover change) |

| Button | Icon (qtawesome name) | Tooltip / accessible name | Function |
| --- | --- | --- | --- |
| Archive | `ph.archive-bold` | `الأرشيف` | Opens the daily-archive view (history of past days). |
| Settings | `ph.gear-six-bold` | `إعدادات` | Opens settings. |
| Close | `ph.x-bold` | `إغلاق` | Quits the app cleanly (same as context-menu `إغلاق التطبيق`): flush pending writes, persist position/size, exit. |

**Phase rule:** until the archive view and settings view actually exist, render those two buttons in the **disabled** state with tooltip `غير متاح بعد`. Do not wire empty handlers (no dead actions). Close is always enabled.

## 5. Date hero

Padding T12 R24 B0 L24. Two children, vertically centered against each other: the **date column** (start/right) and the **progress ring** (end/left).

### 5.1 Date column (text, right-aligned, stacked, no gaps except where noted)

1. **Weekday label** — e.g. `الأربعاء`. 14/22 Regular, `#8FB8D8`.
2. **Hijri day numeral** — e.g. `18`. 56/56 Bold, `#F2F5F8`, tracking -2%. Margin: 4 top, 8 bottom. This is the dominant element of the whole window.
3. **Hijri month + year** — e.g. `ربيع الآخر 1448 هـ`. 16/21 Bold, `#F2F5F8`. The suffix `هـ` is part of the string, separated by one space.
4. **Gregorian date (subtext)** — e.g. `30 سبتمبر 2026`. 14/22 Regular, `#98A2B3`, margin-top 2.

Hierarchy rule: the Hijri date is the main date, Gregorian is always secondary. Never swap sizes or colors.

**Data contract:** the domain layer supplies a `DateDisplay` object (weekday, hijri\_day, hijri\_month\_name, hijri\_year, gregorian\_day, gregorian\_month\_name, gregorian\_year). The UI only formats strings. Hijri uses the Umm al-Qura calendar (decide the library in the architecture step, e.g. a `hijri-converter`-style package).

- Hijri months: محرم، صفر، ربيع الأول، ربيع الآخر، جمادى الأولى، جمادى الآخرة، رجب، شعبان، رمضان، شوال، ذو القعدة، ذو الحجة.
- Gregorian months: يناير، فبراير، مارس، أبريل، مايو، يونيو، يوليو، أغسطس، سبتمبر، أكتوبر، نوفمبر، ديسمبر.
- Weekdays: الاثنين، الثلاثاء، الأربعاء، الخميس، الجمعة، السبت، الأحد.
- **Midnight rollover:** a timer re-evaluates the local date at 00:00; on change, refresh the whole hero and load/create the new day's record. Not interactive, not focusable.

### 5.2 Progress ring (completion circle)

- **Size 44×44.** Center (22,22), radius 18, stroke width 4, round caps. Vertically centered in the hero row, at the end (left) side.
- **Track:** full circle `#283241`.
- **Arc:** `#4F7CAC`, starts at 12 o'clock and sweeps **clockwise** by `360° × done / total`. When `done == total` and `total > 0`, arc color becomes `#6FAF8F`.
- **Center text:** `done/total` (e.g. `2/6`), 12 px Bold, `#F2F5F8`, centered, **forced left-to-right** so it never reads `6/2`.
- **Empty day (`total = 0`):** text `0/0`, no arc, track only.
- **Animation:** on any change the arc animates to the new value over 350 ms ease-out; the color switch to green is instant at 100%.
- **Accessibility:** accessible name `أُنجز {done} من {total}`; also shown as tooltip. Not focusable.
- Counts include completed and open tasks of the current day only.

## 6. Quote block

- Margin T16 R24 B0 L24. Text 14/27 Regular `#98A2B3`, **upright (no italic)**, no decorative quotation marks.
- A **2 px vertical rule `#4F7CAC`** runs along the start (right) edge for the full height of the text, with **12 px** padding between rule and text.
- Wraps to as many lines as needed up to 3; beyond that, elide with `…` and show the full quote in a tooltip.
- The quote is chosen once per day and does not change until midnight. Not interactive; text is not selectable.

## 7. Task list

### 7.1 Container

- A scroll area filling the space between the quote and the dock. Margin T8 R12 B0 L12, inner padding 8 top and bottom, rows separated by 2 px.
- **Edge fade:** the top and bottom 8 px fade into the background. Because the window is a flat `#0F141D`, implement with two 8 px overlay widgets painting a vertical gradient from `#0F141D` (opaque) to transparent. Overlays ignore mouse events.
- **Scrollbar:** vertical only, overlay style, 6 px wide, track transparent, thumb `#283241` (hover `#3b4859`), radius 3, no arrows, 4 px inset from the edge.
- **Order:** open tasks first (in stored order), then the completed group (§7.5).
- **Empty day (no tasks at all):** centered block, title `يومك فارغ` (16 Bold `#F2F5F8`), body `ابدأ بمهمة واحدة، ثم اضغط Enter لإضافة التالية.` (14 `#98A2B3`), 4 px between, 24 px padding.
- **All done (tasks exist, none open):** same block with title `أنجزت كل مهام اليوم` and body `أضف مهمة جديدة أو استمتع بالراحة.`, shown above the completed group.

### 7.2 Task row anatomy

Row: padding **T8 R12 B8 L8**, radius 8, children laid out with 8 px gaps. Visual order **right → left**: **Completion checkbox · Text body · Delete button**. Children are top-aligned.

| Part | Geometry |
| --- | --- |
| Checkbox hit area | 32×32 button, radius 8, offset -4 px vertically so the circle's center sits at row-top + 20 px (aligned with the middle of the first title line) |
| Checkbox circle (visual) | **18×18**, 1.5 px ring, centered in the hit area |
| Body | stretches; contains title (16/24) and, for open tasks, the meta line (12/19) directly beneath |
| Delete button | 32×32, radius 8, icon `ph.trash-bold` at 18×18, same -4 px vertical offset, at the end (left) |

Row height: **open task ≈ 59 px** (8+24+19+8), **completed task = 40 px**; titles that wrap add 24 px per extra line.

### 7.3 Row states

| State | Row background | Notes |
| --- | --- | --- |
| default | transparent |  |
| hover | `#171E29` | also when any child has keyboard focus (focus-within) |
| done | transparent / hover as above | title strikethrough, meta line hidden |
| editing | `#171E29` | title replaced by edit field (§7.4) |

**Checkbox circle states**

| State | Ring | Fill | Icon |
| --- | --- | --- | --- |
| unchecked default | `#3b4859` 1.5 px | transparent | none |
| unchecked hover | `#8FB8D8` | transparent | none |
| pressed | unchanged | unchanged | circle scales to 0.88 for 150 ms |
| checked | `#6FAF8F` | `#6FAF8F` | `ph.check-bold` 11×11, stroke-heavy, colored `#0F141D` |
| focus | 2 px ring `#8FB8D8`, offset 2, around the **32×32 hit area**, radius 8 |  |  |

- **Behavior:** click or Space toggles done. The task moves between the open list and the completed group; its original order index is kept so unchecking returns it to its place. The ring counter (§5.2) updates in the same frame. After toggling, keyboard focus moves to the next open task's checkbox, or to the add input if none remain.
- The checkbox exposes role *checkbox*, checked state and the task text as its name.

**Title:** 16/24 Regular `#F2F5F8`, wraps at the available width (no elision). Done: color `#98A2B3` with a strikethrough line `#4A586B`. Cursor: I-beam. Focusable (tab stop).

### 7.4 Inline edit

- **Enter edit:** double-click the title, or press Enter or F2 while the title has focus.
- **Edit field** replaces the title in place: full body width, height 26 (24 text + 2 border), padding 0 8, background `#0F141D`, 1 px border `#4F7CAC`, radius 8, 3 px outer glow `rgba(79,124,172,.25)`, 16 px Regular text, text fully selected on entry.
- **Enter:** save. **Escape:** cancel, restore old text. **Focus lost:** save. Saving trims whitespace; an empty result **cancels** the edit and keeps the old text (it never deletes the task). Backspace on an empty field does nothing special.
- After save/cancel focus returns to that row's title. Maximum length 200 characters.

### 7.5 Meta line (open tasks only)

Directly under the title, 12/19, items spaced 8 px, visual order right → left: **Category button, Priority label**.

- **Category button:** `ph.tag-bold` icon 12×12 + category label, 4 px apart, no background, radius 4, color `#98A2B3`; hover color `#8FB8D8`; focus ring as §4.1 (radius 4). Click opens the category dropdown (§9) **below** the button, with the task's current category selected; choosing a value updates the task immediately. Accessible name: `تغيير الفئة: {category}`.
- **Priority label** (shown only for مهم and عاجل): 8 px dot + label, 4 px apart, 12 Bold `#D9A441`.
  - `مهم` → **hollow** dot (8 px, 2 px ring `#D9A441`, transparent fill)
  - `عاجل` → **solid** dot `#D9A441`
  - `عادي` → nothing is shown.
- The priority label is read-only on the row (priority is chosen in the dock).

### 7.6 Delete button

Invisible (opacity 0) by default; becomes visible when the row is hovered or any child has focus. Icon `#98A2B3`; hover icon `#F2F5F8` with background `#1c2533` (not `#171E29`, which would vanish against the hovered row); focus ring as §4.1. Click removes the task immediately with no confirmation dialog, persists the deletion (soft-delete or archive-safe, to keep history), and updates the counter. Accessible name `حذف المهمة`.

### 7.7 Completed group

- **Header button:** appears only if at least one task is done. Height 32, margin-top 8, padding 0 12, radius 8, items 8 px apart. Visual order right → left: **chevron (`ph.caret-down-bold`, 14×14, `#98A2B3`)**, then text `مكتملة · {n}` (12 Bold `#98A2B3`).
- Hover background `#171E29`; focus ring as §4.1.
- **Expanded (default):** chevron points down, completed rows listed beneath. **Collapsed:** the chevron glyph swaps to ph.caret-left-bold (points left), rows hidden. Click/Space/Enter toggles; the glyph swaps instantly. Remember the state for the session.

## 8. Input dock

Pinned to the bottom. Top border 1 px `#283241`, padding 12 on all sides, background transparent. Two rows, 8 px apart.

### 8.1 Row 1 — input field

- **Container:** height 50, background `#171E29`, 1 px border `#283241`, radius 12, padding 6, 6 px gap. Visual order right → left: **Text input, Add button**.
- **Focus-within:** border becomes `#4F7CAC` and a 3 px glow `rgba(79,124,172,.25)` is drawn outside the border (paint it manually; QSS cannot).
- **Text input:** borderless, transparent, height 36, padding 0 8, 16 px Regular `#F2F5F8`, placeholder `اكتب مهمة جديدة…` in `#6b778a`, single line, max 200 chars, no native focus ring.
- **Add button:** 36×36, radius 8, `ph.plus-bold` 18×18 white `#FFFFFF`.

| State | Background | Icon |
| --- | --- | --- |
| default (text present) | `#4F7CAC` | `#FFFFFF` |
| hover | `#5a89ba` | `#FFFFFF` |
| pressed | `#46709b` | `#FFFFFF` |
| focus | unchanged | 2 px ring `#8FB8D8`, offset 2 |
| disabled (input empty) | `#283241` | `#6b778a` |

- **Add / Enter:** trims text; if empty, does nothing. Otherwise creates a task with the **currently selected category and priority**, appends it to the end of the open list, clears the input, **keeps focus in the input**, scrolls the new row into view, resets priority to عادي (category is **kept** for fast batch entry).
- Disabled-when-empty is a deliberate addition to the prototype for clearer affordance.
- Accessible names: input `مهمة جديدة`, button `إضافة المهمة`.

### 8.2 Row 2 — option chips

Margin-top 8, chips 8 px apart. Visual order right → left: **Category chip, Priority chip**. Both: height 32, padding T0 R12 B0 L12, 1 px border `#283241`, radius 8, transparent background, 14/22 Regular `#F2F5F8`, 8 px gap between parts.

| State | Background |
| --- | --- |
| default | transparent |
| hover, or menu open | `#171E29` |
| focus | 2 px ring `#8FB8D8`, offset 2 |

**Category chip:** parts right → left: `ph.tag-bold` 16×16 `#98A2B3`, label (current category, default `عام`), `ph.caret-down-bold` 16×16 `#98A2B3`. Click or Space/Enter/Down-arrow opens the dropdown (§9) **above** the chip. While open the chip shows the hover background and exposes expanded state. Accessible name `الفئة`.

**Priority chip:** parts right → left: 8 px dot, label. Click or Space/Enter **cycles** عادي → مهم → عاجل → عادي. Dot styles: عادي = solid `#6b778a`; مهم = hollow, 2 px ring `#D9A441`; عاجل = solid `#D9A441`. Accessible name `الأولوية: {label}`.

## 9. Category dropdown (custom popup)

Build as a frameless popup widget (`Qt.Popup | Qt.FramelessWindowHint`, translucent, with a 32 px transparent margin for the shadow). Do not use `QComboBox` or `QMenu`.

- **Panel:** width 176, padding 4, background `#1c2533`, 1 px border `#283241`, radius 12, shadow `0 12px 32px rgba(0,0,0,.5)`. Height = 4 + 6×40 + 4 + 2 border = **250**.
- **Items (6, in this order, 40 px tall each, radius 8, padding 0 12):** `عام` (general) · `عمل` (work) · `شخصي` (personal) · `دراسة` (study) · `صحة` (health) · `المنزل` (home).
  - Label 14 Regular `#F2F5F8` at the start (right); a `ph.check-bold` 16×16 `#8FB8D8` at the end (left), **visible only on the selected item** (space reserved when hidden).
  - Hover or keyboard-highlight background `#283241`. Role *option*, `aria-selected` equivalent set on the current one.
- **Placement:** right edge aligned to the trigger's right edge, 6 px gap. Dock chip → open **upward**; row category button → open **downward**. If it does not fit inside the window (8 px margin), flip to the other side; if neither fits, clamp inside the window. Clamp horizontally 8 px inside the window.
- **Open:** focus goes to the selected item.
- **Keys:** Up/Down move (wrapping), Home/End jump, Enter/Space choose, Escape closes and returns focus to the trigger, Tab closes. Clicking an item chooses it and closes. Clicking outside closes without change. Clicking the trigger again closes it.
- **Choose:** dock chip → sets the *current category for new tasks*; row button → updates that task and persists.

## 10. Pinned-mode context menu (new, reuses tokens)

Right-click on the window shows a popup in the same style as §9 (panel `#1c2533`, radius 12, items 40 px, hover `#283241`), width 220, with a 1 px `#283241` separator (margin 4 8) before the last two items. Items in order: `إضافة مهمة` (focus the input), `نقل غير المكتمل`, `تثبيت` / `إلغاء التثبيت` (matches the pin state), `إعدادات`, ─── `فتح بيانات التطبيق`, `إغلاق التطبيق`. Items for unbuilt features are **disabled** (text `#4A586B`), never no-ops.

## 11. Keyboard and focus map

- **Tab order:** Pin → Archive → Settings → Close → (each open row: checkbox → title → category button → delete) → completed header → (completed rows: checkbox → title → delete) → input → Add → Category chip → Priority chip. Shift+Tab reverses. (Visual right-to-left within a row is the same as logical order.)
- **Everything focusable shows the 2 px `#8FB8D8` ring** (offset 2) except the input field, which uses the focus border+glow.
- **Global:** Enter in input adds; Escape in input clears nothing and does nothing; F2 on a title edits it.
- **Proposed shortcuts (when the window has focus):** `Ctrl+N` focuses the input; `Ctrl+Shift+P` toggles the pin.
- Pinned mode must not steal focus when the user clicks the desktop; the window takes focus only when the user clicks an input or interactive control.

## 12. Data touched by the UI

- **Task:** id, text, category (`general|work|personal|study|health|home`), priority (`normal|important|urgent`), completed, sort\_order, created/updated timestamps. Empty text is never persisted.
- **UI state to persist:** window position, size, pinned flag, completed-group expanded (session only), last-used category (session only).
- The UI layer never touches SQL; it talks to services and receives plain objects.

## 13. Qt implementation notes

### 13.1 What QSS cannot do (paint or code it)

Box shadows (use a translucent window margin + `QGraphicsDropShadowEffect` on the panel, or paint it), the 3 px focus glow, hover transitions (use `QVariantAnimation` or accept instant change), the edge fade (overlay gradients), the circular progress ring (custom `paintEvent`), and per-state icon colors (qtawesome, §1.4).

### 13.2 Icon button helper (see §1.4)

```python
# app/ui/widgets/icon_button.py
from PySide6.QtCore import QEvent, QSize
from PySide6.QtWidgets import QToolButton
from app.ui.icons import icon

class IconButton(QToolButton):
    """36x36 icon button; the color per state is picked here, the background by QSS."""
    def __init__(self, key, idle="#98A2B3", hover="#F2F5F8", disabled="#4A586B", size=18):
        super().__init__()
        self._key, self._colors = key, (idle, hover, disabled)
        self.setFixedSize(36, 36)
        self.setIconSize(QSize(size, size))
        self.setAutoRaise(True)
        self._refresh()

    def _refresh(self):
        idle, hover, disabled = self._colors
        if not self.isEnabled():
            color = disabled
        else:
            color = hover if self.underMouse() else idle
        self.setIcon(icon(self._key, color))

    def enterEvent(self, e):
        self._refresh(); super().enterEvent(e)

    def leaveEvent(self, e):
        self._refresh(); super().leaveEvent(e)

    def changeEvent(self, e):
        if e.type() == QEvent.EnabledChange:
            self._refresh()
        super().changeEvent(e)
```

The colors per state come from the tables in §4 to §9. The pin button reuses this class: when active it switches its key to `pin_active` and uses `#D9A441` for both idle and hover. Pressed uses the hover color.

### 13.3 Progress ring paint sketch

```python
rect = QRectF(4, 4, 36, 36)            # radius 18 inside a 44x44 widget, pen 4
pen = QPen(TRACK, 4); pen.setCapStyle(Qt.RoundCap)
p.setRenderHint(QPainter.Antialiasing)
p.setPen(pen); p.drawEllipse(rect)
if total and done:
    pen.setColor(SUCCESS if done == total else TRUST); p.setPen(pen)
    p.drawArc(rect, 90 * 16, int(-360 * 16 * done / total))   # clockwise from 12 o'clock
```

Animate `done/total` as a float with a 350 ms `OutCubic` `QVariantAnimation`.

### 13.3b Other rules

- Draw all rounded surfaces with anti-aliasing; avoid QSS `border-radius` on the top-level window (it does not clip children).
- Use `QFontMetrics`/layouts for wrapping rows; row height must be computed, not fixed.
- Never hardcode `left`/`right`; rely on `layoutDirection` and `Qt.AlignLeading`/`AlignTrailing`.
- Keep colors, sizes and strings in one `theme.py`/`strings_ar.py` so the values in this document exist exactly once in code.

## 14. Accessible names (Arabic)

| Control | Name |
| --- | --- |
| Pin (active / inactive) | `إلغاء التثبيت` / `تثبيت` |
| Archive / Settings / Close | `الأرشيف` / `إعدادات` / `إغلاق` |
| Progress ring | `أُنجز {done} من {total}` |
| Task checkbox | the task text (role checkbox, checked state) |
| Category button on row | `تغيير الفئة: {category}` |
| Delete | `حذف المهمة` |
| Input / Add | `مهمة جديدة` / `إضافة المهمة` |
| Category chip / Priority chip | `الفئة` / `الأولوية: {label}` |
| Dropdown | `اختيار الفئة` (role list, items role list item with selected state) |

## 15. Acceptance checklist

- [ ] Window renders 380×640 with 16 px radius, 1 px `#283241` border, correct shadow per pin state.
- [ ] Top bar: pin at the far right, grip centered, ✕ / settings / archive at the far left in that screen order.
- [ ] Pin is amber with filled icon and amber-12 background when pinned; gray outline otherwise.
- [ ] Hijri day is the 56 px hero numeral; Gregorian date is 14 px secondary subtext; weekday above in `#8FB8D8`.
- [ ] Ring is 44 px, animates 350 ms, turns green at 100%, shows `done/total` left-to-right.
- [ ] Quote is upright, 14 px secondary, with a 2 px `#4F7CAC` rule on the right.
- [ ] Rows are two-line (title + meta), 18 px circles with 32 px hit areas, delete appears only on hover/focus.
- [ ] Completed tasks collapse into the `مكتملة · n` group and return to their place when unchecked.
- [ ] Double-click / Enter / F2 edits inline; Enter saves, Escape cancels, empty save cancels.
- [ ] Dock: input + add on row 1, category + priority chips on row 2; category persists after adding, priority resets.
- [ ] Category dropdown is the custom 250 px popup, fully keyboard operable, opens up from the dock and down from a row.
- [ ] Every interactive element has a visible focus ring, an accessible name, and a correct tab position.
- [ ] No colors, sizes or strings outside this document.

* [ ] No PNG or SVG icon files in the repo: every icon comes from qtawesome (Phosphor) and renders in the packaged exe.
