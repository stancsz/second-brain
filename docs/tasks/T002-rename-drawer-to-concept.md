---
id: T002
status: blocked
title: Rename drawer→Concept across schema, CLI, and code (G04)
depends_on: [T001]
governed_by: [D001]
oversight: standard
---

## Goal
The model is OKF-canonical — `Concept`/`concepts` — across the SQLite schema, the CLI surface, all help text
and command output, and every internal Python reference. No `drawer`/`drawers` identifier remains in code or
in anything a user sees. RELEASE **R4** ticks.

## Why / context
After T001, the docs say `Concept` while the code still says `drawer` — a stranger following the README hits a
mismatch. Closing this is the second half of the Phase-A close-out. Per [D001], it also must land *before*
Phase C so the psychological-memory tables are written natively in `Concept` vocabulary rather than chased
through a later rename.

## Interfaces & contracts
- **New verifier `terminology-rename`** (RELEASE R4). Author it **red before green** (mochu discipline) and add
  it to `.mochu/verifiers/REGISTRY.md`. It must assert: (a) no `drawer`/`drawers` identifiers in `scripts/*.py`
  outside unavoidable migration strings/comments; (b) CLI help and command output say "Concept"; (c) the CLI
  accepts the renamed surface.
- **Data-compatibility is load-bearing:** an existing `brain.db` with a `drawers` table must still open after
  the rename (G17 will migrate the user's real DB, so the path cannot be broken). Provide a table-rename
  migration or a read compatibility shim, and cover it with the verifier.
- **Do not touch:** `sb_*` frontmatter field names, the OKF on-disk `type` vocabulary, or the Bundle file
  layout. These are namespaced extension fields, not the model name (see brief Principles + [D001]).

## Decision fork to watch
If the DB-compatibility path is non-trivial (e.g. silent in-place migration vs. explicit `migrate` command,
or how to detect an old-schema DB), **do not guess** — open `D003`, set the report `needs-decision`, and stop.
That fork affects G17 and is the architect's call.

## Acceptance criteria
- [ ] No `drawer`/`drawers` code identifiers remain in `scripts/` (migration strings/comments excepted)
- [ ] CLI help + command output use "Concept"
- [ ] `terminology-rename` verifier goes red→green and is registered in the corpus
- [ ] An existing `drawers`-schema `brain.db` still opens (migration or shim), covered by the verifier
- [ ] Full corpus green; `ship_gate.py` passes; RELEASE R4 ticked; ledger/gaps/cooldown updated for G04

## Out of scope
- Psychological tables/fields (Phase C: G08/G09/G10).
- Renaming `sb_*` fields or the OKF `type` vocabulary.
- The real-brain.db migration itself (G17) — only the *compatibility* that keeps G17 possible.

## Reporting bar
Standard: TL;DR + Structure map (changed symbols + any new dependency edges) + Evidence (verifier red→green
proof, full corpus exit-0, ship_gate pass) + Risks. If you opened D002, report `needs-decision` and stop.
