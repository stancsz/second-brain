# G10 adequacy — affect-persist suite (R12)

The bar R12 sets: structured affect **persists and is queryable per Concept**.
A passing suite must make "stored a JSON blob" insufficient — it must force a
real typed, queryable `affect` table. Three lazy artifacts that a weak suite
would accept, and how this suite blocks each:

1. **Schema-only (table exists, never populated).** A dev adds
   `CREATE TABLE affect (...)` to schema.sql, ships, and never writes the
   rebuild/add wiring that fills it. A suite that only checks
   `"affect" in sqlite_master` would pass.
   *Blocked by:* Phase 2 asserts the table holds *exactly the 5 affect-bearing
   rows with the right typed values* after `bundle.rebuild()` of a real Bundle,
   and that the affectless Concept has NO row. An empty or wrongly-populated
   table fails immediately.

2. **Metadata-blob only (no real query surface).** A dev leaves `sb_affect` in
   `concepts.metadata` (where it already round-trips), adds an `affect(id)`
   getter that just reads the blob, and calls it done. Per-Concept reads work;
   there is no typed table, so range/categorical queries across Concepts are
   impossible.
   *Blocked by:* Phase 4 requires `recall_by_affect(emotion=..., min_intensity=...,
   max_valence=..., min_valence=...)` to return the *exact* Concept set for
   categorical, range, and combined filters (a TEXT JSON blob cannot answer
   `WHERE intensity >= 0.7`); Phase 6 asserts an `ON DELETE CASCADE` FK from
   `affect.concept_id` to `concepts.id`, which only exists if affect is a real
   related table; Phase 8 drives the `brain recall-affect` CLI via subprocess.

3. **Happy-path only (assumes all 4 dims always present).** A dev wires the
   table assuming every `sb_affect` has valence/arousal/emotion/intensity, and
   either crashes or stores 0 for a partial/absent affect.
   *Blocked by:* the fixture includes `e-005` (emotion-only affect) and `n-006`
   (no affect). Phase 3 asserts `affect(partial)` returns the emotion with
   numeric dims = **None** (not 0, not crash), `affect(affectless)` returns
   None, and Phase 4 asserts the NULL-intensity partial row does NOT leak into a
   `min_intensity=0.0` numeric query. A happy-path build fails on the partial row.

## Strongest-pattern check
Features dimension → drive the real entry point end-to-end. This suite calls
`bundle.rebuild` / `bundle.export` / `SecondBrain.add` / `.update` / `.affect` /
`.recall_by_affect` on a real Bundle and a real SQLite file on disk, and drives
the `brain recall-affect` CLI through a subprocess — never a mock, never an
internal helper. It exercises all three ways affect enters the store: OKF
round-trip (export → wipe → rebuild), live CRUD, and the CLI. A senior engineer
at Zep/Mem0 would accept "affect is queryable" only if shown exactly these range
queries returning exact sets — which is what Phase 4 does.
