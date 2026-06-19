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
| recall-encoding | reliability | Proactive recall hook emits its block (incl. unicode) under a cp1252 stdout; filler prompts stay silent | `python .mochu/verifiers/G19/verify_recall.py` | iter-7 |
| docs-okf | docs | README.md and SKILL.md updated with OKF terminology (Concept, Bundle, sync); psychological memory mentioned | `python .mochu/verifiers/G14/verify_docs.py` | iter-7 |
| okf-spec-conformance | trust | Exported Bundle conforms to OKF v0.1 spec: `okf_version` lives in bundle-root `index.md` frontmatter (not a separate file); subdir indexes carry no frontmatter; every Concept has non-empty `type`; no Concept frontmatter contains `okf_version`; rebuild pre-condition | `python .mochu/verifiers/G20/verify_okf_spec_conformance.py` | iter-10 |
| secret-history | trust | R14 satisfied: no secret-shaped strings (AWS / GitHub / OpenAI / Anthropic / Slack / Google / PEM) in `git log --all -p`; no inline `password=...` / `api_key=...` in tracked `*.toml/*.ini/*.yaml/*.yml/*.env` (env-var refs `$VAR` / `{{var}}` skipped) | `python .mochu/verifiers/G22/verify_no_secrets.py` | iter-11 |
