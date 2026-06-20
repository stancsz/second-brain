# second-brain — one-page handout

> Drop this in a Discord, a conference Slack, a comparison thread, or print it.
> Every claim is sourced in `growth/BRIEF.md`.

## Own your agent's memory. Don't rent it.

**second-brain** is a local, file-based knowledge graph for AI agents. One SQLite file
over plain markdown, synced through your own git. Zero dependencies, zero accounts,
zero monthly cliff. MIT-licensed.

### Why it exists
Every "AI memory" service sells you back your own memory behind an API and a pricing
tier — and can change the terms or get acquired. second-brain is the opposite bet:
**your memory is plain files in your home directory, versioned in your git.** No vendor
to migrate from.

### What you get
- 🗂️ **Files are truth** — OKF v0.1 markdown; SQLite is a rebuildable cache.
- 🔁 **Sync = git** — multi-device via a git remote; works offline.
- 🧠 **Psychological memory** — subjects, **bi-temporal validity** (point-in-time recall:
  *what did I believe on this date?*), structured **affect**, **supersession**.
- 🔒 **Selective encryption** — private memories are ciphertext on the remote; public
  notes stay diffable.
- 🤖 **Drop-in agent skill** — install as a Claude Code skill; your agent gets memory in
  one conversation.

### vs. the rental services
| | Rented memory | second-brain |
|---|---|---|
| Graph memory | often a paid tier (e.g. $249/mo) | included, local, **$0** |
| Self-host | stand up Neo4j / managed cloud | **one SQLite file, stdlib only** |
| Your data | in a vendor's store | **markdown in your git** |
| Privacy | "privacy drift", varying compliance | you own + encrypt it |
| Lock-in | vendor / framework | none — OKF, readable in Obsidian |

*Honest note: retrieval is full-text today; optional semantic (vector) search is on the
roadmap as a zero-dep-preserving adapter. We don't quote benchmarks we can't reproduce
on your data.*

### Get it
```bash
git clone https://github.com/stancsz/second-brain.git
python scripts/brain_cli.py add "title" "content" --tags a,b
python scripts/brain_cli.py recall --as-of 2026-01-01 "query"
```
⭐ **github.com/stancsz/second-brain** · MIT
