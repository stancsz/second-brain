# Gap Register

Scored: score = impact × confidence / effort (each 1-5). Seeded from `docs/` build plan (Phases A–E)
plus competitive deltas. WIP preempts; cooldown excluded; verifiable gaps only.

## Active

| id | dimension | gap | evidence (observed) | impact | effort | confidence | score |
|---|---|---|---|---|---|---|---|
| G04 | features | Rename model `drawer`→`Concept` across schema/CLI/code per docs/02 | Code uses `drawers`/`drawer` throughout | 3 | 3 | 4 | 4.0 |
| G08 | features | Psychological schema: `sb_subject`/subjects table; memory `type` vocabulary | Research+docs identify this as the differentiator; nothing built | 5 | 4 | 4 | 5.0 |
| G09 | features | Temporal validity (`sb_valid_from/to`, `sb_supersedes`) + `--as-of` recall (Zep parity) | Zep/Graphiti v0.29.2 ships bi-temporal at MCP parity; we don't | 5 | 4 | 4 | 5.0 |
| G10 | features | Structured affect (`sb_affect`) + affect table | Needed for emotional mimic agents; not built | 4 | 3 | 4 | 5.33 |
| G11 | features | `Backend` interface + S3/GCS adapters (one-way mirror) | "any cloud db / s3 / gcs" requested; none exist | 4 | 4 | 4 | 4.0 |
| G12 | features | Google Drive / OneDrive backup adapters (MCP-first) | Requested; MCP connectors available in session | 4 | 4 | 3 | 3.0 |
| G13 | trust | Selective-by-tag encryption (age) for private/psych Concepts before push | Psych data would hit remotes in plaintext otherwise | 5 | 4 | 3 | 3.75 |
| G14 | docs | SKILL.md + README updated to OKF terminology & new capabilities | Build landed in iter-7 uncommitted (stashed as `iter-7 G14 build`); verifier G14 hardened in iter-7 | 3 | 2 | 4 | 6.0 |
| G15 | reliability | Hook + OS-scheduler install (`install.sh`) for scheduled sync | install.sh has no scheduler entry | 3 | 3 | 3 | 3.0 |
| G16 | performance | Incremental (mtime-based) rebuild for large Bundles | Full walk only; risk at scale | 2 | 3 | 3 | 2.0 |
| G17 | features | Migrate existing v2.1 brain.db → OKF Bundle (first real round-trip test) | Existing DBs must not be orphaned; G09 migration story must be back-compat | 4 | 3 | 4 | 5.33 |
| G18 | features | Mem0-style preference-consolidation (update existing memory on correction vs duplicate) | Mem0 OpenCode v0.2.0 (2026-06-17) ships gated auto-dream in production — concrete reference impl | 3 | 3 | 3 | 3.0 |
| G19 | reliability | ~~Recall hook misses morphological matches~~ RESOLVED as output-encoding crash (cp1252 swallowed emoji print → empty stdout) | hook now reconfigures stdout to UTF-8; recall block reaches the model under cp1252; filler still silent | 4 | 3 | 4 | 5.33 |
| G20 | trust | OKF spec conformance: verify `okf_version` lives in bundle-root `index.md` frontmatter, NOT as a separate file (per OKF v0.1 SPEC.md refetched iter-8) | Possible G03 regression — our G03 description names `okf_version` as if it's a file; spec says it's an `index.md` frontmatter key | 3 | 1 | 4 | 12.0 |

## Shipped
| id | dimension | shipped | note |
|---|---|---|---|
| G01 | features | iter-1 | OKF serializer `scripts/okf.py`; verifiers okf-roundtrip + okf-conformance. Cooldown until iter-7. |
| G02 | features | iter-2 | Bundle export/rebuild `scripts/bundle.py`; verifier bundle-rebuild. SQLite disposable. Cooldown until iter-8. |
| G03 | features | iter-3 | OKF reserved files in `bundle.export`; verifier index-log. Bundle OKF-conformant. Cooldown until iter-9. |
| G05 | features | iter-4 | Git sync spine `scripts/sync.py`; verifier git-sync. Multi-device portable. Cooldown until iter-10. |
| G07 | reliability | iter-5 | Tombstone deletes + incremental export `bundle.py`/`sync.py`; verifier tombstone. Cooldown until iter-11. |
| G06 | reliability | iter-6 | Conflict parking `sync.py` (conflicts()); verifier conflict. Cooldown until iter-12. |
| G19 | reliability | iter-7 | Recall hook UTF-8 stdout (cp1252 crash); verifier recall-encoding. Cooldown until iter-13. |

## Parked
_(none yet)_

## Notes & Detailed Research on Open Gaps

### G04: Rename model `drawer` → `Concept`
* **Method:** Run a migration query `ALTER TABLE drawers RENAME TO concepts` and update columns/FKs across the schema. Perform global refactoring in Python code (e.g. `SecondBrain` methods `add_drawer` → `add_concept`) and match CLI subcommands to avoid terminology collision.

### G08: Psychological Schema & Subjects
* **Method:** Add a `subjects` table: `id TEXT PRIMARY KEY, slug TEXT UNIQUE, display_name TEXT, kind TEXT`. Map OKF frontmatter `sb_subject: /people/<slug>.md` to `subject_id` as a foreign key on the `concepts` table.

### G09: Temporal Validity & Recall
* **Method:** Add bi-temporal columns (`valid_from`, `valid_to`, `supersedes_id` self-referential FK) on `concepts`. In `recall_memories.py`, add an `--as-of` query filter to retrieve only Concepts that were active at the specified historical moment.

### G10: Structured Affect
* **Method:** Create an `affect` table: `concept_id TEXT PRIMARY KEY, valence REAL, arousal REAL, emotion TEXT, intensity REAL` with a cascade delete. Parse `sb_affect` mapping in `okf.py` to populate this metadata.

### G11: Cloud Backup Adapters (S3/GCS)
* **Method:** Define a `BackupAdapter` ABC interface. Write lazy-imported S3 (`boto3`) and GCS (`google-cloud-storage`) adapters that push exported OKF Bundle directory files as a one-way mirror.

### G12: Google Drive / OneDrive Adapters
* **Method:** Implement an MCP-first approach. Rather than managing OAuth credentials inside local python standard library scripts, configure an external GDrive/OneDrive MCP server to write/sync files.

### G13: Selective-by-Tag Encryption
* **Method:** Use `age` encryption tool or standard Python `cryptography` to selectively encrypt the frontmatter fields and body of files tagged with `private` or `psych` before Git commit, keeping public files plaintext for clean git diffs.

### G14: Capability Documentation Update
* **Method:** Refactor `SKILL.md` and `README.md` to OKF terminology. Document psychological traits, sync spines, and conflict management to reflect the new capabilities.

### G15: Hook & OS Scheduler Integration
* **Method:** Extend `install.sh` to configure cron jobs (Linux/macOS) or Windows Task Scheduler (`schtasks.exe`) to execute `scripts/sync.py` periodically (e.g., hourly).

### G16: Incremental Rebuild Performance
* **Method:** Store file modification times (`mtime`) and hashes in a new `_import_meta` table. Rebuild only parses changed files and deletes records of deleted files instead of executing a full database wipe.

### G17: Migration path v2.1 → OKF
* **Method:** Write a migration script that reads legacy `brain.db` schemas, parses old metadata configurations, runs `bundle.export` to serialize existing content to OKF markdown, and bootstraps the new database schema.

### G18: Preference Consolidation (Mem0 Parity)
* **Method:** Use LLM-in-the-loop during the distillation phase to query the database for existing conflicting Concepts. If found, mark the older Concept's `sb_valid_to` as active and write the new one with a `sb_supersedes` link.

### G20: OKF Spec Conformance (okf_version)
* **Method:** Ensure `bundle.py` writes the `okf_version: "0.1"` directly inside the root `index.md`'s frontmatter block and ensure that the parser skips index/log documents when importing.
