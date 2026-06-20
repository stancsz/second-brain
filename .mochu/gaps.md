# Gap Register

Scored: score = impact × confidence / effort (each 1-5). Seeded from `docs/` build plan (Phases A–E)
plus competitive deltas. WIP preempts; cooldown excluded; verifiable gaps only.

## Active

| id | dimension | gap | evidence (observed) | impact | effort | confidence | score |
|---|---|---|---|---|---|---|---|
| G08 | features | Psychological schema: `sb_subject`/subjects table; memory `type` vocabulary | M1 SHIPPED iter-14 (subjects + concept_subject + subject_subgraph + subjects() + CLI + 6 tests + verifier); R10 satisfied, M2/M3 are non-release enhancements (grouping, FK cascade, humanization) | 3 | 4 | 4 | 3.0 |
| G11 | features | `Backend` interface + S3/GCS adapters (one-way mirror) | "any cloud db / s3 / gcs" requested; none exist | 4 | 4 | 4 | 4.0 |
| G12 | features | Google Drive / OneDrive backup adapters (MCP-first) | Requested; MCP connectors available in session | 4 | 4 | 3 | 3.0 |
| G13 | trust | Selective-by-tag encryption (age) for private/psych Concepts before push | Psych data would hit remotes in plaintext otherwise | 5 | 4 | 3 | 3.75 |
| G15 | reliability | Hook + OS-scheduler install (`install.sh`) for scheduled sync | install.sh has no scheduler entry | 3 | 3 | 3 | 3.0 |
| G16 | performance | Incremental (mtime-based) rebuild for large Bundles | Full walk only; risk at scale | 2 | 3 | 3 | 2.0 |
| G17 | features | Migrate existing v2.1 brain.db → OKF Bundle (first real round-trip test) | Existing DBs must not be orphaned; G09 migration story must be back-compat | 4 | 3 | 4 | 5.33 |
| G18 | features | Mem0-style preference-consolidation (update existing memory on correction vs duplicate) | Mem0 OpenCode v0.2.0 (2026-06-17) ships gated auto-dream in production — concrete reference impl | 3 | 3 | 3 | 3.0 |
| G19 | reliability | ~~Recall hook misses morphological matches~~ RESOLVED as output-encoding crash (cp1252 swallowed emoji print → empty stdout) | hook now reconfigures stdout to UTF-8; recall block reaches the model under cp1252; filler still silent | 4 | 3 | 4 | 5.33 |
| G21 | docs | README.zh.md parity for G14 — translate OKF v0.1, Concept (概念), git-sync, psychological-memory sections to Chinese | README.zh.md still says "笔记(Drawer)", "5 万条笔记" and does not mention OKF/sync/psych | 3 | 2 | 4 | 6.0 |
| G24 | docs | Untracked docs/ files (08-iter7-findings, HANDOFF, brief, decisions/D001, tasks/T002) still have `drawer` refs | docs-surface-rename verifier scopes to git-tracked files; these are untracked | 2 | 1 | 4 | 8.0 |
| G25 | features | Graph-aware search ranking — re-rank FTS hits by relation-graph proximity (boost concepts linked to other strong hits / a seed) | Observed iter-16: `brain.search()` uses `ORDER BY rank` (FTS5 BM25) ONLY; the `relations` graph never influences ranking. Mem0's 2026 retrieval fuses keyword + entity-match; we have the graph but don't use it at rank time. Achievable dependency-free (traversal over existing `relations`); a semantic-embedding signal would break stdlib-only and belongs in an optional adapter, NOT this gap | 3 | 2 | 4 | 6.0 |
| G26 | reliability | ISO date validation on `valid_from`/`valid_to` — currently stored as opaque strings; a malformed date silently sorts wrong without error | Reviewer feedback iter-14–17: `supersede()` and `_normalize_validity()` accept any string for `valid_from`/`valid_to`; `datetime.date.fromisoformat` raises on malformed input but is never called. Lexicographic comparison breaks silently on "June 2023" or "2023/06/01" | 3 | 1 | 5 | 15.0 |
| G27 | reliability | Soft-delete → restore must recover all psych dims (affect + subject) intact | Reviewer feedback iter-14–17: `restore()` undeletes the concept but the `affect` and `concept_subject` derived-index rows were wiped by the soft-delete rebuild pass. Those rows are re-populated only on the next `bundle.rebuild()`. An explicit test (add → affect+subject → soft-delete → restore → assert) and a `restore()`-time re-sync of derived indexes is needed | 4 | 2 | 4 | 8.0 |
| G28 | reliability | CLI error boundary — all CLI entry points yield clean actionable messages on bad input, not raw stack traces | Reviewer feedback iter-14–17: `--affect` was fixed (iter-15 `_parse_affect_arg`), but `--valid-from`/`--valid-to` with non-ISO strings, `--supersedes` with a non-existent id, and other flags can still dump raw Python exceptions. A validation pass at the CLI boundary before delegating to brain.py | 3 | 2 | 4 | 6.0 |
| G29 | features | Optional semantic (vector) search via `sqlite-vec` lazy adapter; FTS5 fallback when the extension is absent (R16, ratified) | Competitive #1 behind-gap (iter-18 intel): all of Mem0/Zep/LangMem do vector recall; we do FTS5 keyword only — "performance tuning" misses a note titled "optimizing code". MUST be optional+lazy+fallback to preserve the zero-dependency moat | 5 | 4 | 3 | 3.75 |
| G30 | features | Generic MCP server exposing the brain (search/add/recall-as-of/recall-affect/recall-subject as MCP tools) (R17, ratified) | Competitive ecosystem-gap (iter-18 intel): competitors ship native SDK wrappers for LangChain/AutoGen/LlamaIndex; we are CLI + Claude-skill only. An MCP server lets ANY framework hook in with zero bespoke glue | 4 | 3 | 4 | 5.33 |
| G31 | features | Agent-side opt-in auto entity/relationship extraction (distillation proposes `[[links]]` + subjects from raw text) | Competitive parity (iter-18 intel): Mem0/Zep use background LLMs to distill entities + draw graphs; we rely on explicit `/brain add` + manual `[[wikilinks]]`. Keep LLM calls AGENT-side/opt-in so the core stays dep-free and fast | 3 | 4 | 3 | 2.25 |

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
| G22 | trust | iter-11 | R14 secret-history + config-shape secret scan (15,804 history lines + tracked *.toml/*.ini/*.yaml/*.yml/*.env; 0 leaks); 0 config files in this repo, the sync.toml half of R14 is locked in for when the config exists. Cooldown until iter-17. |
| G04 | features | iter-12 | Schema + code rename `drawers`→`concepts` (M1+M2 of R4): schema.sql v3.0, brain.py uses concept/concepts everywhere except intentional old-name references in `_migrate_v21_to_concepts()`, brain_cli.py/bundle.py/sync.py/capture_conversation.py/recall_memories.py/test_brain.py/test_capture_hook.py/test_recall_hook.py all use new vocabulary. Auto-migration of v2.1 brain.db in-place (table rename + FTS5 rebuild + trigger replacement). Verifier schema-rename (red→green; 8 sub-checks). 51/51 test_brain.py tests pass; full mochu corpus 12/12 green; ship_gate PASS. Cooldown until iter-18. |
| G23 | docs | iter-13 | R4 M3 (docs surface rename) done: 9 tracked files renamed across commands/, docs/, references/, README.zh.md. Total 59 hits. `docs/02-okf-and-terminology.md` comparison table restructured (was showing "Old: drawer → New: Concept" — after rename, the old column said the same as the new, which would silently mislead readers; now describes current canonical state with historical context in prose). `references/architecture.md` title updated v2.1 → v3.0 to match the body (body now describes v3.0 schema). `docs-surface-rename` verifier: 13 in-scope files scanned, 0 residual hits. corpus 13/13 green; ship_gate PASS; R4 complete. Cooldown until iter-19. |
| G08 | features | iter-14 | R10 satisfied (M1): subjects + concept_subject + subject_subgraph() + subjects() + recall-subject CLI; M2/M3 (grouping, humanization) are non-release enhancements. Cooldown until iter-20. |
| G10 | features | iter-15 | R12 satisfied: typed `affect` table (valence/arousal/emotion/intensity, FK ON DELETE CASCADE) populated by bundle.rebuild + live add/update; `affect(id)` getter + `recall_by_affect()` categorical/range/combined queries; `brain recall-affect` CLI + `--affect` capture; show prints affect. Fixed latent G08 bug (`add --subject` defined-but-unwired). Verifier affect-persist (corpus 15/15); 7 new tests (116→123). Cooldown until iter-21. |
| G09 | features | iter-17+18 | R11 satisfied (2 milestones): M1 (iter-17) = `validity` table + `supersede()` write-path, history-preserving, `brain show` window, verifier temporal-validity. M2 (iter-18) = `recall_as_of()` + `brain recall --as-of` CLI + verifier temporal-asof (17/17 corpus, 137 pytest). Cooldown until iter-24. |

## Parked
_(none yet)_

## Notes & Detailed Research on Open Gaps

### G04: Rename model `drawer` → `Concept`
* **Method:** Run a migration query `ALTER TABLE drawers RENAME TO concepts` and update columns/FKs across the schema. Perform global refactoring in Python code (e.g. `SecondBrain` methods `add_drawer` → `add_concept`) and match CLI subcommands to avoid terminology collision.
* **Agent Build Rationale:** Excellent for agents because it is a deterministic, highly verifiable text-replacement and schema migration task. The agent can easily use `grep` to ensure 100% coverage across the repository without requiring subjective design decisions.

### G08: Psychological Schema & Subjects — **M1 SHIPPED iter-14, M2/M3 OPEN**
* **Method:** Add a `subjects` table: `sb_id TEXT PRIMARY KEY, slug TEXT UNIQUE, display_name TEXT, kind TEXT` and a `concept_subject(concept_id, subject_id)` join table. Map OKF frontmatter `sb_subject: /people/<slug>.md` to the join row. Defaults: missing sb_subject → `/people/self.md`; Person Concept → its own path (and not a member of its own sub-graph — Person IS the subject).
* **M1 SHIPPED iter-14:** schema, rebuild_subject_index, subject_subgraph(), subjects(), `add(sb_subject=...)` / `update(sb_subject=...)` (None clears, missing-arg preserves), `brain recall-subject <path-or-name>` CLI, 6 new tests (51→57), `subject-subgraph` verifier (14/14 corpus).
* **M2 (TBD):** Tighter `subjects()` (grouped by collection / has-personas), display-name humanization, FK ON DELETE CASCADE for concept_subject.
* **M3 (TBD):** `RecallHook`/cron: when a new Concept has `sb_subject: /people/X.md`, propose (auto? interactive?) creating the Person Concept if it doesn't exist yet — closes the "forward refs safe but ghost subjects linger" gap.

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

### G25: Graph-aware search ranking (logged iter-16 recon)
* **Observed:** `brain.py:search()` is `SELECT ... FROM concepts_fts ... ORDER BY rank LIMIT ?` — pure FTS5 BM25. The `relations` graph (wikilinks + manual edges) and `traverse()` exist but are never consulted at rank time. Mem0's 2026 OSS retrieval fuses keyword + entity-match into one score; SecondBrain has the richer graph but doesn't use it to rank.
* **Method (dependency-free):** Keep FTS5 as the candidate generator; after fetching the top-N FTS hits, compute a graph-proximity boost — e.g. a hit linked (1–2 hops over `relations`) to other hits in the same result set, or to an optional `--seed <id>`, gets its score lifted. Re-rank in Python. No embeddings, no new deps. Expose as `search(..., boost_graph=True)` or a `--rerank` flag; default behavior unchanged unless opted in (so existing search-dependent verifiers stay green).
* **Verifier sketch:** Build a brain where concept A and B both weakly match a query, A is graph-linked to a strong hit C (also matching) and B is isolated; assert that with graph-boost on, A ranks above B, and with it off, the BM25 order is preserved. Discriminates a real re-rank from a no-op.
* **NOT in scope:** semantic/embedding similarity (breaks stdlib-only core; would be an optional lazy-imported adapter, a separate gap → now logged as G29).

### G26: ISO date validation on validity windows (review feedback iter-14–17)
* **Method:** Guard `_normalize_validity()` and `supersede()` with `datetime.date.fromisoformat` (accept date AND full ISO datetime). Raise `ValueError` with an actionable message on malformed input. In `bundle.rebuild` / `rebuild_validity_index`, a malformed `sb_valid_from/to` in `concepts.metadata` must be QUARANTINED (skip the row + log), NOT crash the whole rebuild — existing OKF files may already carry a bad string.
* **Verifier sketch:** malformed strings (`"June 2023"`, `"2023/06/01"`, `"2023-13-01"`) → clean `ValueError`, not silent store; valid ISO date + datetime → stored; a metadata row with a bad date → rebuild quarantines it and the rest of the index is intact.

### G27: Soft-delete → restore recovers psych dims (review feedback iter-14–17)
* **Method:** `restore()` must re-sync the derived indexes from the restored concept's `metadata` JSON: call `_sync_affect_for`, `_sync_subject_for`, `_sync_validity_for`. Currently `restore()` only un-sets `deleted_at` + re-resolves wikilinks; the affect/subject/validity rows were dropped and only return on the next full `bundle.rebuild()`.
* **Verifier sketch:** add concept w/ affect+subject+validity → soft-delete → (assert rows dropped) → restore → assert `affect(id)`, `subject_subgraph(path)`, `validity(id)` all return the original data WITHOUT a rebuild.

### G28: CLI error boundary (review feedback iter-14–17)
* **Method:** A validation/error wrapper at every CLI subcommand boundary so malformed input (`--valid-from "bad"`, `--supersedes <ghost-id>`, out-of-range affect JSON) yields a one-line actionable message + exit 1, never a Python traceback. The `--affect` path (`_parse_affect_arg`, iter-15) is the template to generalize.
* **Verifier sketch:** subprocess-drive each bad-input flag → assert exit 1, a human-readable message on stderr, and ZERO `Traceback (most recent call last)` in output.

### G29: Optional semantic search via sqlite-vec (R16, ratified)
* **Architectural constraint (LOCKED):** `sqlite-vec` is an OPTIONAL, lazy-imported adapter. Default `search()` stays FTS5. A `--semantic` path tries to load the extension; if it cannot load, it FALLS BACK to FTS5 and returns results, never crashes. This preserves the zero-dependency / air-gapped moat.
* **Method:** lazy `import sqlite_vec` + `vec0` virtual table holding embeddings (embeddings themselves produced agent-side / by an optional local model, NOT in the stdlib core). `search(query, semantic=True)` does ANN over the vec table, falls back to FTS5 on any import/load failure.
* **Verifier sketch (BOTH legs mandatory):** (1) extension present → a query whose synonym (not literal term) matches a concept is recalled (FTS5 alone would miss it); (2) extension absent/unloadable → `search(semantic=True)` returns FTS5 results with ZERO traceback. Leg (2) is the moat-protecting check and is first-class, not optional.

### G30: Generic MCP server (R17, ratified)
* **Method:** an MCP server (stdio) exposing the brain's read/write surface as tools: `search`, `add`, `recall_as_of`, `recall_affect`, `recall_subject`, `show`, `related`. Thin wrapper over `brain.py` — no new business logic. Lazy-import the MCP SDK so the core CLI never depends on it.
* **Verifier sketch:** start the server as a subprocess, perform an MCP handshake, call each tool with a known fixture brain, assert structured results match the equivalent `brain.py` call. Discriminates a real protocol server from a stub.

### G31: Agent-side auto entity/relationship extraction
* **Method:** during distillation (agent-side, opt-in), an LLM proposes `[[wikilinks]]` + `sb_subject` assignments from raw conversational text; the human/agent confirms before write. Keep ALL LLM calls outside the core — the plumbing (prompt + retrieval + apply-confirmed-edits) is the gap, the reasoning is the runtime model's job (mirrors G18's separation).
* **Verifier sketch:** given a transcript fixture + a stubbed/frozen extraction response, assert the proposed links/subjects are applied to the right concepts and that nothing is written without the confirm step.
