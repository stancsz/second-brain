# G01 — Verifier Adequacy Audit

Claim under test: a Concept ⇄ OKF markdown serializer that round-trips losslessly and
emits OKF v0.1-conformant documents with `sb_*` psychological extensions.

## The three lazy artifacts (summary list)

1. Drops the psychology — round-trips only title/body/tags and silently discards every `sb_*` field.
2. Not actually OKF — emits frontmatter without the required non-empty `type` field.
3. Happy path only — corrupts unicode/special-char titles, mangles multi-source Citations, loses
   wikilinks/empty bodies, or flattens `collection` and breaks the path↔id Bundle hierarchy.

## Three lazy artifacts that would pass a *weak* suite — and how this suite blocks each

### Lazy artifact 1 — "drops the psychology"
A serializer that round-trips only `title`/`body`/`tags` and silently discards every `sb_*`
field (`sb_subject`, `sb_valid_from/to`, `sb_supersedes`, `sb_affect`, `sb_relations`,
`sb_deleted`). It would look correct on a plain note and quietly destroy the actual
differentiator — psychological/temporal memory.
**Blocked by:** `verify_roundtrip.py` compares all 16 canonical KEYS, including every `sb_*`
field, on the `Episode` (c3) and `Trait` (d4) concepts. Any dropped field → mismatch → exit 1.

### Lazy artifact 2 — "not actually OKF"
A serializer that emits markdown + frontmatter but omits the OKF-**required** `type` field
(or emits an empty one). It would round-trip fine through our own parser yet fail OKF
conformance §9 — i.e. no other OKF consumer (Knowledge Catalog, the OKF visualizer) could use it.
**Blocked by:** `verify_conformance.py` reads the emitted **text independently** (not via
okf.from_markdown) and asserts a non-empty `type` on every document. Also pins `OKF_VERSION`.

### Lazy artifact 3 — "happy path only"
A serializer that works on ASCII titles in a single flat folder but corrupts unicode/emoji/
slash/colon titles, mangles multi-source `# Citations`, loses wikilinks in the body, breaks on
an empty body, or ignores `collection` (flattening the Bundle hierarchy and breaking path↔id).
**Blocked by:** `verify_roundtrip.py` includes a 中文/emoji/`/`/`:` title (b2), a 3-source
Reference (e5), a wikilink body (f6), an empty body (i9), and a root-collection concept (g7).
`verify_conformance.py` additionally asserts collection→subdirectory path mapping, the
path↔id rule, and that every source URL appears in the Citations section.

## Strongest-pattern check
Both verifiers **execute the real serializer** over a battery of concepts rather than grepping
for the presence of an `okf.py`. The conformance check validates emitted bytes against the OKF
spec independently of our parser, so passing it cannot be faked by a permissive reader.

## Would a senior engineer at Zep/Mem0 sign off as the acceptance bar?
Yes for G01's scope (serialize/round-trip/conform). Out of scope here and deferred to their own
gaps: G02 (rebuild whole DB from a bundle walk), G03 (index.md/log.md generation), G04 (rename),
and bundle-relative link *rendering* across concepts (the resolver) — tested when those land.
