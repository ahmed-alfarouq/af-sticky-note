# Daily Sticky v3 — Reconciliation Matrix

> Evidence-based comparison of the canonical specification
> (`daily-sticky-ui-v3.md`, transcribed from `daily-sticky-ui-v3-source.md`)
> against the actual repository at HEAD `9068d68` (+ uncommitted Phases
> 7I–7N/0B–0I work). Statuses: `implemented` / `partially implemented` /
> `not implemented` / `conflicting` / `unverified`. A passing test is cited
> as test evidence only; visual/packaging/WM behavior is marked accordingly.

## §0 Global rules (§15: "No colors, sizes or strings outside this document")

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-0-RTL-01 | Entire UI RTL; `setLayoutDirection(RightToLeft)`; first-added renders right | implemented | `app/main.py:184`; per-widget directions (`category_selector.py:46`, `priority_selector.py:76`, `history_window.py:64`, dashboard) | RTL tests green | — |
| V3-0-DIGIT-01 | Western digits everywhere incl. dates/counters | partially implemented | Gregorian digits in dates; ring/stats paint Arabic-Indic `٪` (`progress_ring.py:83`) | — | Decide `٪` vs `%`; R-typography |
| V3-0-ICON-01 | Phosphor via qtawesome; retire PNGs | conflicting | PNG family `assets/icons/` + `CategoryIconProvider`; zero qtawesome/qtpy refs; no `QT_API` setup | PNG-based icon/packaging tests | Icon migration; see §B |
| V3-0-FORBID-01 | No italic Arabic / emoji icons / native combo-menu styling / Arabic letter-spacing / unlisted colors | conflicting | Emoji buttons (`main_window.py`); native `QComboBox` selectors; `letter-spacing: 0.3px` on `dateLabel` (`app_style.py:137`); scattered hardcoded hex | stylesheet tests | Redesign phases |
| V3-0-UNITS-01 | Logical px, no manual HiDPI scaling | implemented | No device-pixel math in UI code | `test_note_shape.py` | — |

## §1 Design tokens

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-1-COLOR-01 | Exact 18-token palette; no red/coral/gradients | partially implemented | `COLOR_*` (`app_style.py:22-38`) cover most tokens; hardcoded hex scattered (`#E57373`, `#242F42`…); no red/coral/gradients | object-name coverage guard | Finish centralization; R-theme |
| V3-1-TYPE-01 | Thmanyah Regular/Bold; 500→Regular 600/700→Bold; fallbacks | partially implemented | `fonts.py` + bundled `fonts/thmanyah/*.otf` (**conflicting**: spec says `.woff2`); weight mapping implicit; fallback string differs | `test_fonts.py` | Resolve woff2-vs-otf; R-theme |
| V3-1-TYPE-02 | Role table sizes/line-heights/colors | partially implemented | Per-widget sizes differ from table (ring center 9px vs 12; task 14px vs 16) | font-size coverage test | R-theme |
| V3-1-SCALE-01 | Spacing scale, radii, motion, shadows | partially implemented | Radii/spacing approximated; **no motion system** (ring has no 350ms animation); **no shadow system** (organic mask instead) | — | R-shell / R-motion |
| V3-1-ICON-02 | qtawesome dep, `QT_API` order, bold/fill weights, (key,color) cache, PyInstaller data | not implemented | None exists; per-key PNG cache instead | PNG-based icon tests | Icon migration |

## §2 Window shell (§15: 380×640, radius, border, shadow per pin state)

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-2-SIZE-01 | Default 380×640 excl. shadow margin; min 320×480; list grows | conflicting | Default 380×560, min 320×420 (`geometry_manager.py:27-30`); no shadow-margin concept (paper IS the window) | `test_note_shape.py` | R-shell |
| V3-2-FRAME-01 | Frameless translucent, 32px shadow margin, flat bg, 1px border, radius 16, rounded clipping | partially implemented | Frameless/translucent/rounded-mask/border implemented; **no 32px margin** (zero-margin silhouette) | shape/mask tests | R-shell |
| V3-2-PIN-01 | Pinned: small shadow, below windows, no taskbar icon, no focus steal; unpinned: big shadow, normal taskbar | not implemented | `Qt.Tool` only (no taskbar/Alt-Tab); no pin states, shadows, or focus policy | — | R-shell (pin model + platform) |
| V3-2-MOVE-01 | Grip/empty-area drag, closed-hand cursor, persist on release; 6px resize borders | implemented | Header drag + 8px edges (spec: 6px — minor delta), cursors, save-on-release | main-window drag/resize tests | Align border metric in R-shell |
| V3-2-CHROME-01 | No title text/bar/icon | implemented | Frameless, no title bar | — | — |

## §3 Vertical layout map

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-3-MAP-01 | Block order/heights/edges (44/147/quote/list/115; 24px text edge; 12px shared edge) | partially implemented | Same block order; different metrics (no chips row; dock is input-card + selectors; hero structure differs) | layout tests | R-shell/R-dock |

## §4 Top bar (§15: pin right, grip centered, actions left)

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-4-PIN-01 | 36×36 pin toggle, states, tooltips `تثبيت على سطح المكتب`/`إلغاء التثبيت`, persistence, failure rollback | not implemented | Decorative pin `QLabel` only (no toggle, no states) | — | R-topbar (needs pin platform API) |
| V3-4-GRIP-01 | 32×4 pill, drag-only, cursors, non-focusable/a11y-hidden | partially implemented | Header drag area works; no pill widget, no open-hand cursor | drag tests | R-topbar |
| V3-4-ACT-01 | Archive/Settings/Close 36×36, order, states, tooltips `الأرشيف`/`إعدادات`/`إغلاق`, disabled `غير متاح بعد` rule | partially implemented | Exit/history/settings buttons functional (history viewer ≈ archive but named `فتح السجل اليومي`; close tooltip differs); pin-decorative; no disabled states | exit/settings/history tests | R-topbar (rename vs keep decided there) |

## §5 Date hero (§15: 56px Hijri hero, 14px Gregorian, weekday soft)

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-5-DATE-01 | Column order/sizes/margins, Hijri-dominant hierarchy, exact month/weekday strings, `هـ` suffix | partially implemented | Hierarchy + Arabic names + suffix present; exact px/margins differ; string tables overlap but unverified item-by-item | `test_date_format.py`, main-window header tests | R-hero (typography pass) |
| V3-5-DATA-01 | `DateDisplay` domain contract; UI formats only | not implemented | Widget calls `get_date_parts()` directly; no contract type | — | R-hero |
| V3-5-HIJRI-01 | Umm al-Qura calendar (library decision) | partially implemented | Custom `gregorian_to_hijri` converter + Qt Hijri fallback (`clock.py`); Umm-al-Qura compliance **unverified** | date tests | R-hero (converter decision) |
| V3-5-MID-01 | Midnight re-evaluation + hero refresh + day load/create | implemented | Single-shot midnight timer + activation catch-up + in-place refresh | lifecycle tests (4/4 green) | — |
| V3-5-RING-01 | 44px ring, track/arc colors, 12-o'clock clockwise sweep, round caps, 0/0, green-100%, LTR `done/total`, 350ms animation, a11y `أُنجز {done} من {total}` | partially implemented | 52px ring, correct colors/sweep/caps/0%/green/today-only counts; **center shows percent not `done/total`**; **no animation**; tooltip/a11y text differs (`التقدم: …`) | ring/date-header tests | R-hero |
| V3-6-QUOTE-01 | (§6) upright 14px secondary, right rule, 3-line elision + tooltip, daily stability | partially implemented | Centered «…» quotes, daily stability verified; **no vertical rule, no elision/tooltip, decorative quotes present** | quote test suite | R-hero |

## §7 Task list (§15: two-line rows, 18px circles, hover delete, collapse, inline edit)

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-7-BOX-01 | Scroll geometry, vertical-only, styled scrollbar, 8px fades, spacing, empty/all-done strings | partially implemented | Vertical-only + styled scrollbar verified; **no edge fades**; empty label + `مكتملة • N` exist with different strings | wrap/scroll tests | R-rows |
| V3-7-ROW-01 | Padding/geometry, checkbox·body·delete order, top alignment, 59/40px heights | partially implemented | Order is checkbox·text·[category icon·priority dot] (no delete button, meta-as-icons); heights computed not fixed | row geometry tests | R-rows |
| V3-7-CHECK-01 | Circle states, press animation, focus ring on 32px hit area, toggle-move + focus transfer, checkbox role | partially implemented | Toggle/move/ring-update verified; custom icon checkbox (no 1.5px ring states, no press scale, no focus transfer) | priority/row tests | R-rows |
| V3-7-TITLE-01 | 16/24 wrap, done colors, I-beam, tab stop | partially implemented | Wrap + done styling verified (14px, own colors); I-beam/tab-stop **unverified** | row tests | R-rows + R-kbd |
| V3-7-EDIT-01 | Inline edit: triggers, field geometry/glow, Enter/Esc/focus-lost, trim, empty-cancels, 200-limit, focus return | not implemented | Modal `TaskEditDialog` instead; **no 200-char limit anywhere** (grep-verified) | dialog tests (different UX) | R-rows |
| V3-7-META-01 | Category button + priority label (مهم hollow/عاجل solid, عادي hidden), dropdown below, a11y `تغيير الفئة: {category}` | partially implemented | Icon + tooltip convention instead of button + text label; dots use different level mapping (HIGH/MEDIUM/LOW); dropdown is a combo opening on click | category/mutation tests | R-rows + R-dropdown |
| V3-7-DEL-01 | Hover/focus delete button, hover bg, instant delete, history-safe, counter refresh, a11y `حذف المهمة` | partially implemented | Menu-only delete; history-safe + refresh verified; no hover button | delete tests | R-rows |
| V3-7-GROUP-01 | Collapsible `مكتملة · {n}` header, chevrons, session persistence | not implemented | Static always-visible label; no collapse/state | — | R-rows |

## §8 Input dock (§15: two rows, category kept, priority reset)

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-8-DOCK-01 | Divider/padding/field geometry/focus-glow/disabled-add/placeholder/a11y `مهمة جديدة`/`إضافة المهمة` | partially implemented | Input + `+` + selectors dock verified; placeholder/accessible names differ; `+` text button (no icon/states); **no disabled-when-empty**; no painted glow | 7H/input tests | R-dock |
| V3-8-ADD-01 | Trim/empty-add-keeps-focus/scroll, priority reset + category kept | conflicting | Priority reset ✓ + focus ✓ verified; **category also resets** (spec: kept) | reset/preserve tests | R-dock (one-line semantics + test) |
| V3-8-CHIP-01 | Category/priority chips, cycling, dot styles, a11y `الفئة`/`الأولوية: {label}` | partially implemented | Combo selectors (not chips); priority HIGH/MEDIUM/LOW model differs from عادي/مهم/عاجل; no cycling | selector tests | R-dock (priority model decision first) |

## §9 Category dropdown (§15: custom 250px popup, keyboard, up/down placement)

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-9-DROP-01 | Frameless custom popup (no QComboBox/QMenu); 176×250 panel; 6×40px items; checkmark; hover/keyboard highlight; roles | conflicting | Native `QComboBox` + content-fitted popup (`combo_popup.py`); no fixed 176×250 geometry | popup-fit tests | R-dropdown (custom widget) |
| V3-9-DROP-02 | Six items in spec order + labels | **superseded** | Eight active per amendment (selector asserts 8/order/names); original six retained in canonical text only | selector tests | — (amendment governs) |
| V3-9-DROP-03 | Placement (right-aligned, 6px gap, up/down, flip/clamp), focus/keys/outside-click/trigger-toggle, choose semantics | partially implemented | Combo popup handles placement natively; screen-clamp + ElideNone verified; no flip rules, partial keyboard (combo-native) | popup tests | R-dropdown |
| V3-9-GEO8-01 | Eight-item geometry reconciliation (amendment, not original) | unverified | Content-fitted popup adapts to 8 rows; custom-popup geometry TBD in R-dropdown | popup tests (6-row-era logic, still passing) | R-dropdown |

## §10 Pinned-mode context menu

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-10-MENU-01 | 220px popup, six ordered items, separator, pin-label state, disabled-not-noop | not implemented | Different menus exist (task rows: edit/category/priority/delete; list: dashboard/history/settings/clear) — none match | menu tests (other menus) | R-menu (needs pin model) |

## §11 Keyboard and focus map

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-11-KBD-01 | Full tab order, focus rings (input glow exception), Enter/Esc/F2, Ctrl+N, Ctrl+Shift+P, no-focus-steal | not implemented | Enter-in-input adds ✓; zero tab-order/shortcut/F2 hits (grep-verified); focus rings partial | — | R-kbd (after widgets exist) |

## §12 Data touched by the UI (amendment-flagged)

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-12-TASK-01 | Task contract incl. category union of six IDs; priority normal/important/urgent; `sort_order` field; UI state persistence set | conflicting | Model uses `LOW/MEDIUM/HIGH`, bool completed, position (no `sort_order`); category union **superseded to eight** by amendment; geometry persisted, no pin flag/session states | model/repo/rollover/report tests | R-data (union already 8 via 006; priority-model + `sort_order` decisions) |
| V3-12-LAYER-01 | UI never touches SQL | implemented | Service/repo layering; UI SQL-free | architecture tests | — |

## §13 Qt implementation notes

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-13-QSS-01 | Paint/code shadows, glow, transitions, fades, ring, per-state icon colors | partially implemented | Custom ring paint ✓; no shadows/glow/transitions/fades/animations | paint/shape tests | Respective R-phases |
| V3-13-BTN-01 | `IconButton` helper + pin reuse | not implemented | Per-widget QPushButtons; no helper | — | R-topbar |
| V3-13-RING-01 | Paint sketch + 350ms OutCubic animation | partially implemented | Sketch-equivalent paint at different geometry; no animation | — | R-hero |
| V3-13-RULES-01 | AA rounded surfaces; computed row heights; AlignLeading/Trailing; single `theme.py`/`strings_ar.py` | partially implemented | AA + computed heights ✓; explicit AlignRight (not Leading/Trailing); colors partly centralized, strings inline | — | R-theme |

## §14 Accessible names

| ID | Requirement | Status | Implementation evidence | Test evidence | Gap / next |
|---|---|---|---|---|---|
| V3-14-A11Y-01 | Pin/archive/close/ring/checkbox/category/delete/input/chips/dropdown names | partially implemented | Match: `حذف المهمة`, `إضافة المهمة`, `الفئة`, checkbox-by-text; differ: close/history/ring/dropdown names; missing: pin/archive names | a11y assertions in widget tests | Respective R-phases |

## §15 Acceptance checklist (maps to rows above)

| # | Checklist item | Status |
|---|---|---|
| 1 | 380×640, radius, border, shadow per pin | conflicting (V3-2-SIZE-01/FRAME/PIN) |
| 2 | Top bar order | partially implemented (V3-4) |
| 3 | Pin amber/filled vs gray | not implemented (V3-4-PIN-01) |
| 4 | 56px Hijri hero, Gregorian subtext, weekday | partially implemented (V3-5-DATE-01) |
| 5 | 44px animated ring, green 100%, LTR done/total | partially implemented (V3-5-RING-01) |
| 6 | Quote rule/upright/elision | partially implemented (V3-5-QUOTE-01) |
| 7 | Two-line rows, circles, hover delete | partially implemented (V3-7-*) |
| 8 | Collapse group + order restore | partially implemented (order restore ✓ via position; collapse ✗) |
| 9 | Inline edit semantics | not implemented (V3-7-EDIT-01) |
| 10 | Dock rows, category-kept/priority-reset | conflicting on category-kept (V3-8-ADD-01) |
| 11 | Custom 250px dropdown, keyboard, up/down | conflicting (V3-9-DROP-01) |
| 12 | Focus rings, names, tab order | partially implemented (V3-11-KBD-01) |
| 13 | Nothing outside document | conflicting (V3-0-FORBID-01, V3-1-COLOR-01) |
| 14 | No PNG/SVG; qtawesome in exe | conflicting (V3-0-ICON-01, V3-1-ICON-02) |

## Amendment-affected rows

V3-9-DROP-02, V3-9-GEO8-01, V3-12-TASK-01 (category union), plus all category-behavior phases: the amendment governs implementation; the original six-category text is retained above verbatim.

## Unverified items

Exact px rendering (no pixel/golden tests), packaged-exe icon/font rendering, real Windows WM behavior (pin/taskbar/focus), Umm-al-Qura day-level equivalence, I-beam/tab-stop presence. The interactive v3 prototype (§E) is not in the repo or supplied material; the written spec governed this audit.
