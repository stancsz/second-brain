# Iteration 7 Findings: G14 Docs Update

**Date:** 2026-06-18  
**Gap:** G14 [docs] — Update README.md and SKILL.md to reflect OKF terminology and shipped capabilities  
**Status:** SHIPPED (pending Phase 6 gate)  
**Attempt:** 1

---

## What We Did

Renamed `drawer` → `Concept` throughout SecondBrain's user-facing docs and documented the shipped capabilities that have been implemented since iter-0:

### README.md Changes
- Updated headline to mention "OKF v0.1-native" and "multi-device sync via git"
- Changed schema badge from "v2.1" to "OKF v0.1"
- Expanded "What it is" section to describe Bundle as source-of-truth, SQLite as rebuildable cache
- Updated Features section:
  - Added "OKF Bundle as source of truth" as first item
  - Documented multi-device sync (git as backbone, one-way cloud mirrors)
  - Added conflict parking behavior
  - Expanded psychological memory section with field names (subjects, temporal validity, affect, supersession)
  - Mentioned Phase 2 (planned) includes encryption

### SKILL.md Changes (skill description, not the mochu skill)
- Updated description: "OKF v0.1-native, multi-device sync via git, psychological memory foundation"
- Rewrote opening to describe Bundle + SQLite cache architecture
- Documented psychological fields: subjects, temporal validity, affect, supersession
- Replaced all ~50 instances of "drawer" with "Concept"

---

## Verifier

**Name:** `docs-okf`  
**Pattern:** Regex checks for:
- OKF v0.1 terminology in README
- Bundle/export/sync capability mentions
- Concept terminology (not drawer)
- Psychological field names (sb_subject, sb_valid_from, sb_affect, etc.)

**Result:** ✓ RED (verified before work), ✓ GREEN (verified after work)

---

## Handoff Review

Reviewed as a staff engineer would:

- **Prose quality:** Clear, addresses first-time reader questions (what is it, why use it, how does sync work)
- **Consistency:** OKF terminology used consistently; no lingering "drawer" references
- **Completeness:** All shipped features (iter-1 through iter-6) are now described
- **Runnability:** User can read docs and understand the product's core value proposition
- **Debris:** No TODOs, debug text, or placeholder copy introduced

**Verdict:** No blocking findings. Ready to ship.

---

## Regression Corpus

All 9 verifiers pass (no regressions):
- okf-roundtrip (G01)
- okf-conformance (G01)
- bundle-rebuild (G02)
- index-log (G03)
- git-sync (G05)
- tombstone (G07)
- conflict (G06)
- recall-encoding (G19 pre-existing)
- docs-okf (G14 new)

---

## What We Learned

### Pattern: Docs gaps don't fit the 3-artifact adequacy model

Phase 3.5 (adequacy audit) asks gaps to enumerate "three concrete lazy artifacts." This is crisp for code (a function that almost works, a half-implemented feature), but artificial for docs. Instead, docs adequacy is: "Did I answer the stranger's obvious questions?" This suggests mochu should have dimension-aware adequacy rules.

### Observation: Naming matters for user understanding

Renaming "drawer" → "Concept" everywhere doesn't just match OKF spec; it unlocks reader comprehension. "Drawer" is meaningless jargon for new users. "Concept" (borrowed from OKF and used in academic knowledge management) immediately signals "a unit of knowledge I can save, link, and manage."

### Note: Psychological memory is now a headline feature, not an afterthought

By documenting subjects, temporal validity, affect, and supersession upfront in the README, we signal that this product is not just "Obsidian with git" — it's purpose-built for AI memory synthesis (personas, historical facts, emotional context, belief evolution). This is our competitive edge over Mem0, Zep, etc.

---

## Known Limitations

- Documentation doesn't yet describe encryption (Phase 2 planned feature)
- MCP server interface not yet mentioned (Phase 2 planned)
- No mention of scheduled sync / install.sh (G15, Phase E)
- Backend adapters (S3, GCS, GDrive, OneDrive) not yet shipped or documented

These are appropriate — they're not shipped yet.

---

## Next: G04 (Phase A completion)

With G14 shipped, Phase A documentation is complete. Next gap to unblock Phase B is **G04: rename `drawer` → `Concept` in the schema and CLI code**. This is a code-level change (update SQL schema, brain_cli.py, all internal references). Phase A milestone (G01 serializer, G02 export/rebuild, G03 index/log, G04 terminology) will then be done, unblocking Phase B (git spine completion: G05 done, G06 done, G07 done).
