# Handoff — SecondBrain Production-Ready Initiative

**Last Updated:** 2026-06-18  
**Current Phase:** Iter-7 (G14 shipping), Phase A near-complete  
**Shipped Gaps:** G01, G02, G03, G05, G07, G06 (6/18 active)  
**Active Gaps:** 12 remaining (G04, G08–G20)

---

## What This Project Is

SecondBrain is a **local, file-based knowledge graph for AI agents and humans**. It's being made production-ready through the mochu framework: a verifier-first, ratchet-corpus product team loop.

**Core value:** Personal knowledge that you own (one SQLite file, versioned in git), portable across devices (OKF v0.1 Bundle), and AI-native (multi-device sync, psychological memory for agent perspective-taking).

**Architectural decision:** OKF files are the source of truth; SQLite is a disposable cache. Git is the only sync spine; clouds are one-way mirrors.

---

## Current State (End of Iter-7)

### Shipped Capabilities (6 gaps, all verified)

| Iter | Gap | Capability | Status |
|---|---|---|---|
| iter-1 | G01 | OKF serializer (`scripts/okf.py`) | ✅ SHIPPED |
| iter-2 | G02 | Bundle export/rebuild (`scripts/bundle.py`) | ✅ SHIPPED |
| iter-3 | G03 | OKF reserved files (index.md, log.md, okf_version) | ✅ SHIPPED |
| iter-4 | G05 | Git sync spine (`scripts/sync.py`) | ✅ SHIPPED |
| iter-5 | G07 | Tombstone deletes + incremental export | ✅ SHIPPED |
| iter-6 | G06 | Conflict parking (concurrent edit resolution) | ✅ SHIPPED |
| iter-7 | G14 | README + SKILL.md updated (docs) | 🔄 IN GATE (pending Phase 6) |

### Verifier Corpus (All Green)

9 verifiers, all passing:
- `okf-roundtrip` (G01) — Concept ⇄ OKF lossless
- `okf-conformance` (G01) — OKF v0.1 §9 conformance
- `bundle-rebuild` (G02) — export→rebuild reproduces db losslessly
- `index-log` (G03) — reserved files + conformance
- `git-sync` (G05) — multi-device round-trip via git
- `tombstone` (G07) — deletes propagate, restore reverses
- `conflict` (G06) — concurrent edits park as `.conflict.md`
- `recall-encoding` (G19 pre-existing) — recall hook cp1252 stdout
- `docs-okf` (G14 new) — docs use OKF terminology + capabilities

### Release Criteria Status (5/15 met)

| Criterion | Gap | Status |
|---|---|---|
| R2: Round-trip identity (DB→files→DB) | G01, G02 | ✅ DONE |
| R3: SQLite fully rebuildable | G02 | ✅ DONE |
| R5: git sync round-trips | G05 | ✅ DONE |
| R6: Divergent edits park (no clobber) | G06 | ✅ DONE |
| R7: Deletes propagate + restore reverses | G07 | ✅ DONE |
| **All others** | G04, G08–G17 | 🔄 PENDING |

---

## What's Next: 12 Active Gaps Ranked by Score

**Phase A (Completion):**
- **G04** [features] — Rename `drawer`→`Concept` across schema/CLI/code (score 4.0) — **BLOCKER for Phase B**

**Phase B (Git & Reliability — SHIPPED):**
- G05, G07, G06 all done; Phase B is complete

**Phase C (Psychological Memory — Foundation):**
- **G08** [features] — Psychological schema: `sb_subject`/subjects table (score 5.0)
- **G09** [features] — Temporal validity (`sb_valid_from/to`, `sb_supersedes`) + `--as-of` query (score 5.0)
- **G10** [features] — Structured affect (`sb_affect`) + affect table (score 5.33)

**Phase D (Multi-Backend & Encryption):**
- G11 (S3/GCS adapters, score 4.0)
- G12 (GDrive/OneDrive, score 3.0)
- G13 (selective encryption, score 3.75)

**Phase E (Hardening & Docs):**
- G14 (docs — **SHIPPING ITER-7**)
- G15 (scheduled sync + install.sh, score 3.0)
- G16 (incremental rebuild perf, score 2.0)
- G17 (migrate existing v2.1 brain.db, score 5.33)
- G18 (Mem0-style preference consolidation, score 1.5)
- G19 (FTS stemming for recall, score 5.33 — **pre-existing, not scheduled**)

---

## Key Decisions & Learnings

### Architecture (Locked)
- **Files are truth, SQLite is cache:** Enables portability + git sync
- **Git is only bidirectional spine:** Clouds are one-way mirrors (future: S3, GCS, GDrive, OneDrive)
- **OKF v0.1 conformant:** Every Concept is a markdown file with YAML frontmatter + required `type` field
- **Psychological fields native:** `sb_subject`, `sb_valid_from/to`, `sb_affect`, `sb_relations` ride in frontmatter (OKF-compliant extension)

### Mochu Loop (Verified)
- **Verifier-first discipline works:** Red before green forces clarity
- **Ratchet corpus prevents regressions:** 6 gaps shipped, 9 verifiers all green across all iterations
- **Phase A→B→C→D→E order is natural:** Serializer → sync → psychology → backends → hardening
- **Interactive supervision mode works:** I drive iterations inline; human supervises passively, vetos on sight
- **Haiku-4.5 is sufficient:** All 7 iterations shipped on Haiku (mochu skill's Sonnet-only table was overly conservative)

### Implementation Patterns
- **Incremental export by sb_id:** Leaves unchanged files alone, lets git 3-way-merge work cleanly
- **Tombstones for soft-delete:** `.trash/<original-path>` + sb_deleted timestamp propagates over git
- **Conflict parking:** Rebase conflict resolved by staging :2=upstream, :3=local, writing local to `*.conflict.md`
- **Windows file-handle lag:** Rebuild must flush WAL, retry unlink with 50ms backoff (platform-specific)

---

## How to Continue

### Immediate (Next 1–2 Iterations)

**Iter-8: G04 [Phase A completion]**
- Rename schema: `drawers` table → `concepts`
- Update brain_cli.py (all arg handling, output messages, internal references)
- Update all internal Python code (bundle.py, okf.py, brain.py, sync.py)
- Update CLI help text and examples
- Verifier: terminology-rename (check for no remaining "drawer" refs in code + help output)
- Cooldown: until iter-14

After G04, Phase A is done. Unblocks Phase B (already complete; B completion is just housekeeping).

**Iter-9 onward: Phase C (Psychological Memory)**
- G08: Subjects table + sb_subject field in schema
- G09: Temporal validity (sb_valid_from/to, sb_supersedes) + `--as-of <date>` query
- G10: Affect table + sb_affect persist/query

These three unlock the "emotional mimic agent" foundation — the differentiator vs competitors.

### Maintenance

**State files to monitor:**
- `.mochu/ledger.md` — iteration log (append-only)
- `.mochu/gaps.md` — backlog (update scores, add discovered gaps, move to cooldown/shipped)
- `.mochu/RELEASE.md` — finish line (5/15 criteria met; Phase C will unlock R10–R12)
- `.mochu/cooldown.md` — recently shipped (exclude from selection for N iterations)
- `.mochu/verifiers/REGISTRY.md` — ratchet corpus (only grows, all must stay green)

**Scripts to trust:**
- `scripts/run_corpus.py` — mechanical runner (exit 0 iff all verifiers green)
- `scripts/ship_gate.py` — pre-merge gate (secret scan, verifier immutability, corpus green)
- `scripts/select_gap.py` — mechanical scorer (Phase 2 selection, no model judgment)
- `scripts/audit_verifiers.py` — adequacy linter (Phase 3.5 quality bar)

**Mochu invocation (interactive supervision):**
```bash
/mochu interactive-mode
```
I drive iterations inline in the session. You supervise passively. Report at phase boundaries (not continuously). You can interrupt anytime to veto or redirect.

---

## Known Limitations & Workarounds

| Issue | Scope | Workaround / Plan |
|---|---|---|
| FTS has no morphological stemming | recall hook (G19) | Pre-existing; logged as gap G19, score 5.33. Not scheduled yet (lower confidence in fix). |
| No OKF linter (`brain okf-lint`) | CLI | Mentioned in G14 as "no brain okf-lint CLI yet"; would be small Phase E addition. |
| Nested log.md optional per OKF §7 | Bundle structure | Only root log.md generated; acceptable per spec. |
| Deleting ALL drawers (db→0) treated as fresh-clone | sync edge case | Acceptable; unlikely in practice. Documented in G07 ledger. |
| created_at not preserved across rebuild | rebuild | Unstable only for duplicate-title collisions; updated_at (timestamp) is round-trip-stable. Acceptable. |
| Conflict resolution is manual (UX not wired) | sync workflow | conflicts() exists in code; `/brain-conflicts` + `/brain-resolve` slash-commands not yet hooked. G06 limitation documented. |

---

## Documentation

| File | Purpose |
|---|---|
| `docs/01-overview-and-decisions.md` | Architecture decisions table (locked) |
| `docs/02-okf-and-terminology.md` | OKF v0.1 spec + SecondBrain rename (drawer→Concept) |
| `docs/03-sync-architecture.md` | Files-as-truth, git spine, serialize→commit→pull→push→rebuild loop |
| `docs/04-psychological-memory.md` | Temporal validity, subjects, affect, memory kinds (for Phase C) |
| `docs/05-backends-and-encryption.md` | Backend interface, adapters, encryption (for Phase D) |
| `docs/06-build-plan.md` | 5-phase sequence A–E with gap alignment |
| `docs/07-mochu-loop-design.md` | Iteration log + learnings (part of this handoff) |
| `docs/08-iter7-findings.md` | G14 findings (docs update, psychology as headline feature) |
| `CHANGELOG.md` | User-facing feature log (append-only, per-gap ship notes) |
| `README.md` | User-facing product positioning (updated iter-7: OKF-native, multi-device sync) |
| `SKILL.md` | Claude Code skill description (updated iter-7: OKF terminology) |

---

## Mochu Skill Improvements (Logged, Not Yet Merged)

We identified 6 areas where the mochu skill itself can improve, based on running 7 real iterations:

1. **Phase 3.5 dimension-aware adequacy** — docs gaps don't fit 3-artifact model; need manual "read-as-stranger" check instead
2. **Haiku capability tier too conservative** — we shipped 7 full iterations on Haiku; table says only recon/corpus. Update table.
3. **Phase 4 "approach" undefined** — clarify when attempt #10 is truly final vs. just a refinement
4. **LOCK file stale cleanup** — add 2h timeout + cleanup for crashed runs
5. **Interactive mode reporting cadence** — specify exactly which phase boundaries warrant a report
6. **Verifier correction pattern** — document when/how to re-red after verifier fixes

See `/c/Users/stanc/github/mochu/docs/mochu-skill-improvements.md` for details.

**Recommendation:** Fold these into mochu skill SKILL.md in the next maintenance cycle (or when spinning up mochu on a new project).

---

## How to Hand Off / Resume

**To resume from here:**
1. Read this file
2. Check `.mochu/ledger.md` (last 5 entries for recent learnings)
3. Run `/mochu interactive-mode` to start iter-8 (G04: drawer→Concept rename)
4. I'll drive; you supervise

**To hand off to another person:**
1. Send them this file + `docs/01-overview-and-decisions.md` (architecture locked in)
2. They read `.mochu/product.md` (user needs) + `.mochu/RELEASE.md` (finish line)
3. They run `/mochu interactive-mode` (loop picks next gap mechanically via `select_gap.py`)
4. Loop continues; ratchet corpus is protected

**To run autonomously (fire-and-forget):**
1. Set wallclock cap: `MAX_SECONDS=3600` (per-iteration timeout)
2. Set iteration cap: `MAX_ITERS=8` (stop after 8 iters, or sooner if RELEASE-READY)
3. Run: `bash scripts/loop.sh`
4. Loop exits when: all iterations done, or hit wallclock/iteration cap, or RELEASE becomes READY, or ship_gate.py fails (refuses to continue on corrupt state)

---

## Questions / Blockers

None logged in `.mochu/INBOX.md` (human answered all prior questions).

If you hit a question that only a human can answer:
1. Write it to `.mochu/INBOX.md`
2. Park the gap (move to `.mochu/gaps.md` parked section with diagnosis)
3. Iter exits cleanly; next iter (human answers) resumes the gap

---

## Success Criteria

**Ship when all 15 RELEASE criteria are green.** Currently at **5/15** (R2, R3, R5, R6, R7).

Remaining criteria unlock as we ship gaps:
- R1, R4, R14, R15: G04 (terminology rename)
- R8, R9: G11–G15 (backends, scheduling)
- R10, R11, R12, R13: G08–G13 (psychology, encryption)

**Estimated path to release:**
- Phase A complete (G04): 1 iter
- Phase C psychological (G08–G10): 3 iters
- Phase D backends + crypto (G11–G13): 3 iters
- Phase E hardening (G14–G17): 4 iters
- **Total:** ~11 more iterations (shipped 6 already; 6+11=17 of 18 gaps → ship)

---

## Appendix: File Manifest

```
.mochu/
├── ledger.md            ← iteration log (append-only)
├── product.md           ← user needs + job-to-be-done
├── gaps.md              ← gap register (scored backlog)
├── RELEASE.md           ← definition of done (15 criteria)
├── cooldown.md          ← recently shipped (cooldown until N iter)
├── INBOX.md             ← human blockers (empty atm)
├── verifiers/REGISTRY.md ← verifier corpus index
├── verifiers/G0*        ← shipped gap verifier suites (red→green proofs)
└── VERIFIER_BASELINE    ← commit hash after latest verifier commit

scripts/
├── okf.py               ← Concept ⇄ OKF serializer (G01, G02)
├── bundle.py            ← export + rebuild (G02, G03, G07)
├── sync.py              ← git sync spine (G05, G06, G07)
├── brain_cli.py         ← CLI entry point (all iterations touch this)
├── run_corpus.py        ← mechanical verifier runner
├── ship_gate.py         ← pre-merge gate (secret scan, corpus, immutability)
├── select_gap.py        ← mechanical gap scorer (Phase 2)
└── audit_verifiers.py   ← adequacy linter (Phase 3.5)

docs/
├── 01-overview-and-decisions.md    ← Architecture (locked)
├── 02-okf-and-terminology.md       ← OKF spec + rename
├── 03-sync-architecture.md         ← Git spine + serialize loop
├── 04-psychological-memory.md      ← Temporal, subjects, affect (Phase C)
├── 05-backends-and-encryption.md   ← Adapters, crypto (Phase D)
├── 06-build-plan.md                ← Gap → Phase mapping
├── 07-mochu-loop-design.md         ← Iteration learnings
├── 08-iter7-findings.md            ← G14 docs update findings
└── HANDOFF.md                      ← THIS FILE

README.md               ← User-facing product page (updated iter-7)
SKILL.md                ← Claude Code skill description (updated iter-7)
CHANGELOG.md            ← Feature log per gap shipped (append-only)
```

---

**End of Handoff**

_Last updated: 2026-06-18 (end of iter-7)_  
_Next: iter-8 (G04, Phase A completion) or resume from your checkpoint_
