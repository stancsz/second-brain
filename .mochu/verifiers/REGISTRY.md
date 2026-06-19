# Verifier Registry — the ratchet (append-only)

Index of every verifier in the corpus. The full corpus must stay green every iteration.
Run all via `python3 scripts/run_corpus.py`.

| id | dimension | claim | run command | added |
|---|---|---|---|---|
| okf-roundtrip | features | Concept ⇄ OKF markdown round-trips losslessly across all fields incl. sb_* | `python .mochu/verifiers/G01/verify_roundtrip.py` | iter-1 |
| okf-conformance | features | Every emitted Concept document conforms to OKF v0.1 §9 (non-empty type, frontmatter, path↔id, citations) | `python .mochu/verifiers/G01/verify_conformance.py` | iter-1 |
| bundle-rebuild | features | Export→rebuild reproduces a fresh brain.db losslessly (drawers, tags, sources, relations, soft-delete, FTS) — SQLite is disposable | `python .mochu/verifiers/G02/verify_rebuild.py` | iter-2 |
| index-log | features | Exported Bundle has conformant OKF reserved files (root+subdir index.md, log.md, okf_version pin) and still rebuilds | `python .mochu/verifiers/G03/verify_index_log.py` | iter-3 |
| git-sync | features | sync() round-trips memory across two devices via a git remote (serialize→commit→pull→push→rebuild); converges; no-op resync clean | `python .mochu/verifiers/G05/verify_git_sync.py` | iter-4 |
| tombstone | reliability | Deletes propagate over git: soft-delete->.trash tombstone, restore reverses, hard-delete removes file with no resurrection | `python .mochu/verifiers/G07/verify_tombstone.py` | iter-5 |
| conflict | reliability | Concurrent same-concept edits park as *.conflict.md (no crash, no clobber, clean tree, single canonical import) | `python .mochu/verifiers/G06/verify_conflict.py` | iter-6 |
