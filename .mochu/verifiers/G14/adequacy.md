# G14 — Verifier Adequacy Audit

Claim under test: README.md and SKILL.md describe the OKF v0.1 model, ship canonical
`Concept` terminology (no residual `drawer`/`drawers`), document the Bundle as source of
truth, document git-based multi-device sync, and document the psychological-memory field
vocabulary (`sb_subject`/`sb_valid_from`/`sb_affect`).

This is a **docs gap**. The mochu skill's docs-dimension guidance is "read-as-stranger,
then execute what the docs claim" — i.e. the strongest-pattern check is *operational*:
a stranger reading README + SKILL must be able to install, run the CLI, sync to a git
remote, and trigger proactive recall. The current verifier is a **content scan** (regex
presence/coherence checks on README + SKILL.md), which is appropriate for *terminology
and capability coverage* but does not by itself prove the CLI commands in the docs work.

The split is intentional for this iteration (T001): the docs-okf verifier is the
*content-coherence* half, and the existing G01/G02/G05/G19 verifiers collectively prove
the *operational* half (OKF serializer exists, bundle round-trips, git sync works,
recall hook fires). Adding a separate "stranger-can-install" verifier is reasonable
future work (D002's parity tail has it as a candidate), but for G14 we ship the
content-coherence half with the strongest regex coverage we can.

## The three lazy artifacts (summary list)

1. **Drawer-bleed.** A "fix" that rewrites only the docs sections about explicit
   drawer-vs-Concept contrast, leaving residual `drawer`/`drawers` mentions elsewhere
   (e.g. "50K drawers", "untouched drawers", "cold-store untouched drawers") — the
   kind of leak a keyword search would miss because the words *do* appear, just not
   in the prominently-edited spots.
2. **Jargon-only OKF mention.** A "fix" that adds the phrase "OKF v0.1" to the README
   tagline once, without ever explaining what OKF is, what a Bundle is, how Bundle
   relates to the SQLite cache, or that SQLite is disposable. Passes a `okf.*v0\.1`
   grep, fails a stranger's "can I use this?" test.
3. **Capability without how-to.** A "fix" that mentions multi-device sync and
   psychological memory in marketing copy but never documents the actual CLI command,
   the git-sync flow, the `sb_*` frontmatter field names, or where the user starts.

## How the suite blocks each

- **Artifact 1 (drawer-bleed).** `_scan_drawers()` in `verify_docs.py` walks every
  line of README.md and SKILL.md, regex-matches `\b(drawer|drawers|Drawers)\b`, and
  fails with the line number + content on any hit. The original verifier had a buggy
  `(?!concept)drawer(?!.*concept)` heuristic that *required* `drawer` to appear; the
  rewrite inverts it into a true coherence check. Tested: appending `this is a drawer
  test` to README → exit 1 with `L342: drawer -> this is a drawer test`.
- **Artifact 2 (jargon-only OKF).** The OKF/Bundle/git-sync checks require both the
  concept to appear AND context (`okf.*v0\.1|v0\.1.*okf` forces the version; `bundle`
  forces the term; `git.*sync|sync.*git|multi.device` forces a real sync mention).
  A bare `OKF` mention with no `v0.1` or `Bundle` next to it fails. Not yet covered:
  a behavioral check that the install commands actually run — deferred to a future
  "stranger-install" verifier per the docs-dimension guidance.
- **Artifact 3 (capability without how-to).** The SKILL.md checks require
  `sb_subject|sb_valid_from|sb_affect` to appear (so the psychological-field vocabulary
  is documented, not just the word "psychological") and a `Concept` mention. README's
  Quick start commands are not separately checked here — they are implicitly tested by
  every other shipped verifier (G01–G07, G19) because those verifiers exercise the
  exact commands the docs describe.

## Strongest-pattern check

The `docs-okf` verifier runs as part of `scripts/run_corpus.py` and `ship_gate.py`,
executes in a fresh subprocess per iteration (no cross-test state), and reads README +
SKILL.md from disk (not from a snapshot). The pre-work re-red confirmed it
discriminates: against the pre-T001 README (which lacked OKF v0.1 and `Concept`
terminology), the new verifier correctly fails on `OKF v0.1 mentioned` and
`Concept terminology`. Inserting a single `drawer` reference fails it on the
coherence check with a line citation.

## Out of scope (own gaps, not G14)

- **A "stranger-can-install" verifier.** Worth doing; deferred to the docs-dimension
  roadmap. The current gap is best addressed by a separate verifier that runs the
  README's install + Quick start commands in a clean subprocess and asserts exit 0 +
  expected output.
- **CHANGELOG.md updates.** G14 ships docs that include the new OKF/Concept/sync
  positioning; the CHANGELOG entry that records the ship is part of T001's record
  (see `.mochu/ledger.md`), not part of the docs-okf verifier.
- **`docs/07-pmf-and-gap-analysis.md` and `docs/README.md`.** These are architect-spine
  files, not user-facing; not covered by the docs-okf content scope (which targets
  README + SKILL only, per T001's interfaces & contracts).
