#!/usr/bin/env python3
"""G01 verifier — OKF Concept serializer round-trip identity.

Claim: a Concept serialized to an OKF markdown document and parsed back is
identical across every field, including the `sb_*` psychological extensions,
unicode/special-char titles, multiple sources, wikilinks in the body, an
empty (root) collection, and tombstones.

This EXECUTES the real serializer (scripts/okf.py) over a battery of concepts.
Exits nonzero on the first field mismatch. Independent of okf internals: it
only uses the public to_markdown / from_markdown contract.
"""
import sys, os
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
import okf  # noqa: E402  (must exist; absence = RED, which is the point pre-build)

# Canonical full schema. Every concept dict carries all keys; absent optionals
# are None / []. from_markdown(to_markdown(c)) must reproduce this exactly
# (body compared modulo leading/trailing blank lines).
KEYS = [
    "sb_id", "type", "title", "description", "collection", "tags", "sources",
    "timestamp", "body", "sb_subject", "sb_valid_from", "sb_valid_to",
    "sb_supersedes", "sb_affect", "sb_relations", "sb_deleted",
]


def C(**kw):
    base = {k: None for k in KEYS}
    base["tags"] = []
    base["sources"] = []
    base["sb_relations"] = []
    base["type"] = "Note"
    base.update(kw)
    return base


CONCEPTS = [
    C(sb_id="a1", title="Plain Note", body="Just a simple body line."),
    C(sb_id="b2", title="中文标题 with émojis 🔥 / slashes : colons",
      body="Body with unicode 日本語 and symbols <>&|.",
      description="A one-line summary.", collection="notes",
      tags=["zh", "test"], timestamp="2026-06-18T20:14:00Z"),
    C(sb_id="c3", type="Episode", title="First real fight with Rox",
      description="Argument about silence.", collection="episodes",
      tags=["relationship", "conflict", "private"],
      timestamp="2026-06-18T20:14:00Z",
      sb_subject="/people/rox.md",
      sb_valid_from="2024-11-02T00:00:00Z",
      sb_affect={"valence": -0.7, "arousal": 0.6, "emotion": "hurt",
                 "intensity": 0.8},
      sb_relations=[{"to": "/traits/rox-conflict-avoidant.md",
                     "type": "expands", "strength": 0.8}],
      body="The argument started over a missed call.\n\nIt escalated."),
    C(sb_id="d4", type="Trait", title="Rox is conflict-avoidant",
      collection="traits", sb_subject="/people/rox.md",
      sb_valid_from="2024-01-01T00:00:00Z", sb_valid_to="2025-06-01T00:00:00Z",
      sb_supersedes="/traits/rox-distant.md",
      body="Goes quiet rather than confront."),
    C(sb_id="e5", title="Multi-source Reference", type="Reference",
      collection="references",
      sources=["https://example.com/a", "https://example.com/b",
               "https://cloud.google.com/blog/x"],
      body="See the cited material below."),
    C(sb_id="f6", title="Has Wikilinks", collection="notes",
      body="Links to [[Plain Note]] and [[中文标题]] inline."),
    C(sb_id="g7", title="Root Concept No Collection",
      body="Lives at the bundle root, no subdirectory."),
    C(sb_id="h8", title="Tombstoned", collection="notes",
      sb_deleted="2026-06-18T21:00:00Z", body="Soft-deleted concept."),
    C(sb_id="i9", title="Empty Body", collection="notes", body=""),
    # j10: body legitimately contains a "# Citations" heading as prose, but the
    # concept has NO sources — the parser must NOT strip it (regression: it did).
    C(sb_id="j10", title="Citations Word In Prose", collection="notes",
      body="Intro line.\n\n# Citations\n\nThis is my actual prose, not a source list."),
    # k11: purely non-ASCII title — slug is empty, path must fall back to sb_id
    # (not a colliding 'untitled.md').
    C(sb_id="k11", title="日本語のみ", collection=None, body="body"),
]


def norm_body(s):
    return (s or "").strip("\n").rstrip()


def main():
    failures = []
    for c in CONCEPTS:
        md = okf.to_markdown(c)
        back = okf.from_markdown(md, path=okf.concept_path(c))
        for k in KEYS:
            exp, got = c[k], back.get(k)
            if k == "body":
                if norm_body(exp) != norm_body(got):
                    failures.append(f"[{c['sb_id']}] body mismatch:\n  exp={norm_body(exp)!r}\n  got={norm_body(got)!r}")
                continue
            if exp != got:
                failures.append(f"[{c['sb_id']}] field {k!r}: exp={exp!r} got={got!r}")
    if failures:
        print("ROUNDTRIP FAIL:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print(f"ROUNDTRIP PASS: {len(CONCEPTS)} concepts round-tripped identically")


if __name__ == "__main__":
    main()
