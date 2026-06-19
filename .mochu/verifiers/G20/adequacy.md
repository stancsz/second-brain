# G20 — Verifier Adequacy Audit

Claim under test: an exported Bundle conforms to the OKF v0.1 specification at
the file-shape level. Specifically: `okf_version: "0.1"` lives in the
bundle-root `index.md` frontmatter (and NOT in a separate file); subdirectory
indexes carry no frontmatter; every Concept has a non-empty `type` and no
Concept's frontmatter contains an `okf_version` key; the bundle round-trips
(rebuild pre-condition).

This is a **trust** gap: the spec has been refetched (iter-8) and the code
appears compliant, but nothing in the corpus locks in compliance. The loop
must not silently drift back into "okf_version as a separate file" — a
regression that would break OKF interop with other Bundle consumers.

## The three lazy artifacts (summary list)

1. **"Spec mention" pass-through.** A verifier that greps `bundle.py` for
   the string `okf_version` and declares it conformant because the word
   appears once. Misses: the value (must be `"0.1"`), the location (must be
   in `index.md` frontmatter, not in body or in a separate file), the
   subdir-index rule, and the concept-side restriction.
2. **One-shot export check.** A verifier that only checks the happy path
   (a single root concept, no collection, no log) — would miss violations
   that only appear with a subdirectory present (e.g., a subdir index that
   silently gains a frontmatter block).
3. **Coarse regex that accepts CRLF-encoded bodies as separate files.** A
   verifier that uses `Path.rglob("okf_version")` naively might match
   `okf_version` in a body string, or fail to detect `okf_version.md` /
   `okf_version.txt` because of an exact-name match only.

## How the suite blocks each

- **Artifact 1 (pass-through).** The verifier actually exports a real Bundle
  with both a root concept AND a subdirectory collection, then parses the
  `index.md` frontmatter structurally (extracts `okf_version` value and
  asserts equality with `okf.OKF_VERSION` constant, not just the literal
  string `"0.1"`). It also walks every non-reserved `.md` file and parses
  ITS frontmatter to assert `okf_version` is absent — catches the case
  where a Concept's frontmatter is silently extended.
- **Artifact 2 (one-shot).** The test brain has a root concept + a
  collection (`Eng`) with two concepts inside, so both root and subdir
  index.md files are exercised. The subdir-check loop is `rglob` based,
  not single-file, so any future subdir addition is automatically covered.
- **Artifact 3 (coarse rglob).** The file-existence check uses
  `bdir.rglob("okf_version*")` (globstar with prefix) — matches
  `okf_version.md`, `okf_version.txt`, `okf_version-backup`, etc. Body
  false-positives are avoided because the rglob is for files only, not
  text content.

## Strongest-pattern check

- **EXEC (not grep).** Operates on the real `bundle.export` output, parses
  frontmatter via a small YAML reader, and asserts on the structural shape
  — not on the source code or a mocked export.
- **Discrimination proof.** Inline test (recorded in the commit message):
  injecting `okf_version.md` into a Bundle is detected (output: `bad files:
  [okf_version.md]`). Corrupting a Concept's `type` field is detected
  (output: `(e) root.md: frontmatter 'type' is empty`).
- **Cross-references.** G01 (okf-conformance) covers the Bundle export
  shape at a coarser level; G02 (bundle-rebuild) covers the round-trip;
  G03 (index-log) covers the index structure. G20 is the spec-conformance
  specialization that locks in the `okf_version`-placement rule + Concept
  type-required rule against future drift.

## Out of scope (own gaps, not G20)

- **Bundle round-trip** (export → wipe → rebuild). G02 covers this.
- **Concept-level OKF interop** (do our Concepts interop with another
  consumer of OKF Bundles?). Not in scope until we have a second OKF
  consumer to test against.
- **OKF versioning beyond 0.1.** When the spec moves to 0.2, this verifier
  will need to be re-evaluated — the `okf_version` value check is
  anchored to `okf.OKF_VERSION` constant, not a literal.
- **README/SKILL.md wording about okf_version.** The docs (G14) reference
  OKF v0.1 generically; this verifier does not check the docs.
