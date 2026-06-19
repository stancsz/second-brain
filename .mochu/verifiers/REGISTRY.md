# Verifier Registry — the ratchet (append-only)

Index of every verifier in the corpus. The full corpus must stay green every iteration.
Run all via `python3 scripts/run_corpus.py`.

| id | dimension | claim | run command | added |
|---|---|---|---|---|
| okf-roundtrip | features | Concept ⇄ OKF markdown round-trips losslessly across all fields incl. sb_* | `python .mochu/verifiers/G01/verify_roundtrip.py` | iter-1 |
| okf-conformance | features | Every emitted Concept document conforms to OKF v0.1 §9 (non-empty type, frontmatter, path↔id, citations) | `python .mochu/verifiers/G01/verify_conformance.py` | iter-1 |
