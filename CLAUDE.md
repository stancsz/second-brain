# CLAUDE.md — working in the second-brain repo

This file orients Claude Code (and any agent) working in this repository. Read it
first; it encodes the invariants that must not be broken and how work gets done here.

## What this project is

`second-brain` is a **local, file-based knowledge graph for AI agents** — one SQLite
cache over an **OKF v0.1** Bundle of markdown files, synced via git, with a native
**psychological-memory layer** (subjects, bi-temporal validity, structured affect,
selective encryption). Zero third-party deps in the core. The thesis: *you should own
your memory as plain files in your own git, not rent it from a vendor.*

- Entry points: `scripts/brain.py` (the engine), `scripts/brain_cli.py` (`brain` CLI),
  `scripts/bundle.py` (OKF export/rebuild), `scripts/sync.py` (git sync spine),
  `scripts/crypto.py` (optional encryption adapter), `scripts/okf.py` (serializer).
- Skill surface: `SKILL.md` + `commands/` make it a drop-in Claude Code skill.
- Data lives at `~/.secondbrain/` (db + OKF bundle + key); never in the repo.

## Non-negotiable architecture invariants

1. **Files are truth; SQLite is a rebuildable index.** Never make `brain.db`
   authoritative. Anything in the DB must be reconstructable from the OKF Bundle by
   `bundle.rebuild()`. New per-Concept data goes in `concepts.metadata` and is
   re-derived into a SQLite table by a `rebuild_*_index()` (the "derived-index
   pattern" — see `subjects`, `affect`, `validity`).
2. **Stdlib-only core; optional deps are lazy adapters with a fallback.** `brain.py`
   imports only the stdlib. Anything else (`cryptography`, future `sqlite-vec`,
   `boto3`) is imported lazily inside an adapter and must degrade gracefully when
   absent — never a hard dependency of the core.
3. **Windows-first encoding discipline.** Every `open()` passes `encoding="utf-8"`;
   scripts reconfigure `sys.stdout/stderr` to UTF-8 at entry; any text printed to a
   child stderr must be ASCII-safe (cp1252 children crash UTF-8 readers — see G19).
4. **Bi-temporal history is preserved, never deleted.** A contradiction closes the
   old validity window (`supersede()`); it never overwrites or drops the old fact.
5. **Secrets never enter the repo.** Keys live in `~/.secondbrain/`; the ship gate
   scans for them.

## How work gets done here: the mochu loop

This repo is driven by **mochu** (`~/.claude/skills/mochu`), a loop engineering
harness. State lives in `.mochu/`:

- `ledger.md` — append-only iteration history (read the last ~5 to orient)
- `gaps.md` — scored backlog; `RELEASE.md` — the definition of done
- `verifiers/` + `REGISTRY.md` — the append-only verifier corpus (the ratchet)
- `cooldown.md`, `wip/`, `INBOX.md`, `competitors.md`

**The contract:** one verified gap per iteration. Verifiers are authored and frozen
*before* product code (red-confirmed), then build to green, then the full corpus +
`ship_gate.py` must pass. Never weaken a frozen verifier to pass.

Run the loop: invoke the `mochu` skill ("run mochu" / "do an iteration"). Verify
anything: `python scripts/run_corpus.py` and `python scripts/ship_gate.py`.

## Commands you'll use

```bash
python -m pytest tests/ -q            # unit tests (must stay green)
python scripts/run_corpus.py          # run every verifier in the ratchet
python scripts/ship_gate.py           # pre-merge gate (tamper + secrets + corpus)
python scripts/brain_cli.py --help    # the brain CLI
python scripts/crypto.py init         # set up the optional encryption key
```

Tests and the corpus must be green before any merge to `main`. PRs from
`mochu/integration` are human-gated.

## The growth loop

Beyond the engineering loop, a **growth loop** drives go-to-market (research → user
pain points → marketing assets → viral/social). Its brief and process live in
`growth/` (`growth/BRIEF.md`, `growth/LOOP.md`). The GitHub Pages landing source is
`docs/index.md`. Treat marketing copy with the same evidence discipline: claims must
be grounded (cite the research in `growth/BRIEF.md`), never invented.

## Positioning (keep messaging consistent)

second-brain is the **disruptor** to rented AI-memory infra. Every competitor pain
point maps to a moat: cost cliffs (Mem0 graph = $249/mo) → $0 local; deprecated
self-hosting (Zep Community Edition) → one SQLite file; "privacy drift" → you own the
files + selective encryption; vendor/framework lock-in → OKF markdown in your git.
Don't overclaim: we are FTS-first (semantic search is a roadmap adapter), and we are
local-first by design, not a managed cloud.
