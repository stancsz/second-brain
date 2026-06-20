# Board — status by exception

> **Manual bootstrap snapshot** (no `scripts/board.py` generator exists yet — a small Phase-E add-on).
> Regenerate from front-matter once that lands. Architect reads this first; drill only into exceptions.

_Generated-equivalent: 2026-06-19, end of iter-7._

## Needs architect
- _(none open — D001/D002 ruled)_

## Review findings (architect, 2026-06-19)
- **T001/G14 — do not ship as-is.** 2 defects the green `docs-okf` verifier can't catch:
  **F1** psychological memory overclaimed (subjects/temporal/affect presented as queryable; G08–G10 unbuilt) ·
  **F2** Backup section still says "commit brain.db to git," contradicting Bundle-as-source-of-truth.
  Fixes folded into T001 acceptance criteria; oversight raised trusted→standard.

## Open / in flight
| Task | Status | Oversight | Gap | Depends | Governed | Note |
|---|---|---|---|---|---|---|
| T001 | open | trusted | G14 | — | D001 | Claim+ship the uncommitted G14 docs; tick R15 |
| T002 | blocked | standard | G04 | T001 | D001 | drawer→Concept code rename; tick R4; may raise D003 |
| T003 | blocked | proposal-first | G20 | T002 | D002 | Semantic/vector recall over FTS5; tick R16; proposal first |

## Decisions
| ID | Status | Governs | Title |
|---|---|---|---|
| D001 | ruled | T001, T002 | Rename drawer→Concept (G04) before Phase C |
| D002 | ruled | T003 | Market-gap reconciliation — semantic recall elevated; differentiation-first |

## Next arcs (not yet ticketed)
Phase C — G08 subjects (R10) → G09 temporal `--as-of` (R11) → G10 affect (R12); then G17 real-DB migration;
then G13 encryption; then parity tail G21 (auto-extract) / G22 (MCP). Ticketed as the loop advances.

## Register additions recommended (D002 — awaiting builder/gaps.md)
G20 semantic recall (score 6.67, top of register) · G21 auto entity/relation extract (3.0) ·
G22 agent-facing MCP/SDK (2.25). RELEASE gains R16 (semantic recall), bar moves /15 → /16.

## RELEASE pulse
5/16 (R2, R3, R5, R6, R7). T001 → R15 · T002 → R4 · T003 → R16 · Phase C → R10/R11/R12.
