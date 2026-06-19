# Gap Register

Scored: score = impact × confidence / effort (each 1-5). Seeded from `docs/` build plan (Phases A–E)
plus competitive deltas. WIP preempts; cooldown excluded; verifiable gaps only.

## Active

| id | dimension | gap | evidence (observed) | impact | effort | confidence | score |
|---|---|---|---|---|---|---|---|
| G04 | features | Rename model `drawer`→`Concept` across schema/CLI/code per docs/02 | Code uses `drawers`/`drawer` throughout | 3 | 3 | 4 | 4.0 |
| G08 | features | Psychological schema: `sb_subject`/subjects table; memory `type` vocabulary | Research+docs identify this as the differentiator; nothing built | 5 | 4 | 4 | 5.0 |
| G09 | features | Temporal validity (`sb_valid_from/to`, `sb_supersedes`) + `--as-of` recall (Zep parity) | Zep/Graphiti have it; we don't; docs/04 specs it | 5 | 4 | 4 | 5.0 |
| G10 | features | Structured affect (`sb_affect`) + affect table | Needed for emotional mimic agents; not built | 4 | 3 | 4 | 5.33 |
| G11 | features | `Backend` interface + S3/GCS adapters (one-way mirror) | "any cloud db / s3 / gcs" requested; none exist | 4 | 4 | 4 | 4.0 |
| G12 | features | Google Drive / OneDrive backup adapters (MCP-first) | Requested; MCP connectors available in session | 4 | 4 | 3 | 3.0 |
| G13 | trust | Selective-by-tag encryption (age) for private/psych Concepts before push | Psych data would hit remotes in plaintext otherwise | 5 | 4 | 3 | 3.75 |
| G14 | docs | SKILL.md + README updated to OKF terminology & new capabilities | Docs still describe SQLite-only drawer model | 3 | 2 | 4 | 6.0 |
| G15 | reliability | Hook + OS-scheduler install (`install.sh`) for scheduled sync | install.sh has no scheduler entry | 3 | 3 | 3 | 3.0 |
| G16 | performance | Incremental (mtime-based) rebuild for large Bundles | Full walk only; risk at scale | 2 | 3 | 3 | 2.0 |
| G17 | features | Migrate existing v2.1 brain.db → OKF Bundle (first real round-trip test) | Existing DBs must not be orphaned | 4 | 3 | 4 | 5.33 |
| G18 | features | Mem0-style preference-consolidation (update existing memory on correction vs duplicate) | Competitive delta vs Mem0; future | 3 | 4 | 2 | 1.5 |
| G19 | reliability | Recall hook misses morphological matches — FTS has no stemming, so prompt "timing out" doesn't match stored "timeout" | `tests/test_recall_hook.py::test_relevant_prompt_injects_context` fails on clean HEAD (pre-existing); recall injects nothing | 4 | 3 | 4 | 5.33 |

## Shipped
| id | dimension | shipped | note |
|---|---|---|---|
| G01 | features | iter-1 | OKF serializer `scripts/okf.py`; verifiers okf-roundtrip + okf-conformance. Cooldown until iter-7. |
| G02 | features | iter-2 | Bundle export/rebuild `scripts/bundle.py`; verifier bundle-rebuild. SQLite disposable. Cooldown until iter-8. |
| G03 | features | iter-3 | OKF reserved files in `bundle.export`; verifier index-log. Bundle OKF-conformant. Cooldown until iter-9. |
| G05 | features | iter-4 | Git sync spine `scripts/sync.py`; verifier git-sync. Multi-device portable. Cooldown until iter-10. |
| G07 | reliability | iter-5 | Tombstone deletes + incremental export `bundle.py`/`sync.py`; verifier tombstone. Cooldown until iter-11. |
| G06 | reliability | iter-6 | Conflict parking `sync.py` (conflicts()); verifier conflict. Cooldown until iter-12. |

## Parked
_(none yet)_

## Notes
- Natural build order is the docs Phase A→E sequence: G01/G02/G03/G04 (Phase A) → G05/G06/G07 (B) →
  G08/G09/G10 (C) → G11/G12/G13 (D) → G14/G15/G16/G17 (E). Scores will re-rank as dependencies clear.
- G02 scores highest but **depends on G01** (need a serializer before you can rebuild from files).
  Treat G01→G02→G03→G04 as the Phase-A milestone chain.
