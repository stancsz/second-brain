# Adequacy audit: window-coherence (G32)

Three lazy artifacts that would pass a weak suite — and how this suite blocks each:

1. **Checks `add()` only, ignores `update()` and `supersede()`** — a partial fix
   where a backwards window slips in via `update(sb_valid_to=...)` to before an
   existing `valid_from`, or via `supersede(as_of=...)` with an `as_of` that
   precedes the old fact's `valid_from`. Blocked by Phases 2 & 3: assert ValueError
   on the update and supersede paths, including the supersede-as_of-before-open case.

2. **String compare instead of temporal compare** — uses `valid_from > valid_to`
   on raw strings, which mis-orders mixed date/datetime forms (e.g.
   `"2023-06-01T12:00:00"` vs `"2023-06-01"` compare wrong lexicographically).
   Blocked by Phase 1's mixed date/datetime backwards case, which a naive string
   compare would let through (or wrongly reject in Phase 4).

3. **Rebuild crashes on a backwards window instead of quarantining** — validation
   that raises inside `rebuild_validity_index`, so one hand-authored OKF file with
   `valid_from > valid_to` takes down the whole rebuild. Blocked by Phase 5:
   injects a backwards window into metadata, asserts the rebuild completes, the
   good row survives, and the backwards one is quarantined (no row).

The suite drives the real CLI (Phase 6): a backwards `--valid-from/--valid-to`
must produce a clean message with no traceback, blocking a fix that guards the
Python API but lets the CLI dump a stack trace. It also asserts (Phase 4) that
coherent and equal-bound windows are NOT over-rejected — guarding against a fix
that is too aggressive.
