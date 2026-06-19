# Competitors — last recon: 2026-06-18 (bootstrap)

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
