#!/usr/bin/env python3
"""Bundle export / rebuild — make the SQLite store disposable.

The OKF Bundle (a directory of Concept files) is the source of truth; brain.db
is a derived cache. `export` writes the whole brain out as an OKF Bundle;
`rebuild` walks a Bundle and reconstructs a fresh brain.db from it, losing
nothing — drawers, tags, sources, collections, soft-delete state, wikilink
relations, and the FTS index.

Until later gaps add real columns for the psychological layer (G08–G10), a
Concept's `type` and `sb_*` extension fields are stored in `drawers.metadata`
so the round-trip stays lossless without a schema change.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import okf
from brain import SecondBrain, _uuid  # noqa: F401

RESERVED = {"index", "log"}
# Concept extension fields carried through drawers.metadata (besides okf_type).
_SB_FIELDS = ["sb_subject", "sb_valid_from", "sb_valid_to", "sb_supersedes",
              "sb_affect", "sb_relations", "description"]


# -- drawer <-> concept ----------------------------------------------------

def _drawer_to_concept(brain: SecondBrain, row) -> dict:
    meta = json.loads(row["metadata"] or "{}")
    return {
        "sb_id": row["id"],
        "type": meta.get("okf_type", "Note"),
        "title": row["title"],
        "description": meta.get("description"),
        "collection": row["collection"],
        "tags": brain._tags_for(row["id"]),
        "sources": json.loads(row["sources"] or "[]"),
        "timestamp": row["updated_at"],
        "body": row["content"],
        "sb_subject": meta.get("sb_subject"),
        "sb_valid_from": meta.get("sb_valid_from"),
        "sb_valid_to": meta.get("sb_valid_to"),
        "sb_supersedes": meta.get("sb_supersedes"),
        "sb_affect": meta.get("sb_affect"),
        "sb_relations": meta.get("sb_relations") or [],
        "sb_deleted": row["deleted_at"],
    }


def _concept_to_meta(concept: dict) -> dict:
    """Pack non-column Concept fields back into drawers.metadata."""
    meta = {}
    if concept.get("type") and concept["type"] != "Note":
        meta["okf_type"] = concept["type"]
    for k in _SB_FIELDS:
        v = concept.get(k)
        if v not in (None, [], {}):
            meta[k] = v
    return meta


# -- export ----------------------------------------------------------------

def _unique_path(concept: dict, used: set) -> str:
    """OKF path for a concept, disambiguated against collisions and reserved
    filenames (index.md / log.md)."""
    coll = (concept.get("collection") or "").strip("/")
    stem = okf.slugify(concept.get("title") or "") or (concept.get("sb_id") or "untitled")
    if stem in RESERVED:
        stem = f"{stem}_{(concept.get('sb_id') or '')[:8] or 'x'}"
    base = f"{coll}/{stem}" if coll else stem
    path = f"{base}.md"
    if path in used:
        path = f"{base}_{(concept.get('sb_id') or _uuid())[:8]}.md"
    used.add(path)
    return path


def export(brain: SecondBrain, bundle_dir) -> dict:
    """Write the entire brain (including soft-deleted drawers) as an OKF Bundle."""
    bundle_dir = Path(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    rows = brain.con.execute("SELECT * FROM drawers ORDER BY created_at").fetchall()
    used: set = set()
    n = 0
    for row in rows:
        concept = _drawer_to_concept(brain, row)
        rel = _unique_path(concept, used)
        f = bundle_dir / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(okf.to_markdown(concept), encoding="utf-8")
        n += 1
    return {"concepts": n, "path": str(bundle_dir)}


# -- rebuild ---------------------------------------------------------------

def rebuild(bundle_dir, db_path) -> SecondBrain:
    """Build a FRESH brain.db from an OKF Bundle. Any existing db at db_path is
    replaced — the Bundle is authoritative."""
    bundle_dir = Path(bundle_dir)
    db_path = Path(db_path)
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()

    brain = SecondBrain(db_path)
    concepts = []
    for f in sorted(bundle_dir.rglob("*.md")):
        if f.name in ("index.md", "log.md"):
            continue
        rel = f.relative_to(bundle_dir).as_posix()
        concepts.append(okf.from_markdown(f.read_text(encoding="utf-8"), path=rel))

    # Insert all drawers first (so wikilink resolution sees the full set).
    for c in concepts:
        meta = _concept_to_meta(c)
        brain.con.execute(
            "INSERT INTO drawers (id, title, content, collection, sources, "
            "metadata, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, "
            "COALESCE(?, CURRENT_TIMESTAMP), ?)",
            (c["sb_id"] or _uuid(), c["title"], c["body"] or "", c["collection"],
             json.dumps(c["sources"] or []), json.dumps(meta),
             c["timestamp"], c["sb_deleted"]),
        )
        brain._set_tags(c["sb_id"], c["tags"] or [])

    # Re-derive wikilink relations + resolve cross-references for ALIVE drawers.
    for c in concepts:
        if c["sb_deleted"]:
            continue
        brain._sync_wikilinks(c["sb_id"], c["body"] or "")
    for c in concepts:
        if c["sb_deleted"]:
            continue
        brain._resolve_pending_to(c["sb_id"], c["title"])
    brain.con.commit()
    return brain


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "export":
        b = SecondBrain()
        print(export(b, sys.argv[2]))
    elif len(sys.argv) >= 3 and sys.argv[1] == "rebuild":
        rebuild(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else SecondBrain().db_path)
        print("rebuilt")
    else:
        print("usage: bundle.py export <dir> | rebuild <dir> <db>")
