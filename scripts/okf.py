#!/usr/bin/env python3
"""OKF serializer — Concept ⇄ Open Knowledge Format markdown document.

OKF v0.1 (GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md): a Concept is one
markdown file = YAML frontmatter (required `type`) + markdown body, inside a
Bundle directory tree. This module is the canonical (de)serializer; it is
stdlib-only and round-trips a Concept losslessly, including our namespaced
`sb_*` psychological extensions.

Wire-format choices (all OKF-conformant):
- Frontmatter scalars are emitted raw when safe, else as JSON strings. JSON is a
  valid YAML subset, so any real YAML parser reads them, and we parse them back
  deterministically with json.loads.
- `tags` → inline JSON array. `sb_affect` / `sb_relations` → inline JSON.
- `sources` → an OKF `resource` (first URL) plus a `# Citations` section listing
  all URLs. Parsed back from the Citations section.
- `collection` is encoded by the file's directory (the OKF idiom: directory =
  grouping), recovered from the concept's path — not stored in frontmatter.

Canonical Concept dict (all keys present; absent optionals are None / []):
    sb_id, type, title, description, collection, tags, sources, timestamp, body,
    sb_subject, sb_valid_from, sb_valid_to, sb_supersedes, sb_affect,
    sb_relations, sb_deleted
"""
from __future__ import annotations

import json
import re

OKF_VERSION = "0.1"

# Field groups -------------------------------------------------------------
# Scalar string fields, emitted in this order in the frontmatter.
_SCALARS = [
    "type", "sb_id", "title", "description", "resource", "timestamp",
    "sb_subject", "sb_valid_from", "sb_valid_to", "sb_supersedes", "sb_deleted",
]
# JSON-valued fields.
_JSON_FIELDS = {"tags", "sb_affect", "sb_relations"}

_RAW_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]*$")
_CITATION_RE = re.compile(r"^\[\d+\]\s+(.*)$")


# -- identity / paths ------------------------------------------------------

def slugify(title: str) -> str:
    """Filesystem-safe, URL-friendly stem derived from a title. ASCII-folded;
    non-alphanumeric runs collapse to single hyphens."""
    s = (title or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s  # may be "" (e.g. a purely non-ASCII title); caller supplies fallback


def concept_path(concept: dict) -> str:
    """Bundle-relative file path for a Concept: `<collection>/<slug>.md`
    (or `<slug>.md` at the bundle root)."""
    # Fall back to sb_id (then "untitled") when a title has no ASCII slug, so two
    # non-ASCII-titled concepts in one collection don't collide on `untitled.md`.
    stem = slugify(concept.get("title") or "") or (concept.get("sb_id") or "untitled")
    coll = (concept.get("collection") or "").strip("/")
    return f"{coll}/{stem}.md" if coll else f"{stem}.md"


def concept_id(path: str) -> str:
    """OKF Concept ID: the bundle-relative path with the `.md` suffix removed."""
    return path[:-3] if path.endswith(".md") else path


# -- frontmatter scalar (de)serialization ----------------------------------

def _emit_scalar(v) -> str:
    """Render a scalar value for frontmatter: raw when safe, else JSON-quoted."""
    s = str(v)
    if _RAW_SAFE.match(s):
        return s
    return json.dumps(s, ensure_ascii=False)


def _parse_scalar(raw: str):
    """Inverse of _emit_scalar / _emit_json: JSON when it parses, else raw text."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return raw


# -- serialize -------------------------------------------------------------

def to_markdown(concept: dict) -> str:
    """Serialize a Concept dict to an OKF v0.1 markdown document."""
    sources = concept.get("sources") or []
    # Build the frontmatter field map in canonical order.
    fields: dict[str, str] = {}
    for key in _SCALARS:
        if key == "resource":
            if sources:
                fields["resource"] = _emit_scalar(sources[0])
            continue
        val = concept.get(key)
        if key == "type":
            val = val or "Note"  # OKF requires a non-empty type.
        if val is None or val == "":
            continue
        fields[key] = _emit_scalar(val)
    # JSON-valued fields.
    tags = concept.get("tags") or []
    if tags:
        fields["tags"] = json.dumps(tags, ensure_ascii=False)
    if concept.get("sb_affect") is not None:
        fields["sb_affect"] = json.dumps(concept["sb_affect"], ensure_ascii=False)
    if concept.get("sb_relations"):
        fields["sb_relations"] = json.dumps(concept["sb_relations"], ensure_ascii=False)

    lines = ["---"]
    # Preserve a stable, readable key order: type & sb_id first, then the rest.
    order = ["type", "sb_id", "title", "description", "resource", "tags",
             "timestamp", "sb_subject", "sb_valid_from", "sb_valid_to",
             "sb_supersedes", "sb_affect", "sb_relations", "sb_deleted"]
    for k in order:
        if k in fields:
            lines.append(f"{k}: {fields[k]}")
    lines.append("---")

    body = concept.get("body") or ""
    text = "\n".join(lines) + "\n\n" + body.rstrip("\n")

    if sources:
        cites = "\n".join(f"[{i}] {u}" for i, u in enumerate(sources, 1))
        text = text.rstrip("\n") + "\n\n# Citations\n\n" + cites
    return text.rstrip("\n") + "\n"


# -- parse -----------------------------------------------------------------

def _split(text: str):
    """Return (frontmatter_str, body_str) or (None, None) if not OKF-shaped."""
    if not text.startswith("---\n"):
        return None, None
    end = text.find("\n---", 4)
    if end == -1:
        return None, None
    return text[4:end], text[end + 4:]


def from_markdown(text: str, path: str | None = None) -> dict:
    """Parse an OKF markdown document into a canonical Concept dict.

    `path` (if given) supplies the `collection` via the OKF directory idiom.
    """
    fm_str, body = _split(text)
    if fm_str is None:
        raise ValueError("not an OKF document: missing frontmatter delimiters")

    fm: dict = {}
    for line in fm_str.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        if key in _JSON_FIELDS:
            try:
                fm[key] = json.loads(raw.strip())
            except (ValueError, json.JSONDecodeError):
                fm[key] = raw.strip()
        else:
            fm[key] = _parse_scalar(raw)

    # Body: drop a leading blank line gap, then split off a trailing Citations
    # section — but ONLY if it is a genuine `[n] url` list. A body that merely
    # contains the words "# Citations" as prose is left untouched (the section we
    # emit is always last and always numbered, so we match on the last heading
    # whose every non-blank line is a citation entry).
    body = body.lstrip("\n")
    sources: list = []
    if "# Citations" in body:
        body_part, _, cite_part = body.rpartition("# Citations")
        cite_lines = [ln.strip() for ln in cite_part.splitlines() if ln.strip()]
        if cite_lines and all(_CITATION_RE.match(ln) for ln in cite_lines):
            body = body_part
            sources = [_CITATION_RE.match(ln).group(1).strip() for ln in cite_lines]
    body = body.strip("\n")

    # collection from the path (OKF directory idiom), else None.
    collection = None
    if path and "/" in path:
        collection = path.rsplit("/", 1)[0]

    return {
        "sb_id": fm.get("sb_id"),
        "type": fm.get("type") or "Note",
        "title": fm.get("title"),
        "description": fm.get("description"),
        "collection": collection,
        "tags": fm.get("tags") or [],
        "sources": sources,
        "timestamp": fm.get("timestamp"),
        "body": body,
        "sb_subject": fm.get("sb_subject"),
        "sb_valid_from": fm.get("sb_valid_from"),
        "sb_valid_to": fm.get("sb_valid_to"),
        "sb_supersedes": fm.get("sb_supersedes"),
        "sb_affect": fm.get("sb_affect"),
        "sb_relations": fm.get("sb_relations") or [],
        "sb_deleted": fm.get("sb_deleted"),
    }


# -- tiny CLI for manual inspection ---------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        sample = {
            "sb_id": "demo1", "type": "Episode", "title": "A sample episode 中文",
            "collection": "episodes", "tags": ["demo", "private"],
            "timestamp": "2026-06-18T20:14:00Z", "sb_subject": "/people/self.md",
            "sb_affect": {"valence": -0.4, "arousal": 0.6, "emotion": "wistful",
                          "intensity": 0.7},
            "sources": ["https://example.com/x"],
            "body": "Body with a [[wikilink]] inside.",
        }
        md = to_markdown(sample)
        print(md)
        print("# concept_path:", concept_path(sample))
        print("# round-trips:", from_markdown(md, concept_path(sample)) is not None)
    else:
        # Read an OKF doc from stdin, print parsed JSON.
        print(json.dumps(from_markdown(sys.stdin.read()), indent=2, ensure_ascii=False))
