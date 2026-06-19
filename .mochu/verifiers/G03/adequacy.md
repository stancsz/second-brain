# G03 — Verifier Adequacy Audit

Claim: exported Bundles carry OKF reserved files — a root `index.md` (with `okf_version: "0.1"`),
per-subdirectory `index.md`, and a `log.md` — all conformant, with the Bundle still rebuildable.

## The three lazy artifacts (summary list)

1. Empty index — emits `index.md` files that exist but list nothing (no concepts, no collections).
2. Broken links — index/log entries link to paths that don't resolve to real files.
3. Malformed log / missing pin — `log.md` not ISO date-grouped or not newest-first, or the root
   index omits `okf_version`, or an index.md leaks back in as a drawer on rebuild.

## How the suite blocks each

- **Artifact 1** — asserts specific concept titles ("Root note", "Checkout timeout fix",
  "Payments") and collection names ("Engineering", "Planning") appear as links in the relevant
  index files. An empty index fails immediately.
- **Artifact 2** — resolves *every* markdown link target in the root and subdir index files to an
  existing file/dir under the Bundle. Any broken link fails.
- **Artifact 3** — regex-checks `## YYYY-MM-DD` ISO headings, asserts they are sorted newest-first,
  requires the `okf_version: "0.1"` declaration in the root index, asserts subdir index.md has NO
  frontmatter (OKF §6), and re-runs `bundle.rebuild` asserting the concept count is unchanged and
  no index.md leaked in as a drawer.

## Strongest-pattern check
Executes the real export + rebuild and validates the generated files' structure and link integrity
against the OKF spec — not mere existence of the files.

## Out of scope (own gaps)
CLI/skill wiring (G05+), cross-concept link rendering, and per-subdirectory log.md (only a root
log.md is required here; nested logs are optional in OKF §7).
