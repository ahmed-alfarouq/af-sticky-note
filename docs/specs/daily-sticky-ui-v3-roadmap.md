# Daily Sticky v3 — Implementation Roadmap

> Proposal only; no phase is authorized by this document. Each phase is
> independently reviewable with its own acceptance evidence. Category data
> work (migration 006) is complete and is not re-scheduled. Full suite
> baseline at split: 443 passed (offscreen); known sandbox skip may recur.

## Ordering principles

Foundations (deps, icons, theme, shell) before dependent UI; data decisions
before the widgets that display them; packaging verification last. Idle-CPU
rule holds everywhere: no polling, no background threads, no paint-path I/O;
single midnight timer only; cached icons; repaint-on-change.

## R-icons — qtawesome/Phosphor migration

- Objective: `qtawesome>=1.4,<2.0` dep, `QT_API=pyside6` first in `main.py`, `app/ui/icons.py` `(key,color)` lru_cache per §1.4/§13.2, replace PNG usage surface by surface, keep PNGs until every surface migrates (checklist item 14 flips last).
- Prerequisites: none (spec complete).
- Likely files: `requirements.txt`, `app/main.py`, new `app/ui/icons.py`, `packaging/DailySticky.spec` (`collect_data_files("qtawesome")`), icon tests.
- Tests: glyph-key resolution, per-state colors, cache identity, no-paint-path `qta.icon` calls, frozen-bundle render check, packaged-exe icon confirmation on real Windows.
- Perf: cache-only; zero paint-path loading.
- Exclusions: no widget redesign; no PNG deletion until checklist flips.
- Acceptance: checklist item 14 green + exe screenshot/log evidence.

## R-theme — tokens, typography, digits, strings

- Objective: centralize remaining hardcoded colors into tokens; apply role table (§1.2); resolve `.woff2`-vs-`.otf`, weight mapping, fallbacks; decide `٪` vs `%`; remove Arabic `letter-spacing`; single `theme.py`/`strings_ar.py` for spec values.
- Prerequisites: none (R-icons independent; coordinate token names).
- Likely files: `app/ui/styles/app_style.py`, new theme/strings modules, `fonts.py`, ring/stats formatting.
- Tests: token-exactness tests, typography spot tests, digit-format tests, object-name coverage stays green.
- Exclusions: no layout/geometry changes.
- Acceptance: §15 item 13 green.

## R-shell — window shell, pin model, geometry

- Status note: shell foundation landed separately (default 380×640, min 320×480, radius bound to theme token; zero-margin silhouette retained). Remaining here: 32px shadow margin + per-pin-state shadows + pin/unpin model; the margin requires restructuring the central layout and mask translation and needs the pin model for shadow switching, so it ships with the pin work below, not before it.
- Objective: 32px shadow margin + shadows per pin state; pin/unpin model (platform API, persistence, taskbar, stacking, focus-no-steal); 6px resize borders; drag via grip/empty areas with cursors.
- Prerequisites: R-theme (tokens). Needs pin platform API design (desktop layer exists; pin toggle is new).
- Likely files: `main_window.py`, `note_shape.py` (or shadow-margin successor), `geometry_manager.py` (+pin flag), platform windows/desktop.
- Tests: geometry/persist tests, pin-state machine tests (mocked platform), focus/taskbar checks where offscreen-observable; real-Windows manual check.
- Perf: shape/mask rebuilt on resize only (existing rule kept).
- Exclusions: top-bar content redesign (R-topbar).
- Acceptance: checklist item 1 green.

## R-topbar — pin/grip/actions, IconButton helper

- Objective: pin/grip/actions per §4 (36×36, order, states, tooltips `تثبيت…`/`إلغاء التثبيت`, failure rollback, disabled `غير متاح بعد` rule, focus rings).
- Prerequisites: R-icons, R-shell (pin API + shell metrics).
- Likely files: header construction in `main_window.py`, new `icon_button.py`, settings/history entry points.
- Tests: state-table tests, tooltip/a11y tests, failure-rollback test, disabled-state test.
- Exclusions: archive-view content (exists as history viewer; naming decided here).
- Acceptance: checklist items 2–3 green.

## R-hero — date column, DateDisplay, Umm al-Qura, ring, quote

- Objective: `DateDisplay` contract; converter decision (Umm-al-Qura library vs custom, with equivalence evidence); hero typography/margins; 44px ring with `done/total` LTR center, 350ms animation, `أُنجز…` name; quote rule/elision/tooltip/upright.
- Prerequisites: R-theme (tokens/type), R-icons (none needed).
- Likely files: `clock.py`, new date-display contract, `date_header.py`, `progress_ring.py` (+QVariantAnimation, OS-animation-off → 0), `quote_widget.py`.
- Tests: converter equivalence vectors, contract tests, ring geometry/animation tests (mocked clock), quote elision tests.
- Perf: animation only on change; repaint-on-change kept.
- Exclusions: midnight/rollover logic (already correct).
- Acceptance: checklist items 4–6 green.

## R-rows — task rows, inline edit, delete, completed group

- Objective: row geometry/order per §7.2; checkbox state table + press scale + focus transfer; inline edit per §7.4 (incl. 200-limit, focus return); hover delete per §7.6; collapsible group + session state per §7.7; meta line (category button + priority label with مهم/عاجل mapping — requires priority-model decision: map LOW/MEDIUM/HIGH or adopt عادي/مهم/عاجل with migration).
- Prerequisites: R-icons, R-theme, R-hero (ring counter updates).
- Likely files: `task_item.py`, `task_list.py`, edit-field widget (new or dialog evolution), QSS row rules.
- Tests: geometry/wrap (existing 31 must stay green), edit state machine, delete/refresh, collapse session tests, focus-transfer tests.
- Perf: height-for-width layouts only; no timers except press/ring animations.
- Exclusions: dropdown widget itself (R-dropdown); data-model changes beyond the decided priority mapping.
- Acceptance: checklist items 7–9 green.

## R-dock — input dock, chips, add semantics

- Objective: dock per §8 (divider, 50px field, glow, disabled-add, placeholder/a11y names); category-kept + priority-reset fix; category/priority chips with cycling, dots, menus.
- Prerequisites: R-icons, R-theme; priority-model decision from R-rows.
- Likely files: dock construction, `task_input.py`, chip widgets, QSS dock rules.
- Tests: add-semantics tests (update the reset test), chip state/cycle tests, focus/scroll tests.
- Exclusions: popup widget internals (R-dropdown).
- Acceptance: checklist item 10 green.

## R-dropdown — custom category popup (8 items)

- Objective: frameless custom popup per §9 (176 panel, 8×40px items for the amended set, checkmark, keyboard map, up/down flip/clamp, choose semantics for chip vs row).
- Prerequisites: R-icons, R-dock/R-rows triggers; eight-category data complete.
- Likely files: new popup widget, chip/row trigger wiring, removal of combo usage for categories.
- Tests: geometry (8-item height derived, not hardcoded 250), keyboard map, placement flip/clamp (mocked screens), focus restoration, screen-reader roles.
- Perf: built on open, destroyed on close; no polling.
- Exclusions: priority selection UX.
- Acceptance: checklist item 11 green.

## R-menu — pinned-mode context menu

- Objective: §10 popup (220px, ordered items, separator, pin-label state, disabled-not-noop).
- Prerequisites: R-shell (pin state), R-icons.
- Likely files: menu builder, wiring for focus-input/carry-forward/settings/open-data-dir/exit.
- Tests: item order/states, disabled items, action dispatch tests.
- Exclusions: task-row menus (exist).
- Acceptance: covered under checklist item 12.

## R-kbd-a11y — tab order, shortcuts, focus, names

- Objective: §11 tab order, 2px rings (input glow exception), Enter/Esc/F2, Ctrl+N / Ctrl+Shift+P, no-focus-steal; §14 name corrections.
- Prerequisites: all widgets exist (R-topbar…R-menu).
- Likely files: focus policies, shortcut map, accessible names/descriptions.
- Tests: tab-order walk test, shortcut tests, focus-ring presence tests, a11y-name table test.
- Exclusions: visual redesign.
- Acceptance: checklist item 12 green.

## R-package — packaged verification

- Objective: installer + frozen exe on real Windows: icons render, fonts load, tray/startup/pinning work, DB isolated per-user.
- Prerequisites: all above.
- Likely files: spec/installer only if evidence demands.
- Tests/checks: `test_packaging.py` + manual exe runbook with screenshot/log evidence.
- Acceptance: checklist item 14 (exe half) + release readiness.

## Deferred / needs decisions

Priority-model mapping (LOW/MEDIUM/HIGH vs عادي/مهم/عاجل — data migration implications); `.woff2` vs shipped `.otf`; Umm-al-Qura library choice; archive-vs-history naming; interactive prototype absent (written spec governs).

## Approved planning decisions (Phases 0K/0L — binding)

- **Fonts:** retain shipped `.otf` files; no conversion to `.woff2`; no license file invented or added. License verification remains outstanding.
- **Hijri calendar:** retain the dependency-free converter unless Umm-al-Qura reference-vector tests demonstrate a meaningful mismatch. No new dependency.
- **Archive/history:** retain current `السجل` terminology; revisit the user-facing label in the top-bar phase.
- **Prototype:** proceed on the written specification; do not claim pixel parity for unverifiable visuals.
- **Priority (explicitly unresolved):** no relabeling, no hidden levels, no value migration until a product decision defines lossless semantics. **R-rows stays blocked**; other phases proceed only where they do not touch priority semantics.
