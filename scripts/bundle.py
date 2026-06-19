#!/usr/bin/env python3
"""Bundle export / rebuild — make the SQLite store disposable.

The OKF Bundle (a directory of Concept files) is the source of truth; brain.db
is a derived cache. `export` writes the whole brain out as an OKF Bundle;
`rebuild` walks a Bundle and reconstructs a fresh brain.db from it, losing
nothing — concepts, tags, sources, collections, soft-delete state, wikilink
relations, and the FTS index.

Until later gaps add real columns for the psychological layer (G08–G10), a
Concept's `type` and `sb_*` extension fields are stored in `concepts.metadata`
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
# Concept extension fields carried through concepts.metadata (besides okf_type).
_SB_FIELDS = ["sb_subject", "sb_valid_from", "sb_valid_to", "sb_supersedes",
              "sb_affect", "sb_relations", "description"]


# -- concept <-> concept ----------------------------------------------------

def _concept_to_concept(brain: SecondBrain, row) -> dict:
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
    """Pack non-column Concept fields back into concepts.metadata."""
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


def _prune_empty_dirs(bundle_dir: Path) -> None:
    """Remove now-empty subdirectories (e.g. a collection emptied by deletes,
    or an emptied .trash), but never the bundle root or .git."""
    for d in sorted(bundle_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if not d.is_dir() or ".git" in d.parts:
            continue
        try:
            next(d.iterdir())
        except StopIteration:
            d.rmdir()


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


def _read_sb_id(path: Path) -> str | None:
    """Cheaply read a concept file's sb_id from its frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    for line in text.split("\n")[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"sb_id:\s*(.*)$", line)
        if m:
            return m.group(1).strip().strip('"')
    return None


def export(brain: SecondBrain, bundle_dir) -> dict:
    """Write the brain as an OKF Bundle *incrementally* — only concept files that
    actually changed are rewritten, files for hard-deleted concepts are removed,
    and soft-deletes move to `.trash/`. This idempotence is what lets git merge
    a remote's edits cleanly: an unchanged concept is left byte-for-byte alone, so
    a remote delete/edit of it applies without a spurious local-overwrite conflict.

    Reserved index.md / log.md are regenerated deterministically (identical input
    → identical bytes → no git churn). Note: the caller must NOT run this on a
    device whose db is empty-but-bundle-is-full (a fresh clone) — sync.py guards
    that case, since here an empty db would (correctly) mean "remove everything".
    """
    bundle_dir = Path(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    rows = brain.con.execute("SELECT * FROM concepts ORDER BY created_at").fetchall()

    used: set = set()
    desired: dict = {}    # sb_id -> (actual_rel, text)
    entries = []          # live concepts only -> index/log
    for row in rows:
        concept = _concept_to_concept(brain, row)
        deleted = bool(concept.get("sb_deleted"))
        rel = _unique_path(concept, used)             # live-style path
        actual = f".trash/{rel}" if deleted else rel   # tombstones under .trash/
        desired[concept["sb_id"]] = (actual, okf.to_markdown(concept))
        if not deleted:
            entries.append({
                "rel": rel, "title": concept["title"], "desc": _description(concept),
                "collection": (concept.get("collection") or "").strip("/"),
                "date": _iso_date(row["updated_at"]),  # updated_at is round-trip-stable
            })

    # Map the current bundle: sb_id -> existing rel path.
    current: dict = {}
    for f in bundle_dir.rglob("*.md"):
        rel = f.relative_to(bundle_dir).as_posix()
        if (rel.startswith(".git/") or "/.git/" in rel
                or f.name in ("index.md", "log.md") or rel.endswith(".conflict.md")):
            continue  # conflict copies are opaque — never managed/removed by export
        sbid = _read_sb_id(f)
        if sbid:
            current[sbid] = rel

    # Apply desired state: move/write only what changed.
    for sbid, (actual, text) in desired.items():
        old = current.get(sbid)
        if old and old != actual:
            _unlink_retry(bundle_dir / old)            # e.g. live -> .trash move
        target = bundle_dir / actual
        if (not target.exists()) or target.read_text(encoding="utf-8") != text:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    # Remove files whose concept no longer exists in the db (local hard-delete).
    for sbid, rel in current.items():
        if sbid not in desired:
            _unlink_retry(bundle_dir / rel)
    _prune_empty_dirs(bundle_dir)

    _write_indexes(bundle_dir, entries)
    _write_log(bundle_dir, entries)
    return {"concepts": len(rows), "live": len(entries), "path": str(bundle_dir)}


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
        by_date.setdefault(e["date"], []).append(e)
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
        if rel.startswith(".git/") or "/.git/" in rel or rel.endswith(".conflict.md"):
            continue  # conflict copies await human resolution; not imported as concepts
        # Tombstones live under .trash/; strip the prefix so the original
        # collection is recovered from the path (sb_deleted drives the state).
        parse_path = rel[len(".trash/"):] if rel.startswith(".trash/") else rel
        concepts.append(okf.from_markdown(f.read_text(encoding="utf-8"), path=parse_path))

    # Insert all concepts first (so wikilink resolution sees the full set).
    for c in concepts:
        meta = _concept_to_meta(c)
        brain.con.execute(
            "INSERT INTO concepts (id, title, content, collection, sources, "
            "metadata, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, "
            "COALESCE(?, CURRENT_TIMESTAMP), ?)",
            (c["sb_id"] or _uuid(), c["title"], c["body"] or "", c["collection"],
             json.dumps(c["sources"] or []), json.dumps(meta),
             c["timestamp"], c["sb_deleted"]),
        )
        brain._set_tags(c["sb_id"], c["tags"] or [])

    # Re-derive wikilink relations + resolve cross-references for ALIVE concepts.
    for c in concepts:
        if c["sb_deleted"]:
            continue
        brain._sync_wikilinks(c["sb_id"], c["body"] or "")
    for c in concepts:
        if c["sb_deleted"]:
            continue
        brain._resolve_pending_to(c["sb_id"], c["title"])
    # Re-sync the derived subject index (subjects + concept_subject) from
    # concepts.metadata. This is the R10 path: a persona sub-graph query must
    # be correct after a bundle rebuild, with no separate state to keep aligned.
    brain.rebuild_subject_index()
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
