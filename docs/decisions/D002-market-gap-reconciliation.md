---
id: D002
status: ruled
raised_by: architect-bootstrap
governs: [T003]
supersedes: null
---

# D002 — Reconcile the market/PMF gap analysis with the internal roadmap

## Context
The internal gap register (G01–G19) and the 15 RELEASE criteria were seeded from the *build plan*
(docs/06, Phases A–E) — an inside-out, portability-and-psychology view. The PMF/competitor analysis
(docs/07) is an outside-in, market view. Cross-checking them surfaces a divergence the architect must
resolve, because the finish line (RELEASE.md) currently does not match the market the product competes in.

Mapping docs/07's five market gaps onto the register:
- **Gap 1 — Semantic/vector recall (Critical):** *absent from the register and from RELEASE entirely.*
  docs/07: "Semantic recall is standard across all competitor memory stacks." Scored in our frame
  (impact 5 × confidence 4 / effort 3) = **6.67 — the highest score in the register.**
- **Gap 2 — Automated entity/relationship extraction (High):** only loosely touched by G18 (score 1.5).
- **Gap 3 — Bidirectional git sync (High):** **shipped** (G05/G06/G07). No action.
- **Gap 4 — SDK / agent-facing MCP interop (Medium):** G12 is *backup* (GDrive/OneDrive), not an
  agent-facing OKF MCP server / standalone library. Under-represented.
- **Gap 5 — Selective encryption (Medium-Low):** covered by G13. No action.

## Options
- **A) Ignore the market view, follow the build plan as-is.** Keeps focus on the differentiator, but ships
  a product whose recall is keyword-only — looks toy next to Mem0/Zep, and RELEASE "production-ready" is a
  finish line the market wouldn't accept.
- **B) Chase parity — semantic search + auto-extraction + MCP first, psychology later.** Matches competitors
  fast, but dilutes the one thing no competitor has (psychological memory on owned files) and burns iters on
  catch-up before the differentiator lands.
- **C) Differentiation-first, with table-stakes parity folded in where it is architecture-compatible.**
  Register the missing market gaps; elevate *only* semantic search to near-term (it is table-stakes AND
  the retrieval substrate that makes psychological Concepts findable); keep psychology as the north star;
  push auto-extraction and MCP to the tail as parity-niceties.

## Recommendation
C.

## Ruling
**C.** Adopted, with this weighting principle made law: **we pursue differentiation first, and parity only
where a feature is both (a) genuine table-stakes and (b) compatible with the locked architecture.**
- **Semantic/vector recall passes both tests** — it is table-stakes (every competitor has it) and it fits
  the architecture (local, zero-cloud via `sqlite-vec` + a small local embedding model, lazy-imported). It
  is also the *retrieval substrate*: rich psychological Concepts (subjects, affect, temporal validity) are
  only valuable if you can actually surface them, and keyword FTS5 can't. So it is elevated to a near-term
  must and inserted right after the Phase-A close-out, **before** Phase C.
- **Psychological memory remains the north star** — it is the reason the product exists and the only axis
  with no competitor. Phase C (G08/G09/G10) lands immediately after semantic search, now on a strong
  retrieval substrate.
- **Auto-extraction (Gap 2) and agent-facing MCP/SDK (Gap 4) are parity-niceties** — registered, but tail
  priority after the differentiator and encryption. Auto-extraction also partially conflicts with the
  "dumb, deterministic, zero-dependency" ethos (it needs LLM calls), so it stays opt-in/agent-side.

## Consequence
- **Three gaps are added to the register** (recommend the builder add to `.mochu/gaps.md`):
  - **G20 — Semantic/vector recall** (`sqlite-vec` + small local embedding model; FTS5 hybrid). impact 5,
    effort 3, confidence 4 → **6.67**. Maps market Gap 1.
  - **G21 — Automated entity/relationship extraction during distillation** (LLM-assisted Concept/relation
    drafting; opt-in, agent-side). impact 4, effort 4, confidence 3 → 3.0. Maps market Gap 2.
  - **G22 — Agent-facing OKF MCP server / standalone CLI+library** (multi-framework interop). impact 3,
    effort 4, confidence 3 → 2.25. Maps market Gap 4.
- **RELEASE gains a criterion R16** (the finish line was incomplete): *"Semantic recall returns concepts
  matching by meaning, not just keyword; FTS5 remains the zero-dependency fallback — verifier:
  semantic-recall (G20)."* Bar moves from /15 to /16.
- **Architecture invariants locked for G20** (these bind any future builder):
  - **Embeddings are cache-only, never persisted to OKF files.** They are derived from Concept text and
    rebuilt with the SQLite cache — storing vectors in markdown would bloat git and break "files are truth."
  - **Semantic search is an optional, lazy-loaded layer.** `sqlite-vec` is a binary extension; FTS5 stays
    the always-available default. The product must degrade gracefully (keyword recall) when the extension
    or model is absent — preserving the zero-dependency / air-gap guarantee.
- **Post-Phase-A sequence (refines D001; G17 moved up 2026-06-19 after a well-reasoned mochu-agent
  dissent):** T001 (G14) → T002 (G04) → **G17 real-DB migration** — validates G04's old-schema compat
  shim on the user's *real* `brain.db` while it's fresh (this is exactly the D003 fork T002 flags; de-risks
  the files-as-truth thesis on real data early) → **T003 (G20 semantic)** → Phase C (G08→G09→G10) →
  G13 encryption → G21/G22 → cloud backends (G11/G15/G12) → tail (G16/G18/G19-stemming).
