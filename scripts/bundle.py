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


def _unlink_retry(p, attempts=10):
    """Unlink a file, tolerating brief Windows handle-release lag after a
    sqlite connection close."""
    import time
    for i in range(attempts):
        try:
            p.unlink()
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.05)
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


def _description(concept: dict) -> str:
    """A one-line description for index/log listings."""
    d = concept.get("description")
    if d:
        return d.strip()
    body = (concept.get("body") or "").strip()
    first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
    return (first[:97] + "…") if len(first) > 100 else first


def _iso_date(ts) -> str:
    """Extract a YYYY-MM-DD date from a timestamp string, else today (UTC)."""
    if ts and isinstance(ts, str) and len(ts) >= 10 and ts[4] == "-":
        return ts[:10]
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def export(brain: SecondBrain, bundle_dir) -> dict:
    """Write the entire brain (including soft-deleted drawers) as an OKF Bundle,
    with conformant reserved files (per-directory index.md, a root log.md, and an
    okf_version pin in the root index.md)."""
    bundle_dir = Path(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    rows = brain.con.execute("SELECT * FROM drawers ORDER BY created_at").fetchall()
    used: set = set()
    entries = []  # {rel, title, desc, collection, created}
    for row in rows:
        concept = _drawer_to_concept(brain, row)
        rel = _unique_path(concept, used)
        f = bundle_dir / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(okf.to_markdown(concept), encoding="utf-8")
        entries.append({
            "rel": rel, "title": concept["title"], "desc": _description(concept),
            "collection": (concept.get("collection") or "").strip("/"),
            "created": _iso_date(row["created_at"]),
        })

    _write_indexes(bundle_dir, entries)
    _write_log(bundle_dir, entries)
    return {"concepts": len(entries), "path": str(bundle_dir)}


def _write_indexes(bundle_dir: Path, entries: list) -> None:
    """Root index.md (okf_version pin + collections + root concepts) and one
    index.md per collection subdirectory. Per OKF §6, index.md carries no
    frontmatter except the root's okf_version declaration."""
    by_coll: dict = {}
    root_concepts = []
    for e in entries:
        if e["collection"]:
            by_coll.setdefault(e["collection"], []).append(e)
        else:
            root_concepts.append(e)

    # Subdirectory indexes.
    for coll, items in by_coll.items():
        lines = [f"# {coll}", ""]
        for e in sorted(items, key=lambda x: x["title"].lower()):
            name = Path(e["rel"]).name
            desc = f" - {e['desc']}" if e["desc"] else ""
            lines.append(f"* [{e['title']}]({name}){desc}")
        (bundle_dir / coll / "index.md").write_text("\n".join(lines) + "\n",
                                                    encoding="utf-8")

    # Root index.
    out = ['---', f'okf_version: "{okf.OKF_VERSION}"', '---', '']
    if by_coll:
        out += ["# Collections", ""]
        for coll in sorted(by_coll):
            n = len(by_coll[coll])
            out.append(f"* [{coll}]({coll}/) - {n} concept{'s' if n != 1 else ''}")
        out.append("")
    if root_concepts:
        out += ["# Concepts", ""]
        for e in sorted(root_concepts, key=lambda x: x["title"].lower()):
            desc = f" - {e['desc']}" if e["desc"] else ""
            out.append(f"* [{e['title']}]({Path(e['rel']).name}){desc}")
        out.append("")
    (bundle_dir / "index.md").write_text("\n".join(out).rstrip() + "\n",
                                         encoding="utf-8")


def _write_log(bundle_dir: Path, entries: list) -> None:
    """Root log.md: ISO date-grouped creation entries, newest date first (OKF §7)."""
    by_date: dict = {}
    for e in entries:
        by_date.setdefault(e["created"], []).append(e)
    lines = ["# Update Log", ""]
    for date in sorted(by_date, reverse=True):
        lines.append(f"## {date}")
        for e in sorted(by_date[date], key=lambda x: x["title"].lower()):
            lines.append(f"* **Creation**: [{e['title']}](/{e['rel']})")
        lines.append("")
    (bundle_dir / "log.md").write_text("\n".join(lines).rstrip() + "\n",
                                       encoding="utf-8")


# -- rebuild ---------------------------------------------------------------

def rebuild(bundle_dir, db_path) -> SecondBrain:
    """Build a FRESH brain.db from an OKF Bundle. Any existing db at db_path is
    replaced — the Bundle is authoritative."""
    bundle_dir = Path(bundle_dir)
    db_path = Path(db_path)
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            _unlink_retry(p)

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
