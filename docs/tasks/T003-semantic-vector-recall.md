---
id: T003
status: blocked
title: Semantic / vector recall as an optional layer over FTS5 (G20)
depends_on: [T002]
governed_by: [D002]
oversight: proposal-first
---

## Goal
Recall returns Concepts that match by **meaning**, not just keyword — closing the market's #1 Critical gap
(docs/07 Gap 1). Keyword FTS5 stays the zero-dependency default; semantic search is an opt-in layer on top.
RELEASE **R16** ticks.

## Why / context
docs/07 rates semantic recall "Critical… standard across all competitor memory stacks," yet it was absent
from the register and from RELEASE — the single biggest divergence between our finish line and the market.
Per [D002] it is elevated to near-term (highest score, 6.67) and sequenced after the Phase-A close-out and
before Phase C, because good retrieval is the substrate that makes psychological Concepts findable.

## Interfaces & contracts (hard invariants from D002)
- **Embeddings are cache-only.** Store vectors in the SQLite cache, derived from Concept text; regenerate on
  `rebuild`. **Never** write embeddings into OKF markdown files (breaks "files are truth," bloats git).
- **Optional, lazy-loaded.** `sqlite-vec` (or equivalent) + a small local embedding model
  (e.g. `all-MiniLM-L6-v2`) are lazy-imported. When the extension/model is absent, recall **degrades
  gracefully to FTS5** — the zero-dependency / air-gap guarantee must hold.
- **Hybrid recall surface.** The recall path returns FTS5 + semantic results; specify the merge/ranking
  contract in the proposal (this is a design fork — see oversight).
- Do not change the OKF on-disk format, `sb_*` fields, or the `type` vocabulary.

## Acceptance criteria
- [ ] A query with no keyword overlap but matching meaning (the docs/07 example: "optimizing code" ↔
      "performance tuning") returns the related Concept
- [ ] With the extension/model unavailable, recall still works via FTS5 (graceful degradation), proven
- [ ] `rebuild` reconstructs embeddings from files; no vectors appear in any OKF markdown file
- [ ] New verifier `semantic-recall` red→green, registered; full corpus green; `ship_gate` passes
- [ ] RELEASE R16 added + ticked; ledger/gaps/cooldown updated for G20

## Out of scope
- Automated entity/relationship extraction (G21) and the agent-facing MCP server (G22) — separate tail gaps.
- Cloud-hosted embedding APIs (violates zero-cloud / air-gap).

## Reporting bar
**proposal-first** (novel + a binary dependency + a retrieval-quality fork): submit a `proposal` report
first — pick the extension/model, define the hybrid FTS5+vector merge/ranking contract, state where
embeddings live and how degradation is detected, and weigh footprint vs. the zero-dependency principle.
Get a ruling before writing code.
