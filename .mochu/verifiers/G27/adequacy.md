# Adequacy audit: restore-psych-dims (G27)

Three lazy artifacts that would pass a weak suite — and how this suite blocks each:

1. **Re-syncs affect but forgets subject and/or validity** — a partial fix that
   wires `_sync_affect_for` into `restore()` but not subject/validity. Blocked by
   Phases 2–4: asserts ALL THREE dims (affect, subject sub-graph membership,
   validity window) return after restore, independently.

2. **"Fix" only works on the live path where rows were never dropped** — a test
   that does `add -> delete -> restore` with no rebuild in between never exercises
   the bug, because soft-delete alone keeps the derived rows; only a `bundle.rebuild`
   drops them. Such a suite passes against the UNFIXED code. Blocked by Phase 1:
   the concept goes through a real `export -> rebuild` into a fresh db, and the
   suite first ASSERTS the psych rows are gone (bug precondition) before testing
   that restore brings them back.

3. **Restores a row but with stale/empty values** — re-inserts an affect/validity
   row from a default or partial source rather than the concept's actual metadata,
   so a row "exists" but the data is wrong. Blocked by Phases 2 & 4: asserts the
   restored values EXACTLY equal the originals (emotion=grief, valence=-0.8,
   intensity=0.9; valid_from/valid_to exact), not merely that a row is present.

The suite drives the real CLI via subprocess (Phase 5): `brain restore` then
`brain show` must display the affect + validity window again, blocking a fix that
repairs the Python API but leaves the user-facing path broken.
