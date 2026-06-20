## Vision
SecondBrain is a **local-first, agent-legible, OKF-conformant knowledge graph the user owns** — plain
markdown files versioned in git, portable across devices, and purpose-built for AI memory *synthesis*
(subjects, temporal validity, structured affect). Market position (docs/07): the only stack that is
**Local-First + Agent-Native + Standard-Compliant** at once. The differentiator vs cloud memory stacks
(Mem0, Zep, LangMem) is **psychological memory on owned files with zero cloud dependency** — but the
product must also clear **table-stakes recall** (semantic search) to not look toy beside competitors.
Finish line: all RELEASE criteria green (now /16 after the market reconciliation, D002).

## Strategy (differentiation vs parity — D002)
Pursue **differentiation first; parity only where a feature is table-stakes AND architecture-compatible.**
- Psychological memory (Phase C) is the north star — no competitor has it. It stays the priority.
- Semantic/vector recall is the one parity feature elevated to near-term: table-stakes, architecture-fit
  (local `sqlite-vec`, lazy-loaded), and the retrieval substrate that makes psych Concepts findable.
- Auto entity-extraction + agent-facing MCP/SDK are parity-niceties → tail.
- Market gaps already covered: git sync (G05/06/07, shipped) · encryption (G13).

## Current state — 2026-06-19 (end of iter-7)
- **Shipped (7 iters):** G01 OKF serializer · G02 bundle export/rebuild · G03 OKF reserved files ·
  G05 git sync spine · G07 tombstone deletes · G06 conflict parking · G19 recall-hook encoding fix.
- **RELEASE: 5/15** (R2, R3, R5, R6, R7). **Corpus: 9 verifiers green.**
- **LOOSE END (caught this turn):** G14 docs (drawer→Concept in README/SKILL) was **built in iter-7 but
  never claimed** — the ledger says "uncommitted README/SKILL diffs… not claimed here." Working tree has
  `M README.md`, `M SKILL.md`, `M docs/README.md` (~95 lines). `gaps.md` still lists G14 **Active, score
  6.0**. This is built work sitting uncommitted *and* a docs→code coherence gap (docs now say `Concept`,
  code still says `drawer`). Tracked by T001 + T002, governed by D001.
- **Architecture (locked):** files are truth; SQLite is a disposable rebuildable cache; git is the only
  bidirectional sync spine; clouds are one-way mirrors; `sb_*` psychological fields ride in OKF frontmatter.

## Principles (invariants the builder self-serves on)
- **Files are truth; SQLite is a rebuildable cache.** Never make SQLite authoritative.
- **Git is the only bidirectional spine;** cloud backends are strictly one-way mirrors.
- Every Concept persists as an **OKF v0.1 file**: YAML frontmatter with a non-empty `type`.
- **`sb_*` psychological fields are namespaced and ride in frontmatter** — they are NOT the model name;
  the drawer→Concept rename must never touch `sb_*` field names or the OKF on-disk `type` vocabulary.
- **Verifier-first, ratchet corpus:** red before green; the corpus only grows; every verifier stays green
  every iter. `ship_gate.py` (secret scan + verifier immutability + corpus green) must pass before any ship.
- **No new `drawer` identifiers in code** (post-D001). The canonical model term is `Concept`.
- **Conflict resolution stays dumb:** park `*.conflict.md`, never auto-merge content.
- **Embeddings are cache-only** (derived, rebuilt with SQLite) — never written into OKF files. **Semantic
  search is an optional lazy-loaded layer; FTS5 is the always-available zero-dependency default** (D002).
- One mochu gap per iteration; the ledger/gaps/cooldown/RELEASE state must move when a gap ships.

## Open arcs (resequenced by D001 + D002)
1. **Phase A close-out** — T001 claim+ship the built G14 docs (→ R15); T002 = G04 rename drawer→Concept in
   code (→ R4). After both, docs and code are coherent and Phase A is truly done.
2. **Real-data proof (moved up):** G17 migrate the user's actual v2.1 `brain.db` → OKF Bundle, *right after
   the rename* — validates G04's old-schema compat shim on real data while it's fresh; first round-trip on
   real data. De-risks the whole files-as-truth thesis early.
3. **Table-stakes recall** — T003 = **G20 semantic/vector recall** over FTS5 (→ R16). Market's #1 Critical
   gap; the retrieval substrate Phase C needs. Optional lazy layer; FTS5 stays the default.
4. **Phase C — psychological memory (the differentiator, north star):** G08 subjects + subject-subgraph
   (→ R10) · G09 temporal validity + `--as-of` (→ R11) · G10 structured affect (→ R12). Written natively
   in `Concept` vocabulary, landing on a semantic-retrieval substrate.
5. **Phase D trust/backends:** G13 selective encryption (→ R13) · G11 S3/GCS + G15 scheduler (→ R8, R9).
6. **Parity tail (D002):** G21 automated entity/relation extraction (market Gap 2, opt-in/agent-side) ·
   G22 agent-facing OKF MCP server + standalone CLI/lib (market Gap 4) · G12 GDrive/OneDrive ·
   G16 incremental rebuild perf · G18 preference consolidation · G19 FTS stemming enhancement.
