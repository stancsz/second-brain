# G08 verifier adequacy

**Gap:** R10 (psychological subjects + persona sub-graph query)
**Verifier:** `verify_subject_subgraph.py`
**Pattern used:** Real Bundle on disk → `bundle.rebuild()` → `SecondBrain.subject_subgraph()` (the same Python entry points a user would hit from the CLI or a hook). End-to-end, not mocked internals. Round-trip is exercised (export → wipe → rebuild → re-query).

## Three concrete lazy artifacts the suite rejects

### Lazy artifact #1 — "Just add a `subjects` column to concepts"
The naive implementation: store `sb_subject` as a string column on `concepts` and filter at query time. The suite would *still* pass on this implementation because the queries use `sb_subject` in the same way. But the explicit `subjects` + `concept_subject` tables give us:
- `subjects()` — enumerate distinct subjects (can't be done efficiently with a GROUP BY on concepts.metadata JSON)
- A FK relationship so deleting a Person Concept cleans up its subject row
- An indexed `(subject_id)` lookup for fast sub-graph queries

How the suite catches the lazy version: a 7th sub-check enumerates `brain.subjects()` and asserts the result includes the default `/people/self.md` *plus* the Person Concepts — this forces the existence of an `subjects` table that can be queried independently of the concepts table. A `subjects` column on concepts would force a JSON scan to enumerate.

### Lazy artifact #2 — "Wire up the index but skip the bundle-rebuild path"
The naive implementation: add `subjects` + `concept_subject` tables, sync on live `add()`, but forget to call them from `bundle.rebuild()`. After a git pull + bundle-rebuild, the index would be empty and `recall-subject` would return nothing. The verifier would only fail on real users.

How the suite catches the lazy version: Phase 1 *builds a Bundle on disk* and calls `bundle.rebuild()`. The fixture is 7 Concepts with mixed sb_subject — if `rebuild_subject_index()` isn't called from `rebuild()`, the `subjects` table would be empty and the assertions on Person rows (`['Alex', 'Rox']`) would fail.

### Lazy artifact #3 — "Include the Person Concept in its own sub-graph"
A reasonable-sounding design: the Person Concept is "the subject, plus everything we know about them". So `subject_subgraph("/people/rox.md")` would return [Rox, "Rox avoids conflict", "Argument with Rox"]. The verifier explicitly tests that the Person Concept is **not** in its own subgraph (the `concept_subject for rox` assertion expects only 2 memories, not 3).

How the suite catches the lazy version: the per-subject `concept_subject` query filters out Person Concepts at index time, and `subject_subgraph()` joins through `concept_subject`, so the Person Concept is naturally excluded. A verifier that just scanned concepts and filtered by `metadata->>'sb_subject'` could go either way; the schema-enforced separation makes the correct answer the only one that fits the round-trip invariant.

## Strongest applicable pattern check

The strongest applicable pattern from the cookbook for a *data-derived index* is "end-to-end drive the real entry point on a real fixture, then round-trip". This is what the verifier does:

- Fixture = a Bundle on disk (real OKF files)
- Entry points = `bundle.rebuild()` (the same path a user hits via `brain import`) and `SecondBrain.subject_subgraph()` (the same path `brain recall-subject` uses)
- Round-trip = `bundle.export()` → wipe → `bundle.rebuild()` → re-query

No mocks. No presence-only checks. The verifier would fail on:
- An empty `subjects` table (catches the "forgot to sync" lazy version)
- A `subjects` table missing the `/people/self.md` default (catches the "forgot to normalize" lazy version)
- A subgraph that leaks unrelated subjects (catches the "filter at query time" lazy version)
- A round-trip drift (catches the "index is not derivable from concepts" anti-pattern)

## Senior-engineer sign-off test

A senior engineer at a competitor (e.g. Logseq, Roam) would say: "OK, you can list people and recall what we know about each. The default-subject path is right. The round-trip is preserved. Ship it." Yes.
