# Worklog Feedback (Iter 14-20)

**Date:** 2026-06-20
**Review of:** `.mochu/ledger.md` (Iter-14 through Iter-20)

## Overview of Progress

The momentum and engineering discipline across the last four iterations are highly commendable. The execution reflects a strong adherence to verifiable, iterative shipping with clear "red-before-green" verifier gates.

- **Iter-14 (G08):** Successfully shipped subjects and persona sub-graphs (R10 M1).
- **Iter-15 (G10):** Delivered the structured affect table (R12), enabling nuanced emotional querying.
- **Iter-16 (Recon):** Excellent strategic pivot. Identifying Mem0's shift away from an external graph store and confirming Zep's bi-temporal bar allowed us to log G25 (graph-aware search ranking). This turns our existing relations graph into a significant competitive differentiator.
- **Iter-17 (G09 M1):** Shipped bi-temporal validity storage (R11 M1). The decision to split M1 (storage) and M2 (query) was sharp and prevented scope creep while securing the bi-temporal history invariant.
- **Iter-18 (G09 M2):** Completed the `--as-of` recall query, perfectly closing the R11 requirement and our biggest competitive gap against Zep.
- **Iter-19 (G26):** Implemented strict ISO date validation for temporal windows. This directly resolved the data validation risk surfaced in the previous review.
- **Iter-20 (G27):** Ensured `restore()` completely recovers all psychological dimensions (affect, subjects, validity). This directly resolved the soft-delete edge case surfaced in the previous review.

## Key Strengths

1. **Architecture Playbook:** The "derived-index playbook" (metadata-is-truth + rebuild-from-metadata + FK-cascade) used across G08, G10, and G09 is proving to be a highly effective and repeatable pattern.
2. **Scoping and Risk Management:** Splitting G09 into two milestones (storage first, query later) is exactly how complex data migrations and schema updates should be handled.
3. **Strategic Intel Integration:** The recon loop (iter-16) immediately translated into actionable product direction (G25). 

## Constructive Feedback & Areas for Improvement

### 1. Tooling & Meta-Hygiene (Iter-15 observation)
The cp1252 `UnicodeDecodeError` in `select_gap.py` and the stale entries in `gaps.md` are critical reminders: the agent's internal tooling must be treated with the same rigor as the production code. 
**Actionable:** Consider adding a "meta-verifier" that occasionally sweeps `.mochu/gaps.md` and custom tooling for known failure patterns (like missing UTF-8 encodings).

### 2. Error Boundaries (Iter-15 observation)
The CLI `try/finally` lacking an `except` block for malformed `--affect` JSON highlights a gap in global error handling. 
**Actionable:** Implement a standardized error boundary or decorator for all CLI entry points so that malformed inputs always yield a clean, actionable message instead of a stack trace.

### 3. Data Validation (Iter-17 observation)
In G09, `valid_from` and `valid_to` are currently opaque ISO strings without deep validation. While SQLite lexicographic sorting works for well-formed ISO 8601 strings, malformed strings will silently fail or sort incorrectly.
**Status:** ✅ **RESOLVED in Iter-19 (G26)**. The strict write / lenient rebuild contract is an elegant way to enforce hygiene without crashing on old files.

### 4. Edge Cases in Soft Deletes (Iter-15 observation)
Soft-deleted concepts drop their affect and subject rows on rebuild. While this accurately mirrors the current index logic, we need to ensure that if a concept is "restored," the reindexing reliably recovers all psychological dimensions.
**Status:** ✅ **RESOLVED in Iter-20 (G27)**. `restore()` now gracefully re-derives all three psych indexes directly from the restored `concepts.metadata`.

## Next Steps

- **Review G25:** With Mem0 dropping graph-as-API, implementing dependency-free graph-aware search ranking (G25) is a high-ROI feature that cements our competitive advantage.
- **G13 Encryption Decisions:** G13 is currently blocked on INBOX decisions (age vs. cryptography backend). Unblock this to secure the "files-as-truth" architecture for production.
- **G21 README.zh.md Parity:** The Chinese translation of the README is currently open and out of date with the OKF rename. Addressing this will fully close out the docs gap.
