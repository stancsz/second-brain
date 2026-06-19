# Product — SecondBrain

## What it is
A local, file-based knowledge graph ("second brain" / 长脑子) packaged as a Claude Code skill.
Captures, searches, links, and recalls notes across conversations. Today: a single SQLite file
(`~/.secondbrain/brain.db`) with FTS5 full-text search and a wikilink-driven relation graph,
plus capture/recall hooks and `/brain`, `/history` commands.

## Who uses it
- Individual power users of Claude Code who want persistent, portable personal memory across sessions.
- (Emerging) builders of emotional/psychological **mimic agents** (cf. `bbju`, `create-ex` skills)
  who need a structured store of a person's traits, values, patterns, and emotional episodes.

## Job to be done
"Remember what I tell you, recall my own knowledge on demand, and never lock my memory inside one
tool or one machine." Memory must be **portable, format-agnostic, backed up, and survivable.**

## Strategic direction (locked — see docs/)
Evolve from SQLite-as-truth to **OKF-files-as-truth**: Concepts are Open Knowledge Format markdown
files (Google OKF v0.1), SQLite is a rebuildable index, **git is the sole bidirectional sync spine**,
and S3/GCS/Google Drive/OneDrive are one-way backup mirrors. Extend with a psychological memory layer
(temporal validity, subjects, structured affect, memory kinds) to be the foundation for mimic agents.

## Deploy / distribution
Distributed as a Claude Code skill + plugin (this git repo). No hosted service; "deploy" = the skill
installed at `~/.claude/skills/second-brain` via `install.sh`. **Merges gated by the human:** each mochu
iteration works on branch `mochu/<gap-id>` and opens a PR; the human reviews and merges to `main`.

The OKF **Bundle** (source-of-truth files) lives in its **own private repo at `~/.secondbrain/okf/`**,
separate from this skill repo, so personal/psychological data never mixes with publishable skill code.

## Tech constraints
- Core must stay **dependency-free** (pure Python stdlib + sqlite3); adapters lazy-import their SDKs.
- Windows-first dev environment (bash via Git Bash); must also work on macOS/Linux.
- Token-minimalism: recall output must stay compact.
