---
title: second-brain — own your agent's memory
description: A local, file-based knowledge graph for AI agents. One SQLite file, zero dependencies, full data ownership. The own-it alternative to rented AI-memory infra.
---

# Stop renting your agent's memory.

**second-brain** is a local, file-based knowledge graph for AI agents — one SQLite file
over plain markdown, synced through *your* git, with a psychological-memory layer the
rental services don't have. Zero dependencies. Zero accounts. Zero monthly cliff.

> You're not building a second brain. You're *renting* one. The export becomes a Pro
> feature, the API terms tighten, the company gets acquired. second-brain bets on the
> other side: one file, in your home directory, versioned in your git. No migration
> plan — because there's no vendor to migrate from.

[⭐ Star on GitHub](https://github.com/stancsz/second-brain) ·
[Quickstart](#quickstart) · [How it compares](#how-it-compares) · [中文](https://github.com/stancsz/second-brain/blob/main/README.zh.md)

---

## The table-flip (掀桌子)

The AI-agent-memory category sells you back *your own memory* — behind an API, a pricing
cliff, and a vendor that can change the terms. Developers already know the escape hatch:
keep your knowledge as markdown in a versioned folder. **second-brain is that escape
hatch, finished and free** — and it adds the memory the rental services *don't* ship.

| What hurts with rented memory | second-brain |
|---|---|
| Graph memory gated behind a **$249/mo** tier; advanced features cloud-only | Graph **+ psychological layer**, fully local, **$0**, no tiers |
| Self-hosting means standing up **Neo4j** (Zep's free tier was deprecated) | **One SQLite file**, Python stdlib only — no Neo4j, no Docker, no `pip install` |
| **"Privacy drift"** — memory runs deeper than you expect, no veto | You own the files. **Selective encryption** for private memories; **bi-temporal** correction instead of silent edits |
| **Vendor & framework lock-in** | **OKF v0.1 markdown in your git** — readable in Obsidian if we vanished tomorrow |
| Disputed vendor benchmarks | Your data is files you can read and `grep` — verify recall yourself |

---

## What makes it different

- **Files are truth.** Every memory is an [OKF v0.1](https://github.com/stancsz/second-brain/blob/main/docs/02-okf-and-terminology.md)
  markdown file with YAML frontmatter. SQLite is a disposable, rebuildable cache. Delete
  the database and rebuild it from the files, losing nothing.
- **Sync is just git.** Multi-device sync rides a git remote — the same merge, history,
  and conflict tools you already trust. Works fully offline.
- **A real psychological-memory layer** (no competitor ships this combination):
  - **Subjects** — who or what a memory is about (people, projects, personas).
  - **Bi-temporal validity** — when a fact was true; ask *"what did I believe on this
    date?"* with point-in-time recall. Contradictions close the old window instead of
    deleting history.
  - **Structured affect** — valence / arousal / emotion / intensity, queryable.
  - **Selective encryption** — private/psychological memories are ciphertext on the
    remote; public notes stay diffable.
- **Drop-in for agents.** Ships as a [Claude Code skill](https://github.com/stancsz/second-brain/blob/main/SKILL.md);
  any agent that loads it can save, search, and link memories mid-conversation.

---

## Quickstart

```bash
git clone https://github.com/stancsz/second-brain.git
cd second-brain

# capture, search, recall — stdlib only, no install step
python scripts/brain_cli.py add "Decided on SQLite over Postgres" \
  "Local-first, zero-dep, rebuildable from files" --tags decision,architecture
python scripts/brain_cli.py search "database choice"
python scripts/brain_cli.py recall --as-of 2026-01-01 "database"   # point-in-time

# multi-device: your memory syncs through your own git remote
python scripts/sync.py ~/.secondbrain/okf <your-git-remote>
```

Install it as a Claude Code skill and your agent gets memory in one conversation. See
the [README](https://github.com/stancsz/second-brain/blob/main/README.md).

---

## How it compares

second-brain is **local-first by design** — not a managed cloud. If you want someone
else to host and operate your memory, a managed service is the trade. If you want to
**own** it — plain files, your git, no vendor, no cliff, and a psychological layer none
of them ship — that's the table we're flipping.

> **Honest status:** today's retrieval is full-text (keyword) search; optional semantic
> (vector) search is on the roadmap as a lazy adapter that won't break the
> zero-dependency core. We lead with ownership, privacy, cost, and the psych layer —
> and we don't quote benchmarks we can't reproduce on your data.

[Read the architecture](https://github.com/stancsz/second-brain/blob/main/references/architecture.md) ·
[⭐ Star on GitHub](https://github.com/stancsz/second-brain)

---

<sub>Open source (MIT). Your knowledge is your intellectual history — it belongs to you,
not to a platform. second-brain keeps it that way.</sub>
