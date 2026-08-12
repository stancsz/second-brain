# CLAUDE.md — working in second-brain

This file orients any coding agent working in this repository. Evidence in the
current tree takes priority over old design notes.

## Product

`second-brain` is a local, file-based knowledge graph that carries durable
context across agent hosts. An OKF Markdown Bundle is canonical; SQLite is a
rebuildable projection. Agent Skills, MCP, and the CLI are portable surfaces.
Claude Code lifecycle hooks are a host-specific adapter.

Primary entry points:

- `scripts/brain.py` — engine and SQLite projection
- `scripts/brain_cli.py` — human/agent CLI
- `scripts/bundle.py` and `scripts/okf.py` — Bundle export and rebuild
- `scripts/brain_mcp.py` — stdio MCP server
- `scripts/sync.py` — bidirectional git sync
- `scripts/storage.py` and `scripts/storage_cli.py` — immutable backup snapshots
- `scripts/crypto.py` — optional selective encryption
- `SKILL.md` — portable Agent Skill

Runtime data belongs under `~/.secondbrain/`, never in this repository.

## Architectural invariants

1. **Files are truth.** New durable fields must survive Bundle export and a full
   rebuild. SQLite tables are disposable indexes.
2. **The core is standard-library Python.** Optional dependencies are imported
   lazily inside adapters and have tested missing-dependency errors.
3. **Git is the only bidirectional sync path.** Storage providers are immutable
   snapshot/restore mirrors until a merge protocol is separately designed.
4. **Remote plaintext must be an explicit choice.** Use strict encryption mode
   for sensitive Concepts; keys and databases must never be staged.
5. **History is preserved.** Supersession closes an old validity window rather
   than deleting the old fact. Soft delete remains recoverable.
6. **Windows is a first-class platform.** Open text as UTF-8, avoid shell-only
   assumptions in Python, and test path/case behaviour across platforms.
7. **Claims match evidence.** “Repo-tested,” “package-validated,” “documented
   target,” and “live-tested” are different assertions. Do not collapse them.

## Public release gate

The old private `.mochu` verifier corpus is not part of the current repository.
Do not cite it as release evidence. The checked-in public gate is:

```bash
python scripts/validate_skill.py .
python scripts/run_corpus.py
python scripts/ship_gate.py
```

`run_corpus.py` compiles Python and runs the public unit/integration suite.
`ship_gate.py` adds package validation and a diff/untracked secret scan. CI runs
the same core checks on Ubuntu, Windows, and macOS with Python 3.10 and 3.14.

For focused work, run the narrow test first, then the full gate. Do not weaken a
test merely to make an implementation pass.

## Change rules

- Observe the surrounding implementation before editing.
- Preserve unrelated and untracked files.
- Add automated evidence for new behaviour and missing-adapter paths.
- For host compatibility, prove a real initialize/add/search handshake when the
  host can be automated. A config example alone is documentation.
- For storage, prove push → wipe → pull → verified restore → rebuild. Never use
  destructive cloud sync primitives inside an adapter.
- For Obsidian, preserve the original Markdown body and be explicit about YAML,
  attachment, alias, fragment, and path-resolution limits.
- Re-read the diff, run `git diff --check`, and run the public release gate.

## Positioning

Lead with the repeated job: a developer switches among Claude, Codex, Gemini,
OpenCode, or Cline and recovers verified project decisions without surrendering
the canonical store. Psychological-memory fields are a high-sensitivity optional
capability, not the first-run pitch.

Do not claim universal host support, native provider integrations, native
Obsidian sync, end-to-end encryption, or production SaaS readiness without the
corresponding live evidence. Current truth and gaps live in
`docs/COMPATIBILITY.md`, `docs/PROJECT_REVIEW.md`, and `docs/THREAT_MODEL.md`.
