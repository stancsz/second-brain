# Adequacy audit: iso-validation (G26)

Three lazy artifacts that would pass a weak suite — and how this suite blocks each:

1. **Validates `add()` but not `update()` / `supersede()`** — a partial fix that
   guards only the create path. A bad date slips in via `update(sb_valid_to=...)`
   or `supersede(as_of=...)`. Blocked by Phase 1: asserts ValueError on all three
   write paths (add, update, supersede), not just add.

2. **Rebuild crashes on a bad date instead of quarantining** — naive validation
   that raises inside `rebuild_validity_index`, so one hand-authored OKF file with
   a malformed date takes down the entire rebuild (every other concept's index is
   lost). Blocked by Phase 3: injects a garbage date directly into metadata,
   asserts the rebuild completes without crashing AND the good concept still gets
   its row AND the bad one is quarantined (no row).

3. **Over-strict validator rejects valid dates too** — e.g. accepts only
   `YYYY-MM-DD` and rejects ISO datetimes (`2023-06-15T12:30:00`) or valid leap
   dates (`2024-02-29`), silently dropping legitimate windows. Blocked by Phase 2:
   asserts a date, an ISO datetime, and a leap-year date are all accepted and
   stored verbatim.

The suite drives the real CLI via subprocess (Phase 5), blocking a fix that
validates in `brain.py` but lets the CLI dump a raw traceback on bad `--valid-from`.
