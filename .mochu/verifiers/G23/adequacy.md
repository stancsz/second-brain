# G23 Adequacy Audit

## Three lazy artifacts the suite must reject

1. **Only checks one file.** A lazy implementation could scan `commands/brain.md` and
   ignore `references/architecture.md` (which has 16 hits pre-iter) and still report
   PASS. → The verifier iterates `git ls-files <dir>/**/*.md` so every tracked file
   in scope is scanned; the per-file hit list is printed on FAIL so a missing file
   would show as `0 files scanned` for that dir.

2. **Only checks lowercase `drawer`.** A lazy regex `re.search("drawer", text)` would
   miss `Drawer` (capitalized) in prose like "the Drawer model". → The regex is
   `\\b(drawer|drawers|Drawers)\\b` — case-sensitive on three explicit forms; missing
   any of them shows up in the hit list.

3. **Positive `Concept` check instead of negative `drawer` check.** A lazy verifier
   could assert "the file mentions Concept" which would pass if a file has *both*
   "the Concept" and "a drawer". → The verifier asserts ZERO matches of the
   `drawer` family; presence of `Concept` is not checked (so a file that adds
   `Concept` without removing `drawer` still FAILS).

## Strongest-pattern check (per the docs dimension)

- Per the cookbook, a docs verifier should *execute* the user-facing surface, not grep
  for its presence. G23's check IS the surface: the docs/commands/references files
  ARE the product surface for the "docs" dimension. The verifier reads them with a
  strict regex and reports hits with file:line:context, so a future contributor can
  diagnose any drift in one read.
- The verifier is anchored to `git ls-files` (not free-form glob) so it cannot be
  fooled by a stray untracked draft, and so a future file-add to commands/ or docs/
  is automatically covered.

## Senior-engineer sign-off test

> "Would a senior engineer at the competitor (Mem0 / Zep / Letta / Supermemory) sign
> off on this as the bar for 'no terminology drift in the docs surface'?"

Honest answer: yes, with the carve-outs documented below. A stricter bar would also
check rendered output (does the published docs site have `drawer`?); for a local
markdown repo like this one, the in-tree scan is the strongest applicable check.

## Out of scope (intentional)

- README.md + SKILL.md — covered by G14 (docs-okf) to avoid double-coverage drift.
- CHANGELOG.md — historical record; rewriting past entries would be revisionism.
  The new v3.0 entry already says "drawers → concepts" in the appropriate context.
- Untracked files in docs/ — separate hygiene gap; not G23's concern.

## Calibration evidence (pre-iter run)

The verifier was run at HEAD before any M3 work and reported FAIL with the following
counts (recorded in iter-12 ledger):
- README.zh.md: 1 hit
- commands/brain.md: 4 hits
- commands/history.md: 2 hits
- docs/01-overview-and-decisions.md: 1 hit
- docs/02-okf-and-terminology.md: 4 hits
- docs/06-build-plan.md: 1 hit
- docs/07-pmf-and-gap-analysis.md: 1 hit
- references/architecture.md: 16 hits
- references/distill-archive.md: 25 hits
- TOTAL: 55 hits across 9 files

After M3, expected: 0 hits across all in-scope files.
