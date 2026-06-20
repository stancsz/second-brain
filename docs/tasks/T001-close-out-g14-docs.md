---
id: T001
status: open
title: Claim and ship the built-but-uncommitted G14 docs
depends_on: []
governed_by: [D001]
oversight: standard
---

## Goal
The drawer→Concept documentation work that was **built in iter-7 but left uncommitted and unrecorded** is
formally shipped: corpus-verified, gated, committed, and reflected in mochu state (ledger, gaps, cooldown,
RELEASE R15). If the `docs-okf` verifier does **not** actually pass against the current working tree, do not
paper over it — re-open G14 cleanly and report why.

## Why / context
Ledger iter-7: *"docs-okf/G14 BUILD landed in parallel this iter (uncommitted README/SKILL diffs) but is not
claimed here."* The working tree carries `M README.md`, `M SKILL.md`, `M docs/README.md` (~95 lines).
`gaps.md` still lists G14 as **Active, score 6.0**. Built work sitting uncommitted is loss risk + state drift.
Governed by [D001]: this is the first half of the Phase-A close-out; T002 (the code rename) follows immediately.

## Interfaces & contracts
- Verify before claiming: `python scripts/run_corpus.py` must exit 0 (all 9 verifiers green, incl `docs-okf`).
- Gate before commit: `python scripts/ship_gate.py` must pass (secret scan, verifier immutability, corpus green).
- On green, the commit includes the G14 doc diffs (`README.md`, `SKILL.md`, `docs/README.md`; include
  `docs/07`/`docs/08` only if they are part of the G14 docs gap, not the architect-spine files).
- State updates: append a G14 `SHIPPED` line to `.mochu/ledger.md`; move G14 Active→Shipped in `.mochu/gaps.md`;
  add a G14 cooldown entry; tick `RELEASE` **R15** naming verifier `docs-okf`.
- Do **not** commit the architect-spine files (`docs/PROTOCOL.md`, `docs/brief.md`, `docs/board.md`,
  `docs/tasks/`, `docs/reports/`, `docs/decisions/`) as part of the G14 ship — they are a separate concern.

## Architect review findings (2026-06-19) — fix before claiming
The drawer→Concept rename is thorough and the prose is good. Two accuracy/coherence defects must be
fixed first (the green `docs-okf` verifier checks terminology *presence*, not *truthfulness*, so it
cannot catch these):
- **F1 — Psychological memory is overclaimed.** README "Features" and SKILL present subjects / temporal
  validity / affect / supersession as present, queryable capabilities ("enable emotion-aware recall,"
  "perspective-aware memory synthesis," "historical queries"). Per the ledger + gaps.md, **G08/G09/G10
  are unbuilt (Phase C).** Only lossless frontmatter *serialization* of `sb_*` exists today — there is no
  schema, no `--as-of`, no affect/subject query, no persona sub-graph. Reframe to the truth: the fields
  **persist losslessly today; recall/query/synthesis lands in Phase C.** Do not claim queryable behavior.
- **F2 — Backup section contradicts the new sync model.** "Backup strategy" still says *"put
  `~/.secondbrain/brain.db` under version control… even at 50K Concepts under 100 MB"* — versioning the
  binary SQLite cache, which contradicts the new Features claim that the **Bundle is source of truth and
  git syncs the Bundle**. Reconcile: Bundle+git is the multi-device model; the single binary-DB-in-git is
  legacy/optional — don't present two conflicting git stories.
- **F3 (minor) — dangling link.** `docs/README.md` now links `07-pmf-and-gap-analysis.md`, which is
  untracked. If that link ships, commit `07` (and `08`) too, or the link dangles.

## Acceptance criteria
- [ ] **F1 fixed:** psychological-memory copy marks query/synthesis as Phase C; no present-tense claim of
      emotion-aware recall / persona sub-graphs / historical queries
- [ ] **F2 fixed:** Backup strategy reconciled with Bundle-as-source-of-truth + git sync (no contradictory
      "commit brain.db to git" as the primary model)
- [ ] **F3 fixed:** any 07/08 doc links that ship are committed alongside
- [ ] `scripts/run_corpus.py` exits 0; report shows `docs-okf` green
- [ ] `scripts/ship_gate.py` passes
- [ ] G14 moved from Active to Shipped in `.mochu/gaps.md`
- [ ] `RELEASE` R15 ticked, naming verifier `docs-okf`
- [ ] `.mochu/ledger.md` has a G14 SHIPPED line; `.mochu/cooldown.md` has a G14 entry
- [ ] No uncommitted README/SKILL G14 doc diffs remain in the working tree

## Out of scope
- Any code/schema/CLI rename — that is T002 (G04).
- New doc sections for unshipped features (encryption, MCP server, cloud backends).
- Improving the `docs-okf` verifier itself.

## Reporting bar
Trusted: TL;DR + Evidence (the `run_corpus.py` and `ship_gate.py` commands with their exit/summary lines) +
one line confirming the working tree has no leftover G14 doc diffs. If the corpus is red, switch to a
`blocked` report instead of shipping.
