# Worklog Feedback (Iter 14-17)

**Date:** 2026-06-20
**Review of:** `.mochu/ledger.md` (Iter-14 through Iter-17)

## Overview of Progress

The momentum and engineering discipline across the last four iterations are highly commendable. The execution reflects a strong adherence to verifiable, iterative shipping with clear "red-before-green" verifier gates.

- **Iter-14 (G08):** Successfully shipped subjects and persona sub-graphs (R10 M1).
- **Iter-15 (G10):** Delivered the structured affect table (R12), enabling nuanced emotional querying.
- **Iter-16 (Recon):** Excellent strategic pivot. Identifying Mem0's shift away from an external graph store and confirming Zep's bi-temporal bar allowed us to log G25 (graph-aware search ranking). This turns our existing relations graph into a significant competitive differentiator.
- **Iter-17 (G09):** Shipped bi-temporal validity storage (R11 M1). The decision to split M1 (storage) and M2 (query) was sharp and prevented scope creep while securing the bi-temporal history invariant.

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
**Actionable:** Add a strict format validation step during the `bundle.rebuild` phase and the `supersede()` write-path to prevent corrupted temporal windows.

### 4. Edge Cases in Soft Deletes (Iter-15 observation)
Soft-deleted concepts drop their affect and subject rows on rebuild. While this accurately mirrors the current index logic, we need to ensure that if a concept is "restored," the reindexing reliably recovers all psychological dimensions.
**Actionable:** Add an explicit test case for soft-delete followed by restore to guarantee `affect` and `subject` metadata return intact.

## Next Steps

- **Prioritize G09 M2:** Complete the `recall_as_of` query and `--as-of` CLI to fully close R11.
- **Review G25:** With Mem0 dropping graph-as-API, implementing dependency-free graph-aware search ranking (G25) is a high-ROI feature that cements our competitive advantage.
