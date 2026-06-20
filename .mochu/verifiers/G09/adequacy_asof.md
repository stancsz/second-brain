# Adequacy audit: temporal-asof (G09 M2)

Three lazy artifacts that would pass a weak suite — and how this suite blocks each:

1. **Schema-only, query ignores validity** — `recall_as_of` just runs
   `SELECT * FROM concepts WHERE deleted=0` without joining `validity`.
   Superseded facts always appear regardless of as-of. Blocked by Phase 3+4
   (NYC→SF: asserts the closed-window NYC fact is EXCLUDED at as-of 2024, not
   just that SF appears).

2. **Forgets timeless notes** — uses `valid_from <= as_of` (no COALESCE),
   so Concepts with no validity row (no JOIN match) produce NULL and the
   WHERE clause excludes them. Blocked by Phase 2: asserts a timeless note
   appears for both past and future as-of dates.

3. **Inclusive valid_to boundary** — uses `valid_to >= as_of` instead of
   `valid_to > as_of`, so a fact that expired ON as-of day is incorrectly
   returned. Blocked by Phase 5: inserts a fact with `valid_to=2023-01-01`,
   asserts it is EXCLUDED at `as_of=2023-01-01` and INCLUDED at `as_of=2022-12-31`.

The suite drives the real CLI via subprocess (Phase 8), blocking a
stub-out of `recall_as_of` that never wires to the CLI parser.
