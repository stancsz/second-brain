# Changelog

## [Unreleased]

### Changed
- **Docs surface rename: R4 M3 closed** (R4 / G23, mochu iter-13) — 9 tracked
  files renamed `drawer`/`drawers`/`Drawers` → `concept`/`concepts`/`Concepts`
  across `commands/`, `docs/`, `references/`, and `README.zh.md`. Total 59 hits.
  `docs/02-okf-and-terminology.md`'s comparison table was restructured (the
  old "Old → New" column would have silently shown the same word twice after
  the rename; the file now describes the current canonical state, with the
  rename history in `.mochu/ledger.md` iter-12 and `brain.py:_migrate_v21_to_concepts`).
  `references/architecture.md` title updated v2.1 → v3.0 to match the body,
  which now describes the v3.0 schema. New verifier `docs-surface-rename`
  locks in zero residual `drawer` references across 13 in-scope files. R4
  is now complete; the only `drawer` mentions left in tracked files are
  intentional: in `brain.py:_migrate_v21_to_concepts` (the v2.1→v3.0 migration
  function references the old `drawers`/`drawers_fts`/`drawers_ai/ad/au`
  names by design), and in CHANGELOG.md (historical record of iter-1 through
  iter-7 that used the old name).
  - Known limitations: untracked files in `docs/` (08-iter7-findings.md,
    HANDOFF.md, brief.md, decisions/D001-terminology-rename-before-phase-c.md,
    tasks/T002-rename-drawer-to-concept.md) still contain `drawer` references
    — these were never committed, so the G23 verifier (which scans git-tracked
    files) correctly does not cover them. Tracked as new gap G24 (docs hygiene:
    commit + rename these untracked docs files).

### Changed
- **Schema + code rename: `drawers` → `concepts`** (R4 / G04, mochu iter-12) —
  the live SQLite table is now `concepts` (OKF v0.1 canonical name), with
  matching `concept_tags` / `concepts_fts` / `concepts_ai/ad/au` triggers.
  A v2.1 brain.db auto-migrates on first open via
  `SecondBrain._migrate_v21_to_concepts()`: the table is renamed in place,
  the FTS5 index is rebuilt, the old triggers are dropped (they survive
  `ALTER TABLE RENAME` with a stale body referring to the dropped FTS5
  table), and the new triggers + FTS5 are recreated against the renamed
  base table. All public methods of `SecondBrain` now use
  `concept`/`concepts` in their return dict keys and parameter names
  (e.g. `export()["concepts"]`, `add() → {"id", "title", "content", ...}`).
  `scripts/brain_cli.py`, `scripts/bundle.py`, `scripts/sync.py`,
  `hooks/capture_conversation.py`, `hooks/recall_memories.py`, and their
  tests are all updated to the new vocabulary. `tests/test_brain.py`
  passes 51/51; the full mochu corpus is 12/12 green. M3 of R4
  (commands/ docs/ references/ CHANGELOG narrative updates) is
  intentionally left as a separate gap so this iter's diff stays
  focused on the schema + code surface.
  - Known limitations: `commands/brain.md`, `commands/history.md`,
    `docs/02-okf-and-terminology.md`, `references/architecture.md`,
    `references/distill-archive.md`, `README.zh.md`, and several
    `docs/tasks/*` still mention `drawer`/`drawers`. These are
    documentation-only (no code) and are tracked as M3 of R4.

### Added
- **Conflict parking** (`scripts/sync.py`) — when two devices edit the same concept concurrently,
  `sync` no longer crashes or clobbers: the rebase conflict is parked — the upstream version stays
  canonical and the incoming local edit is written to a sibling `<slug>.conflict.md`, leaving a
  clean working tree. `conflicts(bundle)` lists parked copies; they are never imported as drawers
  or touched by export until a human resolves them (resolve = delete the conflict file). Both edits
  are preserved. (mochu iter-6, gap G06)
- **Tombstone deletes over git** (`scripts/bundle.py`, `scripts/sync.py`) — deletes now survive
  sync: a soft-delete moves the concept to `.trash/` as a tombstone and propagates to other
  devices; `restore` moves it back and propagates; a hard-delete removes the file so it is gone
  everywhere and never resurrects. Export is now **incremental** (only changed concepts are
  rewritten, keyed by `sb_id`), which both fixes a latent resurrection bug and lets git merge a
  remote's edits to an unchanged concept without a spurious local-overwrite conflict. `sync` now
  detects a fresh clone (empty db + populated bundle) and imports rather than wiping. log.md dates
  use the round-trip-stable `updated_at` so resyncs don't churn. (mochu iter-5, gap G07)
- **Git sync spine** (`scripts/sync.py`) — `sync(db, bundle, remote)` makes memory portable
  across devices: serialize brain.db → OKF Bundle, commit, `pull --rebase`, push, then rebuild
  the brain from the merged Bundle. Git is the single bidirectional channel; works fully offline
  / local-only when no remote is set. Deterministic export means an unchanged brain produces no
  commit. Verified by a real two-clone multi-device round-trip. (mochu iter-4, gap G05)
  - Also hardened `bundle.rebuild` to flush the WAL and retry file replacement (Windows handle lag);
    `sync` no longer leaks the rebuilt connection.
  - Known limitations: concurrent edits to the *same* concept are not yet parked as conflicts (G06);
    deletes don't yet propagate as tombstones over git (G07); no cloud mirrors yet (G11+).
- **OKF reserved files on export** (`scripts/bundle.py`) — `export` now writes a root `index.md`
  declaring `okf_version: "0.1"` and listing collections + root concepts, a per-subdirectory
  `index.md` (progressive disclosure, no frontmatter per OKF §6), and a root `log.md` with
  ISO date-grouped creation entries newest-first (OKF §7). All links resolve to real files;
  `rebuild` ignores the reserved files. The Bundle is now OKF v0.1-conformant end to end.
  (mochu iter-3, gap G03)
- **Bundle export / rebuild** (`scripts/bundle.py`) — `export(brain, dir)` writes the whole
  brain (including soft-deleted drawers) as an OKF Bundle; `rebuild(dir, db)` reconstructs a
  **fresh** brain.db from the Bundle with zero loss: drawers, tags, sources, collections,
  soft-delete state, wikilink relations, and the FTS index all survive. This makes SQLite a
  disposable cache and the OKF files the source of truth. `type`/`sb_*` fields ride in
  `drawers.metadata` until real columns land (G08–G10). Reserved-name titles (`index`/`log`)
  are auto-suffixed. (mochu iter-2, gap G02)
  - Known limitations: no `index.md`/`log.md` generation yet (G03); not wired into the CLI/skill
    or any sync flow yet (G05); cross-concept `[[wikilink]]` rendering still verbatim.

- **OKF serializer** (`scripts/okf.py`) — converts a Concept to/from an Open Knowledge
  Format (OKF v0.1) markdown document with YAML frontmatter, and back, losslessly. Supports
  the namespaced `sb_*` psychological extensions (`sb_subject`, `sb_valid_from/to`,
  `sb_supersedes`, `sb_affect`, `sb_relations`, `sb_deleted`), encodes `collection` as the
  file's bundle directory, and renders `sources` as an OKF `resource` + `# Citations` section.
  Run `python scripts/okf.py demo` to see a sample document. (mochu iter-1, gap G01)
  - Known limitations: serializer only; it does **not** yet walk a bundle to rebuild the DB
    (G02), generate `index.md`/`log.md` (G03), rename the live `drawer` model to `Concept`
    (G04), or render cross-concept `[[wikilinks]]` as bundle-relative OKF links (those remain
    verbatim in the body for now). No CLI/skill wiring yet.
