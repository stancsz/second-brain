# second-brain

> **Own your psychological twin — don't rent it.** A local, file-based container that models a *real person* — their decisions, preferences, and the affect behind them, with bi-temporal validity and supersession — and an OKF v0.1-native knowledge graph that AI agents read and write natively. One SQLite file, zero dependencies, full data ownership, multi-device sync via git.
>
> [中文文档](./README.zh.md) · [Architecture](./references/architecture.md) · [SKILL.md](./SKILL.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org)
[![Dependencies: 0](https://img.shields.io/badge/dependencies-0-green.svg)](#installation)
[![OKF: v0.1](https://img.shields.io/badge/OKF-v0.1-brightgreen.svg)](./docs/02-okf-and-terminology.md)

---

> **The digital-mind platforms want to rent you back to yourself.** Delphi, Personal.ai, and the wave behind them will happily build an AI version of *you* — your voice, your decisions, your personality — and keep it on their servers, behind their API, on their pricing. Your psychological twin becomes a subscription. The day the terms change, the price jumps, or the company gets acquired, the model of who you are changes hands with it. That is the most personal data there will ever be, and the entire category is racing to host it for you.

> `second-brain` bets on the other side: **your twin is a folder of plain markdown in your own git.** Every memory of the person — what they decided, what they prefer, how they felt, and *when* each of those was true — lives in files you can read, diff, version, and carry forever. No vendor owns the model of you. There is no migration plan, because there is no one to migrate from. **Nobody else lets you own the psychological twin instead of renting it. That is the whole point.**

> **It is important to own your data and own your knowledge.** Your memory is your intellectual and emotional history — the decisions you made, the things you learned, the people you cared about, the way you changed. That record belongs to you, not to a platform. `second-brain` keeps it that way: plain files you can read, copy, version, and carry with you forever.

---

## What it is

`second-brain` is a personal knowledge store designed to be read and written by AI agents as easily as by humans. Concepts (notes) are persisted as an **OKF v0.1-conformant Bundle** — a directory of markdown files with YAML frontmatter — backed by a SQLite cache at `~/.secondbrain/brain.db`. Everything uses the Python standard library only — no `pip install`, no `docker compose up`, no cloud account.

Concepts are linked together through `[[wikilinks]]` in their content, building a knowledge graph automatically as you write. The store supports full-text search, typed relations, tags, collections, soft delete, and round-trip export/rebuild to Markdown. **Multi-device sync** works via a git remote (the Bundle is your source of truth; SQLite is a disposable cache). Psychological memory is native: Concepts carry optional **subjects** (who or what the memory is about), **temporal validity** (when it's true), **affect** (emotional valence/arousal), and **supersession** (later facts replace earlier ones).

The `SKILL.md` in this repository makes `second-brain` a drop-in [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills): any agent that loads the skill can save, search, and link Concepts in your brain during a conversation.

## What it's for

The category around you is racing to build your **digital twin** — and to host it. `second-brain` is the same ambition with the ownership inverted: **the twin is yours, on disk, in your git.** It serves two jobs that share the same files.

### 1. Own a psychological twin of a real person (the deep goal)

Point the auto-capture hooks at your real sessions and the brain quietly distills the durable signal of a *person* — their decisions, preferences, knowledge, and the affect behind them — into titled Concepts, never raw chat. What makes it a *twin* and not a pile of notes:

- **Subjects** (`sb_subject`) scope every memory to *who or what it's about*, so a persona sub-graph is one query away.
- **Structured affect** (`sb_affect`) records the emotional valence/arousal/emotion behind a memory — the difference between knowing a fact about someone and knowing how they *felt* about it.
- **Bi-temporal validity** (`sb_valid_from`/`sb_valid_to`) + **supersession** mean the model of the person stays current as they change — `supersede()` closes the old window instead of deleting it — yet stays historically queryable: `recall --as-of <date>` reconstructs *who they were on any past date*. People are not snapshots; this models the trajectory.

Over time this accumulates into an owned, evolving container that models how a real human actually thinks, feels, and changes — the foundation an agent needs to faithfully *shadow* a specific person instead of impersonating a generic one. And because it's plain OKF markdown, you can open the model of yourself in a text editor and read it.

### 2. Give an agent a character

The same primitives, pointed at a fictional subject, give an agent a durable **character**: a consistent personality with its own history, preferences, and emotional coloring, persisted as files you own rather than a system prompt you re-paste every session.

### Stated honestly

The capture pipeline, the psychological fields, and the bi-temporal history are **built and working today** (see [Features](#features)). A turnkey "mimic me" agent on top of them is the **direction, not a finished product** — and on raw mimicry fidelity, the well-funded cloud platforms are further along. What `second-brain` guarantees *right now*, and what none of them offer, is that **the substrate is yours**: the model of a person is never rented, never opaque, and never locked to a vendor that can change the terms or disappear.

## Rented digital mind vs. owned psychological twin

| | Where "you" live | You own the model? | Psychological structure | If they vanish / change terms |
|---|---|---|---|---|
| **Delphi / Personal.ai** (digital-mind platforms) | Their cloud | No — hosted, per their terms & pricing | Yes, but proprietary and opaque | The model of you goes with them |
| **Letta / MemGPT** | Your infra or their cloud | Partially (self-hostable runtime) | Agent-state memory blocks — not a person-model | You keep a runtime, not a portable twin |
| **Mem0 / Zep** | Vendor cloud / API | No / partial | Bi-temporal graph (Zep), but built for *agent* memory | Vendor-controlled; Zep's community edition was deprecated |
| **second-brain** | **Your git, plain markdown** | **Yes, fully** | **Subjects + bi-temporal validity + affect + supersession, in OKF you can read** | **Nothing changes — they're your files** |

The hosted platforms lead on capability — voice, fidelity, scale. `second-brain` leads on the one axis that can't be added later: **you own the twin.** That intersection — *owned, local, file-based, psychologically structured* — is, as far as we can find, empty except for this project.

## Why

Most "AI memory" products store your data in a third-party cloud, behind an API, and behind a vendor that can change pricing, terms, or shut down at any time. Even local-first tools like Obsidian don't speak natively to agents — you end up with one tool for humans and a separate, paid API for AI.

`second-brain` is a deliberately minimal alternative:

- **One file.** A SQLite database you can open with any tool, copy with `cp`, back up with `rsync`, version with `git`.
- **Standard schema.** The schema is checked in as `scripts/schema.sql` and is plain SQL — no proprietary format, no migration service.
- **Agent-native.** Every operation is a single CLI command. Agents read and write the brain with the same interface a human does.
- **Zero dependencies.** If you have Python 3.8+ and a SQLite build, you can run it.

## Features

- **OKF Bundle as source of truth.** Concepts (notes) are persisted as markdown files organized in an OKF v0.1-conformant Bundle. The SQLite database is a fully rebuildable cache — delete it anytime and `rebuild` from the files losslessly.
- **Flat knowledge graph.** Concepts carry tags, an optional collection, and typed relations. No folder hierarchy to maintain.
- **`[[wikilinks]]`.** Cross-references are written in the body and resolved at write time — relations cannot drift from the text.
- **Pending links.** Forward references to not-yet-existing Concepts are stored in an indexed table and promoted to real relations when the target is created.
- **Full-text search.** SQLite FTS5 with soft-delete awareness. Returns sub-100ms results on 50K Concepts.
- **Soft delete by default.** `delete` is reversible; `delete --hard` is permanent. Tombstones propagate over git sync.
- **Typed relations.** `references`, `contradicts`, `expands`, `related` with optional strength.
- **Graph traversal.** Recursive CTE-based traverse from any Concept.
- **Multi-device sync via git.** Export your brain as a Bundle, commit to git, pull/rebase/push, then rebuild on another device. Git is the only sync backbone; all other clouds are one-way mirrors. Works fully offline.
- **Conflict parking.** Concurrent edits to the same Concept on two devices park as `*.conflict.md` instead of clobbering. Human resolves the conflict once; both edits preserved until then.
- **Import / export.** Round-trip to JSON, Markdown (Obsidian-compatible, OKF-native), and CSV.
- **Distill & archive.** Goal-based filter (`distill --query "X"`) writes a focused working brain without touching the old one (pass `--activate` to swap). Cold-storage (`archive --older-than-days 180`) moves untouched Concepts out and VACUUMs the working brain. `merge-brain --from <archive>` brings them back.
- **Psychological memory foundation.** Concepts carry optional **subjects** (who/what the memory is about; enables persona sub-graphs), **temporal validity** (`sb_valid_from`/`to`; enables historical queries), **affect** (emotional valence/arousal/emotion type), and **supersession** (newer facts replace older ones). These fields ride in OKF frontmatter and enable emotion-aware recall, perspective-aware memory synthesis, and — taken together — an owned, evolving model of a real person rather than a flat pile of notes (see [What it's for](#what-its-for)).
- **Logs stay logs; the brain stays clean.** A `Stop` hook archives the full raw transcript of every session to plain files under `~/.secondbrain/logs/` — never into the brain. The brain (`brain.db`) holds only *distilled* know-how: titled Concepts the agent extracts at session end (decisions, preferences, facts, reusable knowledge), plus anything you explicitly save. Searching your knowledge never returns a wall of raw chat.
- **Proactive recall.** A `UserPromptSubmit` hook searches the clean brain against each prompt and injects relevant Concepts into the agent's context *before* it answers — so you don't have to ask "what do I know about X".
- **`/history` slash command.** Browse past conversations in your brain, then dive into the chosen one.
- **Phase 2 (planned).** Optional vector search via `sqlite-vec`, MCP server interface, and selective encryption for private/psychological Concepts.

## Installation

```bash
git clone https://github.com/stancsz/second-brain.git
cd second-brain
python3 scripts/brain_cli.py stats    # first run creates ~/.secondbrain/brain.db
```

Optional, to invoke as `brain`:

```bash
ln -s "$(pwd)/scripts/brain_cli.py" /usr/local/bin/brain
# or
alias brain='python3 ~/path/to/second-brain/scripts/brain_cli.py'
```

The only runtime requirement is Python 3.8+ with `sqlite3` (included in the standard library). The schema uses FTS5, JSON1, and recursive CTEs; these are built into the Python-bundled SQLite since 3.9, otherwise SQLite 3.41+ is required.

To use it as a Claude Code skill (with auto-capture and the `/history` command), see [Use with Claude Code](#use-with-claude-code) below — or just run `bash install.sh` after cloning.

## Quick start

```bash
# Capture
python3 scripts/brain_cli.py add "RAG" "Retrieval-augmented generation" \
  --collection AI --tags rag,llm

# Recall
python3 scripts/brain_cli.py search "RAG"

# Link (the [[RAG]] in content auto-resolves to a references relation;
# if RAG doesn't exist yet, it goes to pending_links and resolves on first match)
python3 scripts/brain_cli.py add "Vector Search" "See [[RAG]]" --collection AI

# Traverse the graph
python3 scripts/brain_cli.py related <id>
python3 scripts/brain_cli.py traverse <id> --depth 2

# Brain health
python3 scripts/brain_cli.py summary

# Distill a focused working brain (old brain stays as a point-in-time backup)
python3 scripts/brain_cli.py distill --query "RAG" --output focused.db --activate

# Cold-store untouched Concepts (180d+) and shrink the working brain
python3 scripts/brain_cli.py archive --output archive-2026.db --older-than-days 180

# Bring archived Concepts back
python3 scripts/brain_cli.py merge-brain --from archive-2026.db

# Browse past conversation logs (also available as the /history slash command)
ls -1t ~/.secondbrain/logs/*/*/*.jsonl 2>/dev/null | head

# Export an Obsidian-compatible vault (one .md file per note, into a directory)
python3 scripts/brain_cli.py export --format markdown --output ./brain-vault
```

## Use with Claude Code

This repository is itself a Claude Code skill — `SKILL.md` defines triggers and behavior.

### Install by asking your agent (recommended)

`second-brain` is agent-native, so the fastest install is to let the agent do it. Paste this into Claude Code (or any coding agent with shell access):

```
Install the second-brain skill from https://github.com/stancsz/second-brain
into my personal Claude Code skills. Cloning the repo does NOT configure the
skill — you MUST also run install.sh, then verify the Stop and PreCompact
hooks actually landed in ~/.claude/settings.json, then end-to-end test
add+search. Do not report success until all three are confirmed.
```

A common failure mode is agents stopping after `git clone` and the CLI smoke test, leaving auto-capture wired to nothing. The agent must complete every step below, in order:

1. **Clone into the skills directory.**
   ```bash
   mkdir -p ~/.claude/skills
   git clone https://github.com/stancsz/second-brain.git ~/.claude/skills/second-brain
   ```
   (Use `.claude/skills/second-brain` instead for a single project.)

2. **Smoke-test the CLI** — this also creates `~/.secondbrain/brain.db` on first run.
   ```bash
   python3 ~/.claude/skills/second-brain/scripts/brain_cli.py stats
   ```

3. **Run the installer** to wire up the auto-capture hooks and the `/history` command without clobbering existing settings.
   ```bash
   bash ~/.claude/skills/second-brain/install.sh
   ```
   `install.sh` merges the `Stop` / `PreCompact` hooks into your `settings.json` (it does **not** overwrite the file), symlinks `commands/history.md`, and prints a `SECONDBRAIN_CLI` env-var hint.

4. **Verify** end to end.
   ```bash
   python3 ~/.claude/skills/second-brain/scripts/brain_cli.py add "Install test" "second-brain is live"
   python3 ~/.claude/skills/second-brain/scripts/brain_cli.py search "live"
   ```

5. **Reload the skill.** Restart Claude Code (or start a new session) so it picks up the new skill, hooks, and slash command.

**Verify the hooks are actually wired.** Run this on your own to confirm — the agent's "I ran install.sh" is not the same as the hooks being present:

```bash
cat ~/.claude/settings.json | python3 -m json.tool | grep -A 4 -E '"(Stop|PreCompact)"'
```

You should see a `Stop` and a `PreCompact` entry, each with a `hooks` array whose `command` ends in `hooks/capture_conversation.py`. If those entries are missing, auto-capture is **not** working yet — re-run `bash ~/.claude/skills/second-brain/install.sh` and check `~/.claude/settings.json` directly.

After that, say "remember this" or "what do I know about X" in any session and the skill takes over.

### Install manually

`SKILL.md` defines the triggers and behavior; cloning the repo into a skills directory is all Claude Code needs. Three ways:

**Project scope** (one project):

```bash
mkdir -p .claude/skills
git clone https://github.com/stancsz/second-brain.git .claude/skills/second-brain
```

**Personal scope** (all your projects):

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/stancsz/second-brain.git ~/.claude/skills/second-brain
```

**Submodule** (if you want to pin a version):

```bash
git submodule add https://github.com/stancsz/second-brain.git .claude/skills/second-brain
```

Once installed, the agent will catch phrases like "remember this", "what do I know about X", "catch me up on project Y", "记一下", "我之前写过 X 吗", and act on them using your brain.

### Auto-capture & auto-distill (optional but recommended)

The design splits cleanly in two: **logs stay logs, the brain stays clean.**

- **Raw transcripts → log files.** Every session is archived to
  `~/.secondbrain/logs/YYYY/MM/` as plain JSONL. These are *logs* — browse them
  with `/history`, `grep` them, delete them, git-ignore them. They never touch
  the brain.
- **Know-how → the brain.** At session end the hook asks the agent to extract
  the durable bits (decisions, preferences, facts, reusable knowledge — and,
  over many sessions, the durable signal of *you*: how you decide, what you
  prefer, the affect behind it) into clean, titled Concepts. The brain
  accumulates distilled knowledge, not bulk chat — so `search` and proactive
  recall stay sharp. This is the shadow-distillation loop in practice: each
  session leaves the model of the person a little more complete.

The easiest way to wire it up is `install.sh`, which merges the hooks into your
existing settings (no overwrite) and substitutes the real path:

```bash
bash <repo>/install.sh
```

To wire it up by hand instead, merge the entries from `settings.example.json`
into your own `~/.claude/settings.json` (personal) or `.claude/settings.json`
(project). Don't `cp` it over an existing file — that would discard your other
settings. Replace `/path/to/second-brain` with the real repo path.

This wires up three hooks:

- **`Stop`** (`hooks/capture_conversation.py`) — logs the transcript to disk,
  then nudges the agent once to distill durable know-how into the brain. Quiet,
  never wedges the session, and audits to `hooks/capture_conversation.log`. The
  nudge is gated by a **smart trigger**: trivial sessions (short, or no
  decision/remember markers) skip the block and just leave the log on disk.
  When the trigger fires, a **heuristic pre-pass** surfaces up to 10 candidate
  lines for the agent to filter — the agent reviews the candidates, not the
  full transcript. Result: less latency, higher precision.
- **`PreCompact`** *(optional)* — snapshots the log before context compaction in
  long sessions. Never distills. Comment out if noisy.
- **`UserPromptSubmit`** (`hooks/recall_memories.py`) — proactive recall: searches
  the clean brain against each prompt and injects relevant notes into context.

Env switches: `SECONDBRAIN_SKIP_CAPTURE=1` (disable the capture hook),
`SECONDBRAIN_SKIP_DISTILL=1` (log only, no distill nudge),
`SECONDBRAIN_SKIP_RECALL=1` (disable proactive recall),
`SECONDBRAIN_LOGS_DIR=/path` (move the log directory).

Smart-trigger knobs (all default-off; tune if you want more or less
auto-distill):

- `SECONDBRAIN_MIN_USER_CHARS=1500` — min user-text chars before distill fires
- `SECONDBRAIN_MIN_TURNS=4` — min user-prompt turns before distill fires
- `SECONDBRAIN_LONG_SESSION_TURNS=20` — above this, the marker check is skipped
  (long sessions get distilled regardless)
- `SECONDBRAIN_MAX_CANDIDATES=10` — max candidate lines surfaced to the agent

```bash
# disable everything for one session
SECONDBRAIN_SKIP_CAPTURE=1 SECONDBRAIN_SKIP_RECALL=1 claude
```

### `/history` slash command

The repo ships a slash command at `commands/history.md` that browses your
conversation **logs** (the files under `~/.secondbrain/logs/`, not the brain).
Wire it up with a symlink (`install.sh` does this for you):

```bash
# Personal scope
mkdir -p ~/.claude/commands
ln -s <repo>/commands/history.md ~/.claude/commands/history.md
```

Then type `/history` — the agent lists your recent session logs and opens the one
you pick, rendered readably. You can also say "show me my last 3 conversations".
From there it can **distill** a log into the brain on request.

## Comparison

| Tool | Data location | Agent-readable | Lock-in | Backup | Cross-session memory | Install |
|---|---|---|---|---|---|---|
| Notion AI | Notion cloud | No | High | Vendor-controlled | No | Browser |
| ChatGPT Memory | OpenAI cloud | No | Total (black box) | Vendor-controlled | Yes (opaque) | Browser |
| Claude Projects | Anthropic cloud | No | High | Vendor-controlled | Yes (per-project) | Browser |
| mem0 | Vendor Postgres | Yes (paid API) | Medium (SDK bound) | Vendor-controlled | Yes (API) | `pip install` + key |
| Obsidian | Local `.md` | No (plugin required) | None | Manual | No (DIY) | Desktop app |
| Logseq | Local `.md` | No | None | Manual | No | Desktop app |
| Anytype | Local (P2P) | No | None | Manual sync | No | Desktop app |
| Quivr / privateGPT | Local vector DB | Via API | None | Manual | No | Docker + models |
| Apple Notes / Keep / OneNote | Vendor cloud | No | High | Vendor-controlled | No | OS-bundled |
| Evernote | Vendor cloud | No | High (historic) | Vendor-controlled | No | Desktop / web |
| **second-brain** | **Local SQLite** | **Yes (CLI)** | **None** | **`cp` / `git push`** | **Yes (agent-native)** | **`git clone`** |

**What only `second-brain` offers in this list:**

1. **Full data ownership.** The store is a plain SQLite file. `sqlite3 brain.db` opens it. The schema is in this repository as `scripts/schema.sql`. There is no export flow because there is no vendor to export from.
2. **Versionable.** The whole brain is one file. `git init` it, `git push` it to a private GitHub repo, get free history, diff, and disaster recovery.
3. **Agent-native.** The CLI is the API. There is no second interface for "AI mode" that you have to pay for separately.
4. **Air-gap and compliance ready.** Zero network calls, zero external dependencies, zero telemetry. Passes the "can legal/security read the whole thing in an afternoon?" test. Runs identically on an internet-connected laptop and a fully isolated private network.

## When to use

- You use AI agents (Claude Code, Cursor, Aider, Continue, custom) and want them to remember across sessions.
- You want a knowledge base that survives any single vendor disappearing.
- You are comfortable with a 200-line Python CLI and a SQLite file.
- You want one tool that humans and agents both drive, with the same data.
- **Your organisation does not allow third-party memory or data-retention services.** `second-brain` never phones home, sends no telemetry, and stores nothing outside the file you point it at. Compliance, legal, and security teams can audit the entire codebase in an afternoon — it is 400 lines of stdlib Python and a SQL schema.
- **You are running agents in an air-gapped or offline environment.** Every dependency ships with Python's standard library. No package registry, no cloud API, no license server. Once the repo is cloned, it works indefinitely with zero network access — on a developer laptop, a private build server, a factory floor, or an isolated government network.
- **You are building or deploying local agents and need a memory layer that stays local.** Most "agent memory" solutions are SaaS APIs (mem0, Zep, LangMem) or require running a vector database (Qdrant, Weaviate, Chroma). `second-brain` is a single SQLite file: no daemon to keep alive, no Docker image to pull, no API key to rotate.

## When not to use

- You want a polished WYSIWYG note-taking app for non-technical users → use Obsidian or Notion.
- You need a team wiki with permissions and comments → use Notion or Confluence.
- You need to store millions of documents and run vector search at scale → use a dedicated vector database; `second-brain` is for personal-scale knowledge.
- You cannot run Python locally → use a hosted note service.

## Architecture

See [`references/architecture.md`](./references/architecture.md) for:

- The data model (3 tables + FTS + `pending_links`)
- FTS5 correctness notes (the v2 bugs and their v2.1 fixes)
- Wikilink resolution rules (frozen at write time)
- Soft delete semantics
- Phase 2 MCP interface contract
- v1 → v2 migration
- Performance targets

## Backup strategy

The recommended setup is to put `~/.secondbrain/brain.db` under version control in a private GitHub repository. The database is a single file; even at 50K Concepts it is typically under 100 MB, which is fine for `git push`.

For continuous backup, pair with [litestream](https://litestream.io/) to replicate the WAL stream to S3, Backblaze, or any S3-compatible object store. Schema migrations and disaster recovery are standard SQLite operations.

## Roadmap

- **v2.1 (current).** FTS5, soft delete, write-time-frozen wikilinks, `pending_links` table, recursive traverse.
- **Phase 2.** MCP server, vector search via `sqlite-vec`, automatic `inferred`-source links above a similarity threshold.
- **North star — the shadow-distilled human.** The psychological-memory layer (subjects, affect, bi-temporal validity, supersession) and the auto-distill loop are the foundation for an agent that can faithfully shadow a *specific* real person over time. The work ahead: richer persona synthesis from the sub-graph, drift/consistency checks across superseded facts, and a recall surface that reconstructs "who this person was as of date X" for grounding a mimic agent.
- **Ideas.** Markdown round-trip sync, Obsidian-compatible export refinements, encrypted local replicas.

## Contributing

Issues and pull requests welcome. The schema is the API — please open an issue before adding tables or columns.

## License

[MIT](./LICENSE) © 2026 second-brain contributors
