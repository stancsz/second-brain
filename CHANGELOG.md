# Changelog

## [Unreleased]

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
