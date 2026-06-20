# SecondBrain Roadmap — iter-19 → iter-27 (RELEASE 10/15 → 15/15)

**Authored:** 2026-06-20 (after iter-18 closed R11; reviewing `docs/09-worklog-feedback.md` + iter-18 competitive intel)
**Driver:** the mochu autonomous loop. This doc is a *design artifact* for the human; the loop's actual inputs are `.mochu/gaps.md` (scored) + `.mochu/RELEASE.md` (finish line). Every gap below is logged there with a verifier sketch.

## Governing architectural decision

**Every new capability is an OPTIONAL, lazy-loaded adapter with a stdlib fallback.** This is the hinge of the entire roadmap. Our moat is zero-dependency / air-gapped / files-are-truth. `sqlite-vec` (semantic search), `boto3` (cloud backup), `age` (encryption), and the MCP SDK are all lazy-imported; when absent, the system degrades gracefully (FTS5 fallback, local-only, plaintext-skip) and never crashes. For every such adapter, the **"adapter absent" path is a first-class verifier phase**, not an afterthought — that fallback leg is precisely what protects the moat.

## Phase 1 — Harden the psych layer (reliability) · iter 19–21

The bi-temporal + affect + subject layers (G08/G09/G10) are new and under-guarded. Three cheap, high-leverage fixes from the review. Aligns with the rotation rule (features is heavy in the last 6 iters; the selector is biased toward reliability now).

| Iter | Gap | Score | Closes |
|---|---|---|---|
| 19 | **G26** ISO date validation on validity windows (+ rebuild quarantine) | 15.0 | review debt; hardens R11 |
| 20 | **G27** restore() re-syncs affect/subject/validity derived indexes | 8.0 | review debt; hardens R10/R11/R12 |
| 21 | **G28** CLI error boundary — no stack traces on bad input | 6.0 | review debt; DX |

## Phase 2 — Close the RELEASE finish line (trust + survivability) · iter 22–24

Now that psych data is rich, getting it safely to a remote is the next guard.

| Iter | Gap | RELEASE | Note |
|---|---|---|---|
| 22 | **G13** selective-by-tag encryption (age) | **R13** | Episode/RelationshipModel/private → ciphertext before push; plaintext stays diffable. Makes the psych layer safe to sync at all. |
| 23 | **G11** cloud backup (`Backend` ABC + S3/GCS adapter) | **R8** | one-way mirror; SDK lazy + mocked in verifier (push→wipe→restore→rebuild) |
| 24 | **RECON** (every-8th) | — | re-validate the semantic-search bet before building it |

After Phase 2: **RELEASE 12/15** (R8, R13 done; R9 = G15 scheduler remains, queued behind moat work or interleaved).

## Phase 3 — Competitive moat · iter 25–27+

Ordered by moat-per-effort: bank the Mem0-graph-retreat opening first (dependency-free), then the heavyweight vector work.

| Iter | Gap | Why now |
|---|---|---|
| 25 | **G25** graph-aware search ranking (dependency-free) | Mem0 *dropped* graph-as-API; we keep the graph and use it at rank time. Pure traversal, zero new deps. |
| 26 | **G29** semantic search via `sqlite-vec` (optional adapter) | the #1 "behind" gap; both legs (present + absent) proven or it doesn't ship. **Candidate R16.** |
| 27 | **G30** generic MCP server | any framework (LangChain/AutoGen/LlamaIndex) hooks in with zero glue. **Candidate R17.** |

**Backlog (post-27):** G31 auto-extraction (agent-side, opt-in — LLM calls stay out of the core), G15 scheduler (R9), G17 v2.1 migration, G21 README.zh parity, G24 untracked-docs hygiene.

## New RELEASE criteria (RATIFIED 2026-06-20 — finish line is now 17)

- **R16** — `search --semantic` recalls a synonym FTS5 would miss when `sqlite-vec` is present, and falls back to FTS5 with no crash when it is absent. (verifier: semantic-search, G29)
- **R17** — every core brain operation is reachable over MCP; a third-party client can search/add/recall without bespoke glue. (verifier: mcp-server, G30)

"Production-ready + competitive" now explicitly includes semantic recall (R16) and ecosystem reach (R17). RELEASE target: **17 criteria** (currently 10/17).

## Invariants (hold across all iterations)

1. Zero-dependency core stays zero-dependency — new capabilities are lazy adapters with stdlib fallbacks.
2. Files remain truth — no feature makes `brain.db` authoritative; derived indexes only.
3. Verifier-first, both legs — for every optional adapter, the "adapter absent" path is a first-class verifier phase.
4. RELEASE is sacred — R16/R17 are proposals to ratify, never silent goalpost moves.
