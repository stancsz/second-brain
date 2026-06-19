# G02 — Verifier Adequacy Audit

Claim: export a brain to an OKF Bundle and rebuild a *fresh* brain.db from those files
with zero loss — making SQLite a disposable cache (RELEASE R2/R3).

## The three lazy artifacts (summary list)

1. Content-only export — writes title/body but drops tags, sources, collection, and the
   `sb_*`/`type` metadata, so rebuild silently loses structure.
2. Dead rebuild — parses files back into rows but never re-derives wikilink relations or the
   FTS index, so search and the graph are empty after a rebuild.
3. Happy path — flattens collections, resurrects soft-deleted drawers, or corrupts unicode.

## How the suite blocks each

- **Artifact 1** — the verifier compares title, content, collection, tags (sorted), and sources
  (sorted) for every drawer id across export→rebuild. Any dropped field fails. It also asserts
  every emitted concept file is OKF-conformant (`type` present), so structural metadata must ride along.
- **Artifact 2** — asserts `b2.related(A)` re-derives the `[[Payments]]` wikilink edge (>=1 and
  equal to the pre-export count) and that `b2.search("timeout")` returns the expected drawer —
  both require rebuild to actually re-derive relations and the FTS index, not just insert rows.
- **Artifact 3** — the corpus includes two drawers in a collection (round-tripped), a root
  (collection-less) drawer, a soft-deleted drawer (must stay dead after rebuild), and a unicode
  body (中文). Collection mismatch, resurrection, or mojibake each fail.

## Strongest-pattern check
Executes the real `bundle.export` + `bundle.rebuild` against a live SQLite brain and asserts on
observable rebuilt state (queries, search, graph) — not file presence. Independent fresh-db
rebuild proves disposability rather than reading back the same handle.

## Out of scope (own gaps)
- index.md / log.md generation (G03), model rename drawer→Concept (G04), cross-concept
  bundle-relative link *rendering* (later), and real `sb_*` columns (G08–G10; until then the
  serializer's psych fields ride in `drawers.metadata` and are validated by G01's round-trip).
