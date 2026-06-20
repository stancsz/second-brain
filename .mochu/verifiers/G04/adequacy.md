# G04 M1 — Verifier Adequacy Audit

Claim under test: R4 / G04 M1 — the SQLite schema uses `concepts` (not
`drawers`) as the canonical table name, and any v2.1 brain.db (with a
`drawers` table) auto-migrates to `concepts` on first open via
`SecondBrain`, preserving rows + FTS5 index + trigger behavior.

## Three lazy artifacts (summary list)

1. **No-op rename.** A verifier that asserts "drawer" doesn't appear in
   the schema.sql text, but the actual SQLite still has the `drawers`
   table at runtime. Schema-as-text-only, not schema-as-runtime.
2. **Half-migration.** A migration that renames the table but leaves the
   FTS5 virtual table pointing at the old name, or leaves the old
   triggers firing on the new table name with stale SQL bodies.
   Search-after-migration returns empty.
3. **Data loss.** A migration that renames the table but loses rows
   (e.g., drops the table, creates empty new one, forgets to copy data).
   Or: a migration that renames the table but breaks the `concept_tags`
   FK so cascading delete no longer works.

## How the suite blocks each

- **Artifact 1 (no-op).** The verifier drives `SecondBrain(db_path)` and
  then inspects `sqlite_master` in the LIVE connection. It doesn't
  read schema.sql; it checks what the database engine actually
  contains. Renaming schema.sql text without changing what the
  connection produces would still fail the verifier.
- **Artifact 2 (half-migration).** The verifier inserts a row with a
  canary word BEFORE migration (via raw `drawers` INSERT in the v2.1
  pre-population step), runs the migration, and asserts the canary
  word is findable via FTS5 search (`b.search("legacy_canary_word_42")`).
  It also adds a NEW row AFTER migration and asserts that row's canary
  word is findable — proving the new triggers fire on the new table
  name. The half-migration failure mode (FTS5 not rebuilt, or triggers
  still on the old name) is caught by either check.
- **Artifact 3 (data loss / FK break).** The verifier asserts the
  post-migration row count matches the pre-migration row count (2
  rows). The `check_fk_cascade()` test inserts a concept with 2 tags,
  hard-deletes the concept, and asserts `concept_tags` rows are gone
  — proving the FK + CASCADE survived the rename.

## Strongest-pattern check

- **EXEC (not grep).** The verifier runs `SecondBrain(db_path)` end-to-end
  and inspects `sqlite_master` of the resulting connection. It does
  not call internals like `_ensure_schema()` directly, and it does
  not grep source code. The assertions are anchored to the public API
  contract, not the implementation.
- **Discrimination proof (run on pre-work tree).** The verifier is
  RED right now: opening a fresh DB produces a connection with
  `['drawers', 'tags', 'drawer_tags', ...]` — exactly the table list
  the post-rename code must NOT produce. The pre-work tree is the
  proof that the verifier discriminates.
- **Coverage.** Three sub-checks: (a-c) fresh-DB invariants, (d-g)
  v2.1 migration invariants, (g-extra) FK cascade. All three are
  independent — a regression in any one is caught by its own check.

## Out of scope (own gaps, not M1)

- **brain_cli.py / bundle.py / sync.py / hooks / tests renaming.**
  Those are M2 and M3 (per `.mochu/wip/G04.md`). The CLI still says
  "drawer" in this iteration; the table is `concepts` underneath. The
  verifier doesn't test the CLI surface — M2's verifier does.
- **docs/ / references/ / commands/ renaming.** M3.
- **Behavior at scale (millions of rows).** The migration does an
  `ALTER TABLE RENAME` (O(1) metadata change) + FTS5 rebuild (O(N)
  index walk). For a 10K-row brain.db this is sub-second. The
  verifier doesn't benchmark — that's G16's scope.
- **Rollback.** A failed migration leaves the DB in a partially
  renamed state. We don't currently support a "down" migration; if
  R4 ships and a user wants to go back to v2.1, they have to keep
  a backup. This is documented in the iter-12 limitations, not
  addressed in M1.
