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
import os
import re
from pathlib import Path

import okf
import crypto
from brain import SecondBrain, VALID_REL_TYPES, _uuid  # noqa: F401

RESERVED = {"index", "log"}


def _encrypted_markdown(concept: dict, plaintext_md: str) -> str:
    """Wrap a private Concept's full OKF markdown in a minimal plaintext envelope
    whose body is the Fernet ciphertext. Only routing identity (type, sb_id) stays
    visible; title, body, and every sb_* field live inside the ciphertext. The
    envelope is itself a valid OKF document so the Bundle still indexes/rebuilds.
    `crypto.encrypt` raises EncryptionUnavailable if no backend/key — by design,
    so a refusal aborts export before any plaintext is written."""
    token = crypto.encrypt(plaintext_md)
    typ = concept.get("type") or "Note"
    return (f"---\n"
            f"type: {typ}\n"
            f"sb_id: {concept['sb_id']}\n"
            f"{crypto.MARKER}: {crypto.SCHEME}\n"
            f"---\n\n{token}\n")


def _maybe_decrypt(text: str) -> str:
    """If `text` is an encrypted Concept envelope (sb_encrypted marker in its
    frontmatter), decrypt the ciphertext body back to the original OKF markdown.
    Otherwise return it unchanged. Raises EncryptionUnavailable if a key is needed
    but absent — a rebuild must not silently drop private Concepts."""
    head = text[:400]
    if f"\n{crypto.MARKER}:" not in ("\n" + head):
        return text
    # frontmatter is delimited by the first two '---' lines; body is the token
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    front, body = parts[1], parts[2]
    if f"{crypto.MARKER}:" not in front:
        return text
    return crypto.decrypt(body.strip())


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


def _atomic_write_text(path: Path, text: str) -> None:
    """Replace one Bundle file atomically and durably where the OS permits."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
# Concept extension fields carried through concepts.metadata (besides okf_type).
_SB_FIELDS = ["sb_subject", "sb_valid_from", "sb_valid_to", "sb_supersedes",
              "sb_affect", "sb_obsidian_path", "sb_obsidian_frontmatter",
              "description"]


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
        "sb_obsidian_path": meta.get("sb_obsidian_path"),
        "sb_obsidian_frontmatter": meta.get("sb_obsidian_frontmatter") or [],
        "sb_relations": meta.get("sb_relations") or [],
        "sb_deleted": row["deleted_at"],
    }


def _concept_to_meta(concept: dict) -> dict:
    """Pack non-column Concept fields back into concepts.metadata.

    ``sb_relations`` is intentionally excluded: manual relations live in the
    relations table and are materialized into frontmatter only at export time.
    """
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

    # Encryption is OPT-IN: it engages only when a key is configured
    # (crypto.available()). Without a key, private Concepts are exported as
    # plaintext (legacy behavior) but a warning is emitted — UNLESS the user has
    # set SECONDBRAIN_REQUIRE_ENCRYPTION, in which case export REFUSES rather than
    # write private plaintext (the production-grade no-leak guarantee).
    enc_on = crypto.available()
    require_enc = str(os.environ.get("SECONDBRAIN_REQUIRE_ENCRYPTION", "")).lower() \
        in ("1", "true", "yes", "on")
    plaintext_private = 0

    used: set = set()
    prepared = []
    paths_by_id: dict[str, str] = {}
    for row in rows:
        concept = _concept_to_concept(brain, row)
        deleted = bool(concept.get("sb_deleted"))
        rel = _unique_path(concept, used)             # live-style path
        actual = f".trash/{rel}" if deleted else rel   # tombstones under .trash/
        prepared.append((row, concept, deleted, rel, actual))
        paths_by_id[concept["sb_id"]] = rel

    # OKF's typed-edge mirror is path-based. Build it from the authoritative
    # manual relation rows after every target path is known. A metadata value is
    # retained only as a compatibility bridge for databases rebuilt by older
    # versions, which stored sb_relations but did not materialize relation rows.
    manual_by_source: dict[str, list] = {}
    for relation in brain.con.execute(
        "SELECT from_id, to_id, relation_type, strength FROM relations "
        "WHERE source='manual' ORDER BY from_id, to_id"
    ).fetchall():
        target_path = paths_by_id.get(relation["to_id"])
        if target_path is None:
            raise ValueError(
                f"manual relation target {relation['to_id']!r} is missing from concepts"
            )
        manual_by_source.setdefault(relation["from_id"], []).append({
            "to": f"/{target_path}",
            "type": relation["relation_type"],
            "strength": relation["strength"],
        })

    # sb_id -> (actual_rel, plaintext_md, enc_meta).  enc_meta is None for a file
    # written verbatim, or (type, sb_id) for one to be encrypted at write time.
    desired: dict = {}
    entries = []          # live concepts only -> index/log
    for row, concept, deleted, rel, actual in prepared:
        if concept["sb_id"] in manual_by_source:
            concept["sb_relations"] = manual_by_source[concept["sb_id"]]
        text = okf.to_markdown(concept)
        enc_meta = None
        if crypto.is_private(concept):
            if enc_on:
                # Mark for encryption; the actual encrypt happens in the write
                # loop so it can be skipped when the plaintext is unchanged
                # (Fernet tokens are non-deterministic — re-encrypting every run
                # would churn git on every sync).
                enc_meta = (concept.get("type") or "Note", concept["sb_id"])
            elif require_enc:
                # Refuse BEFORE any file is written, so a refusal never leaves
                # private plaintext behind (the no-leak guarantee).
                raise crypto.EncryptionUnavailable(
                    f"Concept {concept['sb_id'][:8]} ({concept.get('title')!r}) is "
                    f"private but no encryption key is configured and "
                    f"SECONDBRAIN_REQUIRE_ENCRYPTION is set - refusing to export it as "
                    f"plaintext. Run `python scripts/crypto.py init` first.")
            else:
                plaintext_private += 1
        desired[concept["sb_id"]] = (actual, text, enc_meta)
        # Encrypted Concepts are excluded from the plaintext index.md / log.md so
        # their title + snippet never leak into the pushed bundle.
        if not deleted and enc_meta is None:
            entries.append({
                "rel": rel, "title": concept["title"], "desc": _description(concept),
                "collection": (concept.get("collection") or "").strip("/"),
                "date": _iso_date(row["updated_at"]),  # updated_at is round-trip-stable
            })

    if plaintext_private and not enc_on:
        import sys as _sys
        # ASCII-only: child stderr is cp1252 on Windows; a non-ASCII char here
        # would crash a UTF-8 reader of this process's stderr (the G19 class of bug).
        print(f"warning: {plaintext_private} private Concept(s) exported as PLAINTEXT "
              f"- no encryption key configured. Run `python scripts/crypto.py init` to "
              f"encrypt them, or set SECONDBRAIN_REQUIRE_ENCRYPTION=1 to refuse instead.",
              file=_sys.stderr)

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
    for sbid, (actual, plaintext, enc_meta) in desired.items():
        old = current.get(sbid)
        if old and old != actual:
            _unlink_retry(bundle_dir / old)            # e.g. live -> .trash move
        target = bundle_dir / actual
        if enc_meta is not None:
            # Idempotent encryption: if the existing file already decrypts to this
            # exact plaintext, leave its (stable) ciphertext untouched so an
            # unchanged private Concept produces no git churn. Only re-encrypt
            # when the plaintext actually changed.
            if target.exists():
                try:
                    if _maybe_decrypt(target.read_text(encoding="utf-8")) == plaintext:
                        continue
                except Exception:
                    pass  # unreadable/old-key envelope — re-encrypt fresh below
            typ, sid = enc_meta
            out_text = _encrypted_markdown({"type": typ, "sb_id": sid}, plaintext)
            _atomic_write_text(target, out_text)
        elif (not target.exists()) or target.read_text(encoding="utf-8") != plaintext:
            _atomic_write_text(target, plaintext)
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
        _atomic_write_text(bundle_dir / coll / "index.md", "\n".join(lines) + "\n")

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
    _atomic_write_text(bundle_dir / "index.md", "\n".join(out).rstrip() + "\n")


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
    _atomic_write_text(bundle_dir / "log.md", "\n".join(lines).rstrip() + "\n")


# -- rebuild ---------------------------------------------------------------

def _normalize_relation_path(value) -> str:
    """Normalize an OKF bundle-relative relation target for path lookup."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("sb_relations target 'to' must be a non-empty path")
    target = value.strip().replace("\\", "/")
    while target.startswith("./"):
        target = target[2:]
    target = target.lstrip("/")
    if target.startswith(".trash/"):
        target = target[len(".trash/"):]
    return target.casefold()


def _restore_manual_relations(brain: SecondBrain, concepts: list,
                              ids_by_path: dict[str, str]) -> None:
    """Validate and restore OKF ``sb_relations`` after all concepts exist."""
    seen: set[tuple[str, str]] = set()
    validated = []
    for concept in concepts:
        source_id = concept["sb_id"]
        relations = concept.get("sb_relations") or []
        if not isinstance(relations, list):
            raise ValueError(f"sb_relations for {source_id!r} must be a list")
        for relation in relations:
            if not isinstance(relation, dict):
                raise ValueError(f"sb_relations for {source_id!r} must contain objects")
            target_path = _normalize_relation_path(relation.get("to"))
            target_id = ids_by_path.get(target_path)
            if target_id is None:
                raise ValueError(
                    f"sb_relations target {relation.get('to')!r} from {source_id!r} "
                    "does not exist in the bundle"
                )
            if target_id == source_id:
                raise ValueError(f"sb_relations for {source_id!r} contains a self-loop")
            pair = (source_id, target_id)
            if pair in seen:
                raise ValueError(
                    f"sb_relations for {source_id!r} contains a duplicate target"
                )
            seen.add(pair)

            relation_type = relation.get("type", "related")
            if relation_type not in VALID_REL_TYPES:
                raise ValueError(f"invalid sb_relations type {relation_type!r}")
            strength = relation.get("strength", 0.5)
            if isinstance(strength, bool):
                raise ValueError("sb_relations strength must be a number from 0 to 1")
            try:
                strength = float(strength)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "sb_relations strength must be a number from 0 to 1"
                ) from exc
            if not 0.0 <= strength <= 1.0:
                raise ValueError("sb_relations strength must be a number from 0 to 1")
            validated.append((source_id, target_id, relation_type, strength))

    # Do not mutate the graph until every declaration has passed validation.
    brain.con.executemany(
        "INSERT INTO relations "
        "(id, from_id, to_id, relation_type, strength, source) "
        "VALUES (?, ?, ?, ?, ?, 'manual')",
        [(_uuid(), source_id, target_id, relation_type, strength)
         for source_id, target_id, relation_type, strength in validated],
    )


def _build_database(bundle_dir: Path, db_path: Path) -> SecondBrain:
    """Build and validate one new projection at an unused path."""
    concepts = []
    ids_by_path: dict[str, str] = {}
    for f in sorted(bundle_dir.rglob("*.md")):
        if f.name in ("index.md", "log.md"):
            continue
        rel = f.relative_to(bundle_dir).as_posix()
        if rel.startswith(".git/") or "/.git/" in rel or rel.endswith(".conflict.md"):
            continue
        parse_path = rel[len(".trash/"):] if rel.startswith(".trash/") else rel
        raw = _maybe_decrypt(f.read_text(encoding="utf-8"))
        concept = okf.from_markdown(raw, path=parse_path)
        concept["sb_id"] = concept.get("sb_id") or _uuid()
        path_key = _normalize_relation_path(parse_path)
        if path_key in ids_by_path:
            raise ValueError(f"duplicate concept path in bundle: {parse_path!r}")
        ids_by_path[path_key] = concept["sb_id"]
        concepts.append(concept)

    brain = SecondBrain(db_path)
    try:
        # Insert all concepts first so link resolution sees the full set.
        for c in concepts:
            meta = _concept_to_meta(c)
            brain.con.execute(
                "INSERT INTO concepts (id, title, content, collection, sources, "
                "metadata, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, "
                "COALESCE(?, CURRENT_TIMESTAMP), ?)",
                (c["sb_id"], c["title"], c["body"] or "", c["collection"],
                 json.dumps(c["sources"] or []), json.dumps(meta),
                 c["timestamp"], c["sb_deleted"]),
            )
            brain._set_tags(c["sb_id"], c["tags"] or [])

        for c in concepts:
            if not c["sb_deleted"]:
                brain._sync_wikilinks(c["sb_id"], c["body"] or "")
        for c in concepts:
            if not c["sb_deleted"]:
                brain._resolve_pending_to(c["sb_id"], c["title"])
        _restore_manual_relations(brain, concepts, ids_by_path)
        brain.rebuild_subject_index()
        brain.rebuild_affect_index()
        brain.rebuild_validity_index()
        brain.con.commit()
        return brain
    except BaseException:
        brain.close()
        raise


def rebuild(bundle_dir, db_path) -> SecondBrain:
    """Atomically replace a SQLite projection from an authoritative Bundle.

    Parsing, decryption, validation, and index construction happen in a sibling
    temporary database. A malformed Bundle therefore leaves an existing target
    untouched and does not leak a locked partial database on Windows.
    """
    bundle_dir = Path(bundle_dir)
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = db_path.with_name(
        f".{db_path.name}.rebuild-{os.getpid()}-{_uuid()}.tmp"
    )
    staged = None
    try:
        staged = _build_database(bundle_dir, temporary)
        staged.checkpoint_and_close()
        staged = None
        # Windows rejects FlushFileBuffers on a read-only descriptor; open the
        # fully staged SQLite file read/write for the durability flush.
        with temporary.open("rb+") as handle:
            os.fsync(handle.fileno())

        # A valid staged projection now exists. Remove only SQLite sidecars;
        # os.replace keeps the previous main DB intact until the final swap.
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(db_path) + suffix)
            if sidecar.exists():
                _unlink_retry(sidecar)
        os.replace(temporary, db_path)
        return SecondBrain(db_path)
    finally:
        if staged is not None:
            staged.close()
        for suffix in ("", "-wal", "-shm", "-journal"):
            artifact = Path(str(temporary) + suffix)
            try:
                artifact.unlink()
            except FileNotFoundError:
                pass


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
