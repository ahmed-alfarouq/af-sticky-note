# Approved Amendment 01 — Eight Active Categories

> **Document status:** approved amendment, transcribed verbatim from the
> authorizing message. This file does **not** contain the original Daily
> Sticky v3 specification (not yet delivered) and does not replace it.
> The original six-category requirement is intentionally **not** rewritten
> here; it remains historically accurate wherever it was stated.
>
> *Recorded: 2026-10-14. Source: user-approved amendment message.*
> *Scope of this file: transcription only. No database, selector, or
> production change was made alongside it.*

## Amendment (authoritative, verbatim in substance)

This amendment supersedes the original six-category list. Daily Sticky must
have eight active categories:

1. `general` — `عام`
2. `work` — `عمل`
3. `personal` — `شخصي`
4. `study` — `دراسة`
5. `health` — `صحة`
6. `home` — `المنزل`
7. `religion` — `دين`
8. `life` — `حياة`

All eight categories must be active and selectable for new tasks. `general`
remains the default. Preserve the existing stable IDs for `religion` and
`life`, including all historical task and reporting associations. Do not
delete, rename, remap, or deactivate them. Reconcile the category dropdown's
height and positioning for eight items; do not blindly retain dimensions
calculated for six.

## Compatibility notes (repository facts, not new requirements)

- The four overlapping IDs already exist in `app/database/migrations/005_task_categories.sql`
  with matching Arabic labels (`religion`/`دين`, `work`/`عمل`, `life`/`حياة`,
  `general`/`عام`) and active state, so no rename or remap is needed for them.
- The four new IDs (`personal`, `study`, `health`, `home`) have no rows,
  references, or seeds anywhere in the current schema, migrations, tests, or
  fixtures; introducing them is purely additive.
- `general` is already the code-level default (`DEFAULT_CATEGORY_ID` in
  `app/core/models.py`, migration backfill target).
- The current dropdown is a content-fitted native `QComboBox`
  (`app/ui/widgets/combo_popup.py`), not a fixed six-item custom popup; its
  geometry must still be re-verified for eight items during implementation.
- No migration, seed change, or selector change was made in this
  documentation step. The additive migration is reserved for an explicitly
  authorized implementation phase.
