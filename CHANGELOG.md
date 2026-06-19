# Changelog

## [Unreleased]

### Added
- **OKF serializer** (`scripts/okf.py`) — converts a Concept to/from an Open Knowledge
  Format (OKF v0.1) markdown document with YAML frontmatter, and back, losslessly. Supports
  the namespaced `sb_*` psychological extensions (`sb_subject`, `sb_valid_from/to`,
  `sb_supersedes`, `sb_affect`, `sb_relations`, `sb_deleted`), encodes `collection` as the
  file's bundle directory, and renders `sources` as an OKF `resource` + `# Citations` section.
  Run `python scripts/okf.py demo` to see a sample document. (mochu iter-1, gap G01)
  - Known limitations: serializer only; it does **not** yet walk a bundle to rebuild the DB
    (G02), generate `index.md`/`log.md` (G03), rename the live `drawer` model to `Concept`
    (G04), or render cross-concept `[[wikilinks]]` as bundle-relative OKF links (those remain
    verbatim in the body for now). No CLI/skill wiring yet.
