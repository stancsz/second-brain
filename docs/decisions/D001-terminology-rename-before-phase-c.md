---
id: D001
status: ruled
raised_by: architect-bootstrap
governs: [T001, T002]
supersedes: null
---

# D001 — Rename drawer→Concept (G04) lands before Phase C, not after

## Context
G14 renamed `drawer`→`Concept` in the **docs** (README/SKILL) — built in iter-7, currently uncommitted.
The **code/schema/CLI** still say `drawer`/`drawers`. Phase C (G08 subjects, G09 temporal validity,
G10 affect) is the next major arc and adds the single largest block of new model-referencing code/tables
on the roadmap. The order in which we rename vs. build Phase C is load-bearing because it changes how much
code a later rename has to chase.

## Options
- **A) Phase C first, rename later.** Ship the differentiator sooner. Cost: every new psych table/field is
  written against `drawers`; a later G04 must chase the rename through all of C's new code — a strictly
  larger, riskier rename. Docs and code stay incoherent longer (README says `Concept`, CLI says `drawer`).
- **B) Rename (G04) before Phase C.** Cost: one extra iteration before the differentiator. Benefit: C is
  written natively in canonical OKF vocabulary; docs match code; R4 ticks; Phase A truly closes.
- **C) Migrate real brain.db (G17) first.** Cost: migrates real user data into a still-`drawer`-named
  bundle, so the rename later re-touches migrated data and its migration path.

## Recommendation
B.

## Ruling
**B — rename-first.** Adopted. The cost of a rename grows monotonically with the amount of code that
references the old name. Phase C is the largest single addition of model-referencing code we have planned,
so renaming *after* C is strictly more expensive and more error-prone than renaming *before*. Rename-first
also closes the docs→code coherence gap that shipping G14 opens: a stranger who follows the freshly-updated
README and then runs the CLI must not meet a `drawer` they were never told about.

## Consequence
- Sequence is fixed: **T001 (claim/ship G14 docs) → T002 (G04 code rename) → Phase C (G08→G09→G10) →
  G17 → Phase D.** No Phase C or G17 task starts before T002 is `done`.
- All Phase C tasks inherit canonical vocabulary: new tables are `concepts`-relative; **`sb_*` frontmatter
  field names and the OKF `type` vocabulary are NOT renamed** (they are namespaced extension fields, not the
  model name).
- The transient committed state where docs say `Concept` while code still says `drawer` (between T001 and
  T002) is **accepted but must be closed in the very next iteration** — T002 is not deferrable.
- Going forward, introducing a new `drawer`/`drawers` identifier in code is a violation the architect rejects.
