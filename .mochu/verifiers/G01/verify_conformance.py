#!/usr/bin/env python3
"""G01 verifier — OKF v0.1 conformance of emitted Concept documents.

Claim: every markdown document the serializer emits conforms to OKF v0.1 §9:
(1) a parseable YAML frontmatter block delimited by `---`, (2) a non-empty
`type` field, plus our invariants: (3) `sb_id` present, (4) path↔id rule
(concept_id == path minus `.md`), (5) `collection` maps to a subdirectory in
the path, (6) sources surface as an OKF `resource` + `# Citations` section,
(7) `timestamp` is ISO-8601 when present.

Validation reads the emitted TEXT directly (not via okf.from_markdown), so it
is an independent check, not a tautology against our own parser. Exits nonzero
on any violation.
"""
import sys, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
import okf  # noqa: E402

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

SAMPLES = [
    {"sb_id": "x1", "type": "Note", "title": "Alpha", "collection": "notes",
     "tags": ["a"], "sources": [], "sb_relations": [],
     "body": "b", "timestamp": "2026-06-18T20:14:00Z"},
    {"sb_id": "x2", "type": "Episode", "title": "Beta 中文",
     "collection": "episodes", "tags": [], "sources": ["https://e.com/1",
     "https://e.com/2"], "sb_relations": [], "body": "body",
     "sb_subject": "/people/rox.md", "timestamp": "2026-06-18T20:14:00Z",
     "sb_affect": {"valence": -0.3, "arousal": 0.5}},
    {"sb_id": "x3", "type": "Note", "title": "Root Item", "collection": None,
     "tags": [], "sources": [], "sb_relations": [], "body": "at root"},
]


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return None, None
    end = text.find("\n---", 4)
    if end == -1:
        return None, None
    fm = text[4:end]
    body = text[end + 4:]
    return fm, body


def fm_get(fm, key):
    """Independent shallow YAML scan for a top-level scalar key."""
    for line in fm.splitlines():
        m = re.match(rf"^{re.escape(key)}:\s*(.*)$", line)
        if m:
            return m.group(1).strip()
    return None


def main():
    fails = []
    for c in SAMPLES:
        path = okf.concept_path(c)
        text = okf.to_markdown(c)

        # (1) frontmatter delimited and present
        fm, body = split_frontmatter(text)
        if fm is None:
            fails.append(f"[{c['sb_id']}] no parseable frontmatter block")
            continue

        # (2) non-empty type  (OKF §9 hard requirement)
        t = fm_get(fm, "type")
        if not t or t.strip().strip('"') == "":
            fails.append(f"[{c['sb_id']}] missing/empty required `type`")

        # (3) sb_id present
        if not fm_get(fm, "sb_id"):
            fails.append(f"[{c['sb_id']}] missing `sb_id`")

        # (4) path↔id rule
        cid = okf.concept_id(path)
        if cid != path[:-3] or not path.endswith(".md"):
            fails.append(f"[{c['sb_id']}] path↔id rule broken: path={path} id={cid}")

        # (5) collection → subdirectory
        if c["collection"]:
            if not path.startswith(c["collection"].strip("/") + "/"):
                fails.append(f"[{c['sb_id']}] collection {c['collection']!r} not a path dir: {path}")
        else:
            if "/" in path:
                fails.append(f"[{c['sb_id']}] no collection but path is nested: {path}")

        # (6) sources → resource + Citations
        if c["sources"]:
            if fm_get(fm, "resource") is None:
                fails.append(f"[{c['sb_id']}] has sources but no `resource` in frontmatter")
            if "# Citations" not in body:
                fails.append(f"[{c['sb_id']}] has sources but no `# Citations` section")
            for u in c["sources"]:
                if u not in body:
                    fails.append(f"[{c['sb_id']}] source {u} missing from Citations")

        # (7) timestamp ISO-8601 when present
        ts = fm_get(fm, "timestamp")
        if ts and not ISO.match(ts.strip().strip('"')):
            fails.append(f"[{c['sb_id']}] timestamp not ISO-8601: {ts}")

    # OKF version pin available
    if getattr(okf, "OKF_VERSION", None) != "0.1":
        fails.append("okf.OKF_VERSION must be '0.1'")

    if fails:
        print("CONFORMANCE FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"CONFORMANCE PASS: {len(SAMPLES)} documents conform to OKF v0.1")


if __name__ == "__main__":
    main()
