# Changelog

## [Unreleased]

## [0.2.0] - 2026-06-20

### Added
- **Selective-by-tag encryption for private Concepts** (R13 / G13, mochu iter-22)
  — Concepts that are private (tag `private`/`psych`, or OKF `type`
  `Episode`/`RelationshipModel`) are now encrypted before they enter the OKF
  Bundle that git pushes, while public Concepts stay plaintext and diffable. New
  optional adapter `scripts/crypto.py` (Fernet via a **lazy-imported**
  `cryptography` — the stdlib-only core never imports it). On `export`, a private
  Concept's whole OKF document is encrypted into a minimal envelope (`type`,
  `sb_id`, `sb_encrypted: fernet` + ciphertext) and is **excluded from
  `index.md`/`log.md`** so its title never leaks; on `rebuild` it is transparently
  decrypted (all `sb_*` psych fields round-trip). Encryption is **opt-in**: it
  engages only when a key is configured (`$SECONDBRAIN_KEY_FILE` or
  `~/.secondbrain/secret.key`, created by `python scripts/crypto.py init`).
  Without a key, private Concepts export as plaintext but a **warning** is emitted
  (never silent); with `SECONDBRAIN_REQUIRE_ENCRYPTION=1`, export **refuses** to
  write private plaintext at all (the no-leak guarantee). Encryption is
  **idempotent** — an unchanged private Concept keeps its existing ciphertext, so
  there is no git churn on re-sync. New tests in `tests/test_crypto.py`; verifier
  `selective-encryption` (corpus 21/21). **Closes R13.**

### Fixed
- **Validity window coherence** (G32 / reliability, hardens R11, mochu iter-21) —
  a backwards window (`valid_from` after `valid_to`) was storable; it can never
  contain any `as_of` under `recall_as_of`'s predicate, so it is a mistake, not a
  representable state. Mirroring the G26 two-contract shape: the **write path**
  (`add` / `update` / `supersede`, including a `supersede` `as_of` that precedes
  the old fact's `valid_from`) now raises `ValueError`; the **rebuild path**
  **quarantines** a backwards window already in metadata (drops the whole window,
  keeps the concept and every other row, never crashes). Bounds are compared
  temporally, so mixed date/datetime forms order correctly; equal-bound and
  single-bound (partial) windows are accepted. `brain add --valid-from X
  --valid-to Y` with `X > Y` is a clean one-line message, no traceback. 6 new unit
  tests (145→151); verifier `window-coherence` (corpus 20/20).
- **`restore()` recovers psychological dimensions** (G27 / reliability, hardens
  R10/R11/R12, mochu iter-20) — a Concept that was soft-deleted, carried through a
  `bundle.rebuild` (which skips indexing deleted Concepts), and then restored had
  empty affect/subject/validity derived rows until the *next* full rebuild, because
  `restore()` re-synced only wikilinks + pending links. It now re-derives all three
  psychological indexes from the Concept's surviving `metadata`: affect (R12),
  subject sub-graph membership (R10), and the validity window (R11) — exactly, with
  no second rebuild required. Restoring a plain note adds no spurious rows; the live
  delete→restore path (no rebuild) is unchanged and idempotent. 2 new unit tests
  (143→145); verifier `restore-psych-dims` (corpus 19/19).
- **ISO date validation on validity windows** (G26 / reliability, hardens R11,
  mochu iter-19) — `sb_valid_from` / `sb_valid_to` were stored as opaque strings,
  so a malformed date (`"June 2023"`, `"2023/13/01"`) was silently accepted and
  then sorted wrong under the lexicographic comparison `recall_as_of` relies on.
  Now two contracts hold: the **write path** (`add` / `update` / `supersede`)
  validates against ISO 8601 and raises `ValueError` with an actionable message
  before any row is written (well-formed dates, ISO datetimes, and leap dates
  like `2024-02-29` are accepted); the **rebuild path** (`rebuild_validity_index`,
  reached by `bundle.rebuild`) **quarantines** a malformed date already present in
  hand-authored OKF metadata — that concept's window is dropped, the concept
  itself and every other concept's window survive, and the rebuild never crashes.
  `brain add --valid-from "June 2023"` now exits 1 with a clean one-line message
  instead of a stack trace (a narrow instance of the CLI error-boundary work
  tracked broadly as G28). 6 new unit tests (137→143); verifier `iso-validation`
  (corpus 18/18).

### Added
- **Point-in-time recall: `recall_as_of` + `brain recall --as-of`** (R11 / G09
  **M2 of 2 — R11 closed**, mochu iter-18) — `SecondBrain.recall_as_of(as_of,
  query=None, collection=None, limit=50)` returns Concepts whose validity window
  contains the given ISO date: `(valid_from IS NULL OR valid_from <= as_of) AND
  (valid_to IS NULL OR valid_to > as_of)`. Timeless Concepts (no validity row)
  appear for any `as_of` with no lower-bound restriction. `brain recall
  --as-of <date> [query] [--collection C] [--limit N]` is the CLI form.
  Exclusive upper boundary: a fact with `valid_to=X` is NOT returned at
  `as_of=X`. 7 new unit tests (130→137); verifier `temporal-asof` (corpus
  17/17). This closes **R11** (Zep/Graphiti bi-temporal parity: per-fact
  validity windows + point-in-time query).
  - Known limitations: `as_of` is compared lexicographically against ISO strings
    (works correctly for YYYY-MM-DD dates; datetime strings also compare correctly
    due to ISO 8601 sort order). No `recall_as_of` + graph-proximity reranking
    yet (G25 is the right gap for that). `brain recall --as-of` output does not
    yet display the validity window inline (use `brain show <id>` to see it).
- **Bi-temporal validity storage + supersession** (R11 / G09 **M1 of 2**, mochu
  iter-17) — the temporal fields `sb_valid_from` / `sb_valid_to` /
  `sb_supersedes` (already round-tripped through OKF files) now populate a typed
  `validity` table (one row per Concept with a window, `ON DELETE CASCADE`),
  rebuilt from `concepts.metadata` by `bundle.rebuild()`. New API:
  `SecondBrain.validity(id)` returns `{valid_from, valid_to, supersedes}` (None
  when timeless; partial windows OK), and **`supersede(old_id, title, content,
  …, as_of=…)`** records a contradiction the bi-temporal way — it CLOSES the old
  fact's window at `as_of` and adds a new fact with `supersedes=old_id` and
  `valid_from=as_of`, **preserving the old fact** (history stays queryable, never
  deleted). `add`/`update` gained `--valid-from` / `--valid-to` / `--supersedes`
  capture flags; `brain show <id>` prints the validity window (and what it
  supersedes). Matches the core of Zep/Graphiti's bi-temporal model
  (per-fact validity windows; contradiction closes rather than deletes). 7 new
  unit tests; verifier `temporal-validity` (corpus 16/16).
  - **Not yet** (M2, next iteration): `recall_as_of(date)` / `brain recall
    --as-of <date>` point-in-time query that returns the historically-valid
    state and excludes superseded/expired facts — that query is what closes R11.
    M1 ships the storage and write-path R11 stands on.
- **Structured affect: `sb_affect` is now queryable** (R12 / G10, mochu iter-15)
  — a memory's `sb_affect: {valence, arousal, emotion, intensity}` (already
  round-tripped through OKF files) now also populates a typed `affect` table
  (one row per affect-bearing Concept, `ON DELETE CASCADE`). New API:
  `SecondBrain.affect(id)` returns the typed dict (None when absent; NULL dims
  for partially-scored memories), and `SecondBrain.recall_by_affect(emotion=…,
  min_valence=…, max_valence=…, min_arousal=…, max_arousal=…, min_intensity=…)`
  answers categorical + numeric-range + combined queries, returning full
  Concepts ordered by intensity. New CLI: `brain recall-affect --emotion grief
  --min-intensity 0.7`; `brain add/update --affect '<json>'` to capture it;
  `brain show <id>` prints an affect line. The affect index is rebuilt from
  `concepts.metadata` by `bundle.rebuild()`, so it is correct after any
  files→DB rebuild with no separate state to keep aligned. 7 new unit tests;
  verifier `affect-persist` (corpus 15/15). This is the queryable foundation
  for emotional-mimic agents (Zep/Mem0-class affect recall).
  - Also fixed: `brain add --subject` was defined but silently ignored (the
    handler never forwarded it to `add()`); it now wires through, and
    `brain update` gained `--subject` / `--affect` (pass `""` to clear).
  - Known limitations: `recall_by_affect` exposes only exact emotion match
    (no fuzzy/semantic emotion grouping) and per-dimension AND-combined bounds
    (no OR across emotions in one call); valence/arousal/intensity are stored
    as given and not range-validated (a frontmatter `intensity: 5` persists
    verbatim); soft-deleted Concepts drop their affect row on rebuild (mirrors
    the subject index), so affect is restored from `metadata` only when the
    Concept is restored and re-indexed.

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


### Added
- **Subjects + persona sub-graph (R10 M1)** (R10 / G08, mochu iter-14) —
  every Concept now carries a subject via OKF frontmatter `sb_subject:
  /people/<slug>.md` (default `/people/self.md`). New SQLite tables
  `subjects(sb_id, slug, display_name, kind)` and
  `concept_subject(concept_id, subject_id)` are derived from concepts +
  Person Concepts at bundle-rebuild time (the DB stays disposable). New
  public API: `SecondBrain.subject_subgraph(path_or_slug)`, `subjects()`.
  New CLI: `brain recall-subject <path-or-name>` (e.g.
  `brain recall-subject rox`, `brain recall-subject /people/alex.md`).
  `add(title, content, collection, tags, sources, sb_subject=None)` and
  `update(...)` accept the new field; `update(sb_subject=None)` clears to
  default, missing-arg preserves. Person Concepts are the SUBJECT
  themselves, not members of their own sub-graph (Person = index entry;
  sub-graph = memories about them). commands/brain.md updated with
  `/brain recall <person>` → `brain recall-subject`. 6 new tests in
  tests/test_brain.py (51→57). New verifier `subject-subgraph` (14/14
  corpus). R10 M1 closed; R11 (temporal/--as-of), R12 (affect), and G08
  M2/M3 remain open.
  - Known limitations: `subjects()` returns a flat list (no facets/
    grouping); FK ON DELETE CASCADE is not set on concept_subject
    (hard-deleting a Person Concept leaves orphan rows until rebuild);
    `brain recall-subject` (CLI) and `/brain recall <person>` (slash
    command) don't match docs/04-psychological-memory.md's `/brain-recall`
    name yet — R15 (docs catch-up) is the right place to fix the doc
    shape, not here.
