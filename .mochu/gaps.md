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
| G14 | docs | SKILL.md + README updated to OKF terminology & new capabilities | SHIPPED iter-9 | 3 | 2 | 4 | 6.0 |
| G15 | reliability | Hook + OS-scheduler install (`install.sh`) for scheduled sync | install.sh has no scheduler entry | 3 | 3 | 3 | 3.0 |
| G16 | performance | Incremental (mtime-based) rebuild for large Bundles | Full walk only; risk at scale | 2 | 3 | 3 | 2.0 |
| G17 | features | Migrate existing v2.1 brain.db → OKF Bundle (first real round-trip test) | Existing DBs must not be orphaned; G09 migration story must be back-compat | 4 | 3 | 4 | 5.33 |
| G18 | features | Mem0-style preference-consolidation (update existing memory on correction vs duplicate) | Mem0 OpenCode v0.2.0 (2026-06-17) ships gated auto-dream in production — concrete reference impl | 3 | 3 | 3 | 3.0 |
| G19 | reliability | ~~Recall hook misses morphological matches~~ RESOLVED as output-encoding crash (cp1252 swallowed emoji print → empty stdout) | hook now reconfigures stdout to UTF-8; recall block reaches the model under cp1252; filler still silent | 4 | 3 | 4 | 5.33 |
| G20 | trust | OKF spec conformance: verify `okf_version` lives in bundle-root `index.md` frontmatter, NOT as a separate file (per OKF v0.1 SPEC.md refetched iter-8) | SHIPPED iter-10 | 3 | 1 | 4 | 12.0 |
| G21 | docs | README.zh.md parity for G14 — translate OKF v0.1, Concept (概念), git-sync, psychological-memory sections to Chinese | README.zh.md still says "笔记(Drawer)", "5 万条笔记" and does not mention OKF/sync/psych | 3 | 2 | 4 | 6.0 |

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
| G14 | docs | iter-9 | README/SKILL OKF terminology, multi-device sync, psychological-memory foundation documented; verifier docs-okf (hardened iter-7 with cp1252 fix iter-8). Cooldown until iter-15. |
| G20 | trust | iter-10 | OKF v0.1 spec-shape verifier (okf_version placement, subdir-index frontmatter absence, every concept has type, no concept has okf_version); code was already spec-compliant. Cooldown until iter-16. |

## Parked
_(none yet)_

## Notes & Detailed Research on Open Gaps

### G04: Rename model `drawer` → `Concept`
* **Method:** Run a migration query `ALTER TABLE drawers RENAME TO concepts` and update columns/FKs across the schema. Perform global refactoring in Python code (e.g. `SecondBrain` methods `add_drawer` → `add_concept`) and match CLI subcommands to avoid terminology collision.
* **Agent Build Rationale:** Excellent for agents because it is a deterministic, highly verifiable text-replacement and schema migration task. The agent can easily use `grep` to ensure 100% coverage across the repository without requiring subjective design decisions.

### G08: Psychological Schema & Subjects
* **Method:** Add a `subjects` table: `id TEXT PRIMARY KEY, slug TEXT UNIQUE, display_name TEXT, kind TEXT`. Map OKF frontmatter `sb_subject: /people/<slug>.md` to `subject_id` as a foreign key on the `concepts` table.
* **Agent Build Rationale:** The schema is explicitly defined and localized to `schema.sql` and `okf.py`. An agent can build this autonomously because the data model mapping (frontmatter → JSON → SQL) follows the exact same established pattern as existing fields.

### G09: Temporal Validity & Recall
* **Method:** Add bi-temporal columns (`valid_from`, `valid_to`, `supersedes_id` self-referential FK) on `concepts`. In `recall_memories.py`, add an `--as-of` query filter to retrieve only Concepts that were active at the specified historical moment.
* **Agent Build Rationale:** This relies entirely on standard SQL `WHERE` clauses and explicit schema updates. It is highly testable for an agent: the agent can write a unit test to insert historical records and verify the `--as-of` filter correctly excludes expired ones.

### G10: Structured Affect
* **Method:** Create an `affect` table: `concept_id TEXT PRIMARY KEY, valence REAL, arousal REAL, emotion TEXT, intensity REAL` with a cascade delete. Parse `sb_affect` mapping in `okf.py` to populate this metadata.
* **Agent Build Rationale:** Clear, bounded database work. The agent only needs to implement a single new table and wire up the parser, which is easy to verify via a simple Python integration test asserting that the dictionary round-trips correctly.

### G11: Cloud Backup Adapters (S3/GCS)
* **Method:** Define a `BackupAdapter` ABC interface. Write lazy-imported S3 (`boto3`) and GCS (`google-cloud-storage`) adapters that push exported OKF Bundle directory files as a one-way mirror.
* **Agent Build Rationale:** By keeping the interface as a strict one-way mirror (upload only), we eliminate complex synchronization state logic. An agent can easily mock the `boto3` or `google-cloud-storage` SDKs to verify the interface without needing live cloud credentials.

### G12: Google Drive / OneDrive Adapters
* **Method:** Implement an MCP-first approach. Rather than managing OAuth credentials inside local python standard library scripts, configure an external GDrive/OneDrive MCP server to write/sync files.
* **Agent Build Rationale:** Building OAuth flows is notoriously difficult for agents due to browser redirects. By offloading this to an MCP connector, the agent's task is reduced to simple RPC calls (which agents excel at) rather than managing complex authentication states.

### G13: Selective-by-Tag Encryption
* **Method:** Use `age` encryption tool or standard Python `cryptography` to selectively encrypt the frontmatter fields and body of files tagged with `private` or `psych` before Git commit, keeping public files plaintext for clean git diffs.
* **Agent Build Rationale:** The logic is purely functional: if `tag == 'private'`, apply encryption function before writing. An agent can build and verify this completely locally using temporary keys, ensuring no regression on plaintext files.

### G14: Capability Documentation Update
* **Method:** Refactor `SKILL.md` and `README.md` to OKF terminology. Document psychological traits, sync spines, and conflict management to reflect the new capabilities.
* **Agent Build Rationale:** Agents are uniquely strong at documentation updates. Provided with the locked architecture docs, the agent can accurately propagate terminology changes across the user-facing documentation without needing complex environmental setup.

### G15: Hook & OS Scheduler Integration
* **Method:** Extend `install.sh` to configure cron jobs (Linux/macOS) or Windows Task Scheduler (`schtasks.exe`) to execute `scripts/sync.py` periodically (e.g., hourly).
* **Agent Build Rationale:** Writing shell scripts to append to `crontab` or invoke `schtasks` is a well-understood, discrete task. It avoids modifying core Python logic and restricts the agent's surface area to a single bash script.

### G16: Incremental Rebuild Performance
* **Method:** Store file modification times (`mtime`) and hashes in a new `_import_meta` table. Rebuild only parses changed files and deletes records of deleted files instead of executing a full database wipe.
* **Agent Build Rationale:** Excellent for agents as it relies on deterministic filesystem properties (`os.path.getmtime`). The agent can easily write a test script that touches a file, runs rebuild, and verifies that only the touched file was parsed.

### G17: Migration path v2.1 → OKF
* **Method:** Write a migration script that reads legacy `brain.db` schemas, parses old metadata configurations, runs `bundle.export` to serialize existing content to OKF markdown, and bootstraps the new database schema.
* **Agent Build Rationale:** Agents excel at writing translation scripts between two known schemas. Because both the legacy and target schemas are strictly defined in `schema.sql`, the agent can write an automated verification suite to prove zero data loss during migration.

### G18: Preference Consolidation (Mem0 Parity)
* **Method:** Use LLM-in-the-loop during the distillation phase to query the database for existing conflicting Concepts. If found, mark the older Concept's `sb_valid_to` as active and write the new one with a `sb_supersedes` link.
* **Agent Build Rationale:** This leverages the core strength of the LLM itself. The agent only needs to write the prompt and retrieval plumbing to allow the runtime agent to perform semantic deduplication, cleanly separating the plumbing task from the semantic reasoning task.

### G20: OKF Spec Conformance (okf_version)
* **Method:** Ensure `bundle.py` writes the `okf_version: "0.1"` directly inside the root `index.md`'s frontmatter block and ensure that the parser skips index/log documents when importing.
* **Agent Build Rationale:** Highly constrained bug fix. The agent merely needs to adjust string formatting in `bundle.py` and add an `if file == 'index.md'` check in the parser, which is immediately verifiable against the OKF specification.
