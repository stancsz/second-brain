# G09 M1 adequacy — bi-temporal validity storage

M1's bar: validity windows persist into a typed table, round-trip through the
Bundle, and `supersede()` correctly CLOSES the old fact's window and links the
new one WITHOUT discarding history (the bi-temporal invariant). Three lazy
artifacts a weak suite would accept, and how this suite blocks each:

1. **Schema-only (table exists, never populated / not derived).** A dev adds the
   `validity` table but never wires `add()`/`rebuild` to fill it. A
   `"validity" in sqlite_master` check would pass.
   *Blocked by:* step 1 asserts `add(sb_valid_from=…, sb_valid_to=…)` produces a
   typed row with the exact window, the no-validity Concept has NO row, and step
   4 asserts the row is reconstructed by `bundle.rebuild()` after a wipe.

2. **Supersede-by-delete (loses history).** A dev implements "supersede" as
   "soft-delete the old fact and add the new one." Queries for the current state
   would look right, but the historical fact is gone — which destroys the entire
   point of a bi-temporal store (`--as-of` in M2 could never return the old
   state).
   *Blocked by:* step 2 asserts that after `supersede()`, the OLD Concept still
   `get()`s (history preserved) AND its `valid_to` is CLOSED at `as_of` (not
   NULL, not deleted), AND the new fact's `supersedes` points at the old id and
   its `valid_from` equals `as_of`. A delete-based impl fails the "old fact still
   exists" assertion.

3. **Happy-path only (assumes both bounds always present).** A dev wires the
   table assuming every fact has both `valid_from` and `valid_to`, and crashes or
   mis-stores a one-sided / open window.
   *Blocked by:* step 1 includes a partial window (`valid_from` only) and asserts
   `valid_to` persists as NULL; step 3 asserts `update()` can both set and then
   fully clear the bounds (removing the row); a both-bounds-required impl fails
   on the partial fact.

## Strongest-pattern check
Features dimension → drive the real entry points end-to-end. This suite calls
`SecondBrain.add` / `.update` / `.supersede` / `.validity` and
`bundle.export` / `bundle.rebuild` on a real SQLite file + Bundle on disk —
never a mock, never an internal helper. It asserts the bi-temporal INVARIANT
(history preserved on contradiction) that a senior Zep engineer would treat as
the acceptance bar for temporal storage, and exercises the FK cascade that
proves `validity` is a real related table, not a metadata blob. (The `--as-of`
point-in-time RECALL bar is M2's verifier `temporal-asof`, intentionally out of
M1's scope.)
