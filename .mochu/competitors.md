# Competitors — last recon: 2026-06-20 (iter-16 refresh)

The space splits into two domains SecondBrain straddles: **agent memory layers** and **human PKM /
note tools**. SecondBrain's wedge is the crossover (markdown-as-substrate that both human and agent use).

## Agent memory layers
| Name | URL | What they have / do better | Delta vs us |
|---|---|---|---|
| Mem0 | github.com/mem0ai/mem0 | ~48k stars; multi-store (vector+graph+KV); updates existing memory on correction instead of duplicating; user/session/agent scopes | We lack adaptive preference-consolidation; no multi-scope memory model |
| Zep / Graphiti | getzep.com / github.com/getzep/graphiti | Temporal knowledge graph: facts as nodes with validity windows; contradiction invalidates old without discarding history; strong governance | **Our planned temporal-validity layer targets exactly this** — not yet built |
| Letta (MemGPT) | letta.com | OS-style self-hosted control of the memory-management loop | We don't expose memory-loop control |
| supermemory | supermemory.ai | MCP server + Claude Code/OpenCode plugins; purpose-fit for coding-agent memory | We're skill-native already, but they have a polished MCP story |

## Human PKM / note tools
| Name | URL | What they have / do better | Delta vs us |
|---|---|---|---|
| Obsidian | obsidian.md | Plain-markdown local-first; deepest plugin ecosystem; mature mobile; git-syncable vault | **Our OKF-markdown plan makes us Obsidian-readable** — but they have UI, mobile, plugins we won't |
| Logseq | logseq.com | Open-source outliner; block references | Mid-transition off markdown to a DB format (portability risk for them = our opportunity) |
| Notion | notion.so | Team collab, visual databases | Proprietary cloud format = our portability pitch wins for individuals |

## Standards / formats
| Name | URL | Note |
|---|---|---|
| Google OKF v0.1 | github.com/GoogleCloudPlatform/knowledge-catalog/okf | The format we adopt natively. Markdown + YAML frontmatter; required `type`; links untyped. Reference enrichment agent + HTML graph visualizer exist. |

## Recon notes
- OKF (released 2026-06-12) legitimizes "specified markdown wiki" as the interop substrate — directly
  validates our direction and gives us a free interop story (Knowledge Catalog can ingest our Bundle).
- The genuinely-hard-to-roll capabilities flagged by research: Mem0's preference-consolidation and
  Zep's temporal reasoning. Our roadmap claims the temporal one; consolidation is a future gap.

## Recon — 2026-06-19 (iter-8)

Sources fetched (last 30 days of each): Mem0 releases, Zep/Graphiti releases, Letta releases,
supermemory releases, OKF SPEC.md (raw). WebSearch backend was returning 400s during this iter;
WebFetch was used instead.

### Deltas since 2026-06-18

**Mem0 — last 30 days**
- **OpenCode Plugin v0.2.0 (2026-06-17)**: dropped the MCP server; uses native OpenCode tools backed by
  `mem0ai`. Per-call `scope` (`project` / `session` / `global`) with persistent default + safety
  carve-out for `delete_all_memories`. **Gated auto-dream consolidation** (time/session/memory gates,
  filesystem lock) — this is the preference-consolidation we have on the backlog as **G18**.
- **Vercel AI SDK Provider v3.0.0 (2026-06-10)**: removes client-side graph memory; graph is now a
  Platform-only project setting. **Implication: a local-first graph store (us) is differentiated**
  — Mem0 users on the free/OSS tier lose the graph and must pay for Platform, or self-host elsewhere.
- Python SDK v2.0.7 / Node SDK v3.0.9 (2026-06-17): bug-fix releases; no new public surface.
- Mem0 Graph: no new commits in the 30-day window.

**Zep / Graphiti — last 30 days**
- **v0.29.2 (2026-06-08)**: bi-temporal + sagas + communities + filters + triplets at MCP core-parity.
  FalkorDB hardening; Kuzu deprecation. **Direct impact on G09** — bi-temporal is the bar.
- v0.29.1 (2026-05-21): episode-time watermarks distinguishing event-time vs wall-clock
  (`last_summarized_episode_valid_at` separate from wall-clock) — fine-grained temporal reasoning
  beyond what we spec'd in G09.
- v0.29.0 (2026-04-27): combined node+edge extraction, decoupled timestamp resolution,
  `summarize_saga` API + `SagaNode` + `fact_triple` episode type + `episode_metadata` filtering.
  **SagaNode is a new concept: episodic narrative on top of the temporal KG.** Worth tracking.
- **Migration note**: Kuzu users needed a one-time `ALTER TABLE RelatesToNode_ ADD reference_time
  TIMESTAMP` after v0.29.0. **Implication for G09**: any temporal-validity schema must be designed to
  migrate forward without breaking rebuild (our `sb_valid_from/to` columns must be added
  back-compatibly — see G17 round-trip note).

**Letta — last 30 days**
- v0.16.8 (2026-05-14): security fix replacing pickle with JSON for sandbox→server tool result
  transport. No new memory surface.
- v0.16.7 (2026-03-31, outside window): context window 32k→128k default, block-limit removal,
  memfs/git memory changes — still relevant background but stale.

**supermemory — last 30 days**
- supermemory-server 0.0.3 (2026-06-13): thread bug fix. No public-surface change.
- 0.0.2 / 0.0.1 (2026-06-10): cancel flow with reason capture. Billing/admin only.
- Multiple Granola-docs PRs; no MCP or memory-layer changes. **Their MCP story is unchanged from our
  last recon — we remain the only "skill-native" agent memory in the file.**

**OKF v0.1 spec — re-fetched 2026-06-19**
- Still "Version 0.1 — Draft" with no published date.
- Confirmed rules: required `type` (non-empty), reserved filenames are `index.md` and `log.md` only
  (no separate `okf_version` file — that key lives in bundle-root `index.md` frontmatter).
- Consumers must tolerate: missing optional fields, unknown `type` values, unknown extra
  frontmatter keys, broken cross-links, missing `index.md`.
- **Action for next iter**: verify our `bundle.py` / G03 verifier place `okf_version` in
  `index.md` frontmatter (not as a separate file). If our docs/code drifted, this is a G03
  regression — log under G20.

### Strategic implications for our backlog

1. **G18 (preference-consolidation) just got a real-world reference implementation.** Mem0
   OpenCode v0.2.0 ships gated auto-dream in production. Bump confidence 2→3; effort is bounded
   because the spec is "time/session/memory gates + filesystem lock" — small surface.
2. **G09 (`--as-of` recall) is correctly aimed.** Zep v0.29.2 bi-temporal core-parity is the bar;
   our `sb_valid_from/to` + `sb_supersedes` design is simpler but covers the core case. No scope
   change needed; verify the migration-on-add story (G17).
3. **SagaNode-style episodic narrative is a future opportunity, not a current gap.** Stay aware;
   don't pull it in.
4. **Local-first graph is now a real differentiator** (post Mem0's graph-to-Platform move). Our
   OKF-as-truth story is the carrying argument; the docs need to make it explicit (G14/R15 work).
5. **OKF spec drift watch**: our G03 verifier needs to confirm `okf_version` placement. Log as G20.

## Recon — 2026-06-20 (iter-16)

WebFetch backend was erroring this iter (backing model "MiniMax-M2.7" unavailable);
WebSearch worked and was used instead. Calendar gap since last recon is only 1 day,
so most changelogs had not moved — the signal this iter is a **Mem0 architecture
shift** confirmed via their own 2026 blog/docs, plus reconfirmation of the Zep bar.

### Deltas since iter-8 (2026-06-19)

**Mem0 — graph store deprecated, replaced by entity-linking-for-ranking**
- Mem0 **removed the external graph store (Mem0g)** from the OSS algorithm. In its
  place: during `add()`, entities are extracted and stored in a parallel
  `{collection}_entities` collection; at search time, query entities are matched
  and **boost** the combined score. **This is NOT a queryable graph traversal API**
  — relationships are used indirectly for ranking only.
- Retrieval is now **three-signal fusion**: semantic similarity + BM25 keyword +
  entity-match, normalized and fused into one score.
- (Graph traversal is still possible only by bolting on an external store, e.g.
  Amazon Neptune Analytics — i.e. pay/self-host, not in the core.)
- Sources: [Mem0 State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026),
  [Mem0 Graph Memory docs](https://docs.mem0.ai/platform/features/graph-memory).

**Zep / Graphiti — no new release surfaced; bar unchanged**
- No release newer than v0.29.2 (iter-8) found. Bi-temporal model reconfirmed:
  per-fact **validity windows** (valid-from / valid-to), contradiction **closes**
  the old window rather than deleting (history stays queryable), point-in-time
  queries, and **provenance** (every fact traces to its source episode).
- Source: [getzep/graphiti](https://github.com/getzep/graphiti),
  [Zep temporal knowledge graph](https://www.getzep.com/ai-agents/temporal-knowledge-graph/).

### Strategic implications for our backlog

1. **Our queryable graph is now MORE differentiated, not less.** Mem0 — the
   category leader — just retreated from graph-as-API to entity-boost-for-ranking.
   SecondBrain keeps a real, local, queryable relation graph (`relations`,
   `traverse`, subject sub-graphs G08, affect queries G10). The OKF-as-truth +
   queryable-graph story is the wedge; docs should say so (R15/G14 already does
   the foundation, but the "vs Mem0's 2026 entity-linking retreat" framing is new).
2. **Multi-signal retrieval is the emerging bar, and we only have one signal at
   rank time.** `brain search` is FTS5 (BM25-class keyword) only; the wikilink
   relation graph exists but does NOT influence search ranking, and there is no
   semantic layer. Mem0 fuses three signals. **New gap G25**: graph-aware search
   boost — re-rank FTS hits by relation-graph proximity to other hits / to a
   seed. This is achievable **dependency-free** (pure graph traversal over
   `relations`, no embeddings), unlike a semantic-embedding signal (which would
   break the stdlib-only core and belongs behind an optional adapter if ever).
3. **G09 (`--as-of` recall) remains the highest-value release-linked gap.** Zep's
   bi-temporal bar is unchanged; our `sb_valid_from/to` + `sb_supersedes` design
   covers the core point-in-time case. Next non-recon iter should target it.
4. **Provenance**: Zep traces every fact to its source episode; we have per-Concept
   `sources` (URLs) but not "which conversation/episode produced this Concept."
   Minor; not a gap yet — note for when Episode types mature.

## Recon cadence
- Bootstrap: 2026-06-18
- Refresh 1: 2026-06-19 (iter-8)
- Refresh 2: 2026-06-20 (iter-16)
- Next: iter-24 or when 30+ days stale, whichever is sooner.
