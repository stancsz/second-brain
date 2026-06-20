#!/usr/bin/env python3
"""SecondBrain v3.0 — local knowledge graph for AI agents (OKF v0.1).

One file, stdlib only (sqlite3 + json + uuid + re). No external deps for Phase 1.
Every /brain-* command maps to a method here. The CLI wrapper is brain_cli.py.

v3.0 renames the underlying table from `drawers` to `concepts` to align
with OKF v0.1 canonical naming. A v2.1 brain.db is auto-migrated on
open via SecondBrain._migrate_v21_to_concepts(): the table is renamed
in place, the FTS5 index is rebuilt, and the triggers are replaced.
The CLI (brain_cli.py) + bundle (bundle.py) + sync (sync.py) +
hooks (capture_conversation.py, recall_memories.py) all use the new
"concept" naming in this release. The remaining R4 surface is
docs/references/commands/CHANGELOG; tracked in M3.

Design decisions worth knowing:
- Soft-deleted concepts are excluded from EVERY read path. There is one helper,
  _alive(), and all queries go through views/filters that use it.
- Wikilinks resolve at WRITE time and the resolved target id is frozen into the
  relation row. Editing some *other* concept later never silently re-points an
  existing link. (This fixes the v2 "most recently updated wins, forever" drift.)
- Unresolved [[links]] go to the pending_links table. When a concept is created or
  retitled, we resolve any pending links pointing at its title in one indexed query.
"""

import json
import re
import sqlite3
import uuid
from datetime import date as _date
from pathlib import Path

DB_PATH = Path.home() / ".secondbrain" / "brain.db"
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
VALID_REL_TYPES = {"references", "contradicts", "expands", "related"}

# Sentinel for "argument not passed" — distinguishes None (explicit clear) from
# omitted (leave alone). Used by update() to avoid clobbering sb_subject when
# the caller didn't intend to change it.
_UNSET = object()


def _uuid() -> str:
    return uuid.uuid4().hex


class SecondBrain:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.db_path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema()

    def _ensure_schema(self):
        self._migrate_v21_to_concepts()
        schema = (Path(__file__).parent / "schema.sql").read_text()
        self.con.executescript(schema)
        self.con.commit()

    def _migrate_v21_to_concepts(self):
        """One-shot v2.1 -> v3.0 schema migration.

        v2.1 had `drawers` as the table name; v3.0 (OKF v0.1) renames it
        to `concepts`. SQLite's ALTER TABLE RENAME updates indexes
        automatically and the FTS5 content= reference, but the FTS5
        virtual table itself, the FTS5 internal shadow tables, and the
        triggers all keep their old names + stale SQL bodies pointing
        at the old FTS5 table. We have to:

          1. ALTER TABLE drawers RENAME TO concepts
          2. DROP the old FTS5 virtual table (drawers_fts)
          3. DROP the old triggers (drawers_ai/ad/au — SQLite's
             ALTER TABLE RENAME updated their `ON` clause but their
             body still references `drawers_fts`)
          4. CREATE the new FTS5 + new triggers (these match what
             schema.sql will do, but we do it here so we can rebuild
             the index from the renamed base table in step 5)
          5. Rebuild the FTS5 index from the renamed base table

        After this function returns, schema.sql is run by the caller.
        All its CREATE statements use IF NOT EXISTS, so they are
        no-ops on a DB that the migration has just upgraded.

        Idempotent: if `concepts` already exists, do nothing. If neither
        `concepts` nor `drawers` exists, do nothing (fresh DB; the
        schema.sql will create everything)."""
        has_concepts = self.con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='concepts'"
        ).fetchone() is not None
        has_drawers = self.con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='drawers'"
        ).fetchone() is not None
        if has_concepts or not has_drawers:
            return  # already migrated, or fresh DB
        # 1. rename base table
        self.con.execute("ALTER TABLE drawers RENAME TO concepts")
        # 2. drop old FTS5 virtual table (also drops its shadow tables)
        self.con.execute("DROP TABLE IF EXISTS drawers_fts")
        # 3. drop old triggers — SQLite's ALTER TABLE updated the
        # `ON` clause (now `ON concepts`) but left the body referring
        # to the dropped `drawers_fts` table, so the triggers would
        # fail at next insert/update/delete.
        self.con.executescript(
            "DROP TRIGGER IF EXISTS drawers_ai;\n"
            "DROP TRIGGER IF EXISTS drawers_ad;\n"
            "DROP TRIGGER IF EXISTS drawers_au;\n"
        )
        # 4. create the v3.0 FTS5 + triggers
        self.con.executescript(
            "CREATE VIRTUAL TABLE IF NOT EXISTS concepts_fts USING fts5(\n"
            "    title, content,\n"
            "    content=concepts,\n"
            "    content_rowid=rowid\n"
            ");\n"
            "CREATE TRIGGER IF NOT EXISTS concepts_ai AFTER INSERT ON concepts BEGIN\n"
            "  INSERT INTO concepts_fts(rowid, title, content)\n"
            "  VALUES (new.rowid, new.title, new.content);\n"
            "END;\n"
            "CREATE TRIGGER IF NOT EXISTS concepts_ad AFTER DELETE ON concepts BEGIN\n"
            "  INSERT INTO concepts_fts(concepts_fts, rowid, title, content)\n"
            "  VALUES ('delete', old.rowid, old.title, old.content);\n"
            "END;\n"
            "CREATE TRIGGER IF NOT EXISTS concepts_au AFTER UPDATE ON concepts BEGIN\n"
            "  INSERT INTO concepts_fts(concepts_fts, rowid, title, content)\n"
            "  VALUES ('delete', old.rowid, old.title, old.content);\n"
            "  INSERT INTO concepts_fts(rowid, title, content)\n"
            "  VALUES (new.rowid, new.title, new.content);\n"
            "END;\n"
        )
        # 5. rebuild FTS5 from the renamed base table
        self.con.execute("INSERT INTO concepts_fts(concepts_fts) VALUES('rebuild')")
        self.con.commit()

    # -- internal helpers ---------------------------------------------------

    def _row_to_concept(self, row) -> dict:
        d = dict(row)
        d["sources"] = json.loads(d.get("sources") or "[]")
        d["metadata"] = json.loads(d.get("metadata") or "{}")
        d["tags"] = self._tags_for(d["id"])
        return d

    def _tags_for(self, concept_id: str) -> list:
        rows = self.con.execute(
            "SELECT t.name FROM tags t JOIN concept_tags dt ON dt.tag_id = t.id "
            "WHERE dt.concept_id = ? ORDER BY t.name",
            (concept_id,),
        ).fetchall()
        return [r["name"] for r in rows]

    def _resolve_title(self, title: str) -> str | None:
        """Resolve a [[title]] to a concept id. Exact (case-insensitive) match,
        most-recently-updated on ambiguity. Returns None if no live match."""
        row = self.con.execute(
            "SELECT id FROM concepts WHERE title = ? COLLATE NOCASE "
            "AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 1",
            (title.strip(),),
        ).fetchone()
        return row["id"] if row else None

    def _upsert_tag(self, name: str) -> str:
        name = name.strip()
        row = self.con.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        tid = _uuid()
        self.con.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (tid, name))
        return tid

    def _set_tags(self, concept_id: str, tags: list):
        self.con.execute("DELETE FROM concept_tags WHERE concept_id = ?", (concept_id,))
        for name in tags or []:
            if not name.strip():
                continue
            tid = self._upsert_tag(name)
            self.con.execute(
                "INSERT OR IGNORE INTO concept_tags (concept_id, tag_id) VALUES (?, ?)",
                (concept_id, tid),
            )

    def _sync_wikilinks(self, concept_id: str, content: str):
        """Re-derive wikilink relations for one concept from its content.
        Deletes only this concept's source='wikilink' edges, never manual ones.
        Unresolved targets land in pending_links."""
        self.con.execute(
            "DELETE FROM relations WHERE from_id = ? AND source = 'wikilink'",
            (concept_id,),
        )
        self.con.execute("DELETE FROM pending_links WHERE from_id = ?", (concept_id,))
        seen = set()
        for raw in WIKILINK_RE.findall(content or ""):
            title = raw.strip()
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            target = self._resolve_title(title)
            if target and target != concept_id:
                self.con.execute(
                    "INSERT OR IGNORE INTO relations "
                    "(id, from_id, to_id, relation_type, strength, source) "
                    "VALUES (?, ?, ?, 'references', 0.5, 'wikilink')",
                    (_uuid(), concept_id, target),
                )
            elif not target:
                self.con.execute(
                    "INSERT OR IGNORE INTO pending_links (id, from_id, target_title) "
                    "VALUES (?, ?, ?)",
                    (_uuid(), concept_id, title),
                )

    def _resolve_pending_to(self, concept_id: str, title: str):
        """A concept named `title` now exists (id=concept_id). Convert any pending
        links pointing at this title into real wikilink relations."""
        rows = self.con.execute(
            "SELECT id, from_id FROM pending_links WHERE target_title = ? COLLATE NOCASE",
            (title.strip(),),
        ).fetchall()
        for r in rows:
            if r["from_id"] == concept_id:
                continue
            self.con.execute(
                "INSERT OR IGNORE INTO relations "
                "(id, from_id, to_id, relation_type, strength, source) "
                "VALUES (?, ?, ?, 'references', 0.5, 'wikilink')",
                (_uuid(), r["from_id"], concept_id),
            )
            self.con.execute("DELETE FROM pending_links WHERE id = ?", (r["id"],))

    # -- CRUD ----------------------------------------------------------------

    def add(self, title, content, collection=None, tags=None, sources=None,
            sb_subject=None, sb_affect=None, sb_valid_from=None, sb_valid_to=None,
            sb_supersedes=None):
        did = _uuid()
        meta = {}
        if sb_subject:
            meta["sb_subject"] = sb_subject
        if sb_affect:
            meta["sb_affect"] = sb_affect
        if sb_valid_from:
            meta["sb_valid_from"] = sb_valid_from
        if sb_valid_to:
            meta["sb_valid_to"] = sb_valid_to
        if sb_supersedes:
            meta["sb_supersedes"] = sb_supersedes
        self.con.execute(
            "INSERT INTO concepts (id, title, content, collection, sources, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (did, title, content, collection, json.dumps(sources or []),
             json.dumps(meta)),
        )
        self._set_tags(did, tags or [])
        self._sync_wikilinks(did, content)
        self._resolve_pending_to(did, title)
        self._sync_subject_index_for(did)
        self._sync_affect_for(did, sb_affect)
        self._sync_validity_for(did, sb_valid_from, sb_valid_to, sb_supersedes)
        self.con.commit()
        return self.get(did)

    # -- subjects (G08 / R10) -------------------------------------------------

    DEFAULT_SUBJECT_PATH = "/people/self.md"

    def _normalize_subject(self, sb_subject: str | None) -> str:
        """Return the canonical subject id to use (defaults to /people/self.md).

        A subject id is a Bundle path. The OKF Concept's path IS its identity,
        so this is the same string the user's `sb_subject:` frontmatter holds.
        """
        if sb_subject and sb_subject.strip():
            return sb_subject.strip()
        return self.DEFAULT_SUBJECT_PATH

    def _ensure_subject(self, subject_id: str, display_name: str | None = None) -> None:
        """UPSERT a subject row. Creates a virtual row when no Person Concept exists."""
        slug = subject_id.rstrip(".md").rsplit("/", 1)[-1] or subject_id
        name = display_name or slug
        self.con.execute(
            "INSERT INTO subjects (sb_id, slug, display_name, kind) "
            "VALUES (?, ?, ?, 'Person') "
            "ON CONFLICT(sb_id) DO UPDATE SET "
            "  display_name = COALESCE(excluded.display_name, subjects.display_name)",
            (subject_id, slug, name),
        )

    def _sync_subject_index_for(self, concept_id: str, sb_subject: str | None = None) -> None:
        """Update the derived `subjects` and `concept_subject` tables for one concept.

        If sb_subject is None, reads from concepts.metadata (used by the live add
        path). If the concept has no sb_subject, defaults to /people/self.md.
        """
        if sb_subject is None:
            row = self.con.execute(
                "SELECT metadata FROM concepts WHERE id=?", (concept_id,)
            ).fetchone()
            if not row:
                return
            try:
                meta = json.loads(row["metadata"] or "{}")
            except (ValueError, TypeError):
                meta = {}
            sb_subject = meta.get("sb_subject")
        subject_id = self._normalize_subject(sb_subject)
        # If the subject points at a real Person Concept, prefer its title.
        person = self.con.execute(
            "SELECT title FROM concepts WHERE id=? AND deleted_at IS NULL", (subject_id,)
        ).fetchone()
        if person:
            self._ensure_subject(subject_id, person["title"])
        else:
            self._ensure_subject(subject_id)
        self.con.execute(
            "INSERT OR IGNORE INTO concept_subject (concept_id, subject_id) "
            "VALUES (?, ?)",
            (concept_id, subject_id),
        )

    def rebuild_subject_index(self) -> tuple[int, int]:
        """Full re-sync of subjects + concept_subject from concepts.metadata.

        Used by bundle.rebuild() after a full import. Returns
        (subjects_count, links_count) for diagnostics.
        """
        self.con.execute("DELETE FROM concept_subject")
        self.con.execute("DELETE FROM subjects")
        rows = self.con.execute(
            "SELECT id, title, collection, metadata, deleted_at FROM concepts"
        ).fetchall()
        # First pass: identify Person Concepts and their canonical paths.
        # A Person Concept's own subject IS its own Bundle path — it appears
        # in its own sub-graph by design.
        person_paths: dict[str, str] = {}  # path -> concept id
        for r in rows:
            if r["deleted_at"]:
                continue
            try:
                meta = json.loads(r["metadata"] or "{}")
            except (ValueError, TypeError):
                meta = {}
            if meta.get("okf_type") == "Person" and r["collection"]:
                path = f"/{r['collection']}/{r['title'].lower()}.md"
                person_paths[path] = r["id"]
        for path, cid in person_paths.items():
            # Use the Person Concept's title as the display name
            person_title = self.con.execute(
                "SELECT title FROM concepts WHERE id=?", (cid,)
            ).fetchone()["title"]
            self._ensure_subject(path, person_title)
        # /people/self.md always exists (default subject)
        self._ensure_subject(self.DEFAULT_SUBJECT_PATH, "self")
        # Second pass: link every non-Person concept to its subject. Person
        # Concepts are the SUBJECT themselves — they are listed in `subjects`
        # so users can enumerate people, but they are NOT members of their own
        # sub-graph (the sub-graph is "memories about this person", not the
        # person). We use INSERT OR IGNORE for the subject row so we never
        # clobber the display_name set in the first pass.
        links = 0
        for r in rows:
            if r["deleted_at"]:
                continue
            try:
                meta = json.loads(r["metadata"] or "{}")
            except (ValueError, TypeError):
                meta = {}
            if r["id"] in person_paths.values():
                # Person Concept: is the subject itself, not a member of it.
                continue
            subject_id = self._normalize_subject(meta.get("sb_subject"))
            self.con.execute(
                "INSERT OR IGNORE INTO subjects (sb_id, slug, kind) VALUES (?, ?, 'Person')",
                (subject_id, subject_id.rstrip(".md").rsplit("/", 1)[-1] or subject_id),
            )
            self.con.execute(
                "INSERT OR IGNORE INTO concept_subject (concept_id, subject_id) "
                "VALUES (?, ?)",
                (r["id"], subject_id),
            )
            links += 1
        self.con.commit()
        return len(person_paths) + 1, links

    def subjects(self) -> list[dict]:
        """All registered subjects (Person Concepts + the default 'self')."""
        rows = self.con.execute(
            "SELECT s.sb_id, s.slug, s.display_name, s.kind, "
            "       (SELECT COUNT(*) FROM concept_subject cs "
            "        WHERE cs.subject_id = s.sb_id) AS concept_count "
            "FROM subjects s ORDER BY s.display_name"
        ).fetchall()
        return [dict(r) for r in rows]

    def subject_subgraph(self, subject_id: str) -> list[dict]:
        """Return all live concepts for the given subject (Bundle path or normalized).

        Per R10, a persona sub-graph query returns exactly that subject's Concepts.
        Excludes soft-deleted concepts and concepts belonging to other subjects.
        Empty list for unknown subjects (does not raise).
        """
        subject_id = self._normalize_subject(subject_id)
        rows = self.con.execute(
            "SELECT d.* FROM concepts d "
            "JOIN concept_subject cs ON cs.concept_id = d.id "
            "WHERE cs.subject_id = ? AND d.deleted_at IS NULL "
            "ORDER BY d.updated_at DESC",
            (subject_id,),
        ).fetchall()
        return [self._row_to_concept(r) for r in rows]

    # -- structured affect (G10 / R12) ----------------------------------------

    _AFFECT_DIMS = ("valence", "arousal", "emotion", "intensity")

    def _normalize_affect(self, sb_affect) -> tuple | None:
        """Coerce an `sb_affect` mapping to a (valence, arousal, emotion, intensity)
        tuple, or None when there is no affect to record.

        Each dimension is optional: a memory may name an `emotion` without scoring
        it, or score `valence` alone. Non-numeric scores are dropped to None rather
        than raising — a corrupt frontmatter value must not crash a rebuild. An
        empty / all-missing mapping yields None (→ no affect row).
        """
        if not sb_affect or not isinstance(sb_affect, dict):
            return None

        def _num(v):
            if v is None or v == "":
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        valence = _num(sb_affect.get("valence"))
        arousal = _num(sb_affect.get("arousal"))
        intensity = _num(sb_affect.get("intensity"))
        emotion = sb_affect.get("emotion")
        emotion = str(emotion) if emotion not in (None, "") else None
        if valence is None and arousal is None and intensity is None and emotion is None:
            return None
        return (valence, arousal, emotion, intensity)

    def _sync_affect_for(self, concept_id: str, sb_affect) -> None:
        """Upsert (or, when there is no affect, delete) one Concept's affect row."""
        row = self._normalize_affect(sb_affect)
        if row is None:
            self.con.execute("DELETE FROM affect WHERE concept_id=?", (concept_id,))
            return
        valence, arousal, emotion, intensity = row
        self.con.execute(
            "INSERT INTO affect (concept_id, valence, arousal, emotion, intensity) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(concept_id) DO UPDATE SET "
            "  valence=excluded.valence, arousal=excluded.arousal, "
            "  emotion=excluded.emotion, intensity=excluded.intensity",
            (concept_id, valence, arousal, emotion, intensity),
        )

    def rebuild_affect_index(self) -> int:
        """Full re-sync of the affect table from concepts.metadata.sb_affect.

        Used by bundle.rebuild() after a full import. Returns the affect-row count.
        """
        self.con.execute("DELETE FROM affect")
        n = 0
        for r in self.con.execute(
            "SELECT id, metadata, deleted_at FROM concepts"
        ).fetchall():
            if r["deleted_at"]:
                continue
            try:
                meta = json.loads(r["metadata"] or "{}")
            except (ValueError, TypeError):
                meta = {}
            if self._normalize_affect(meta.get("sb_affect")) is not None:
                self._sync_affect_for(r["id"], meta.get("sb_affect"))
                n += 1
        self.con.commit()
        return n

    def affect(self, concept_id: str) -> dict | None:
        """Return the structured affect dict for a Concept, or None if it has none.

        Keys: valence, arousal, emotion, intensity. Any dimension may be None.
        """
        r = self.con.execute(
            "SELECT valence, arousal, emotion, intensity FROM affect WHERE concept_id=?",
            (concept_id,),
        ).fetchone()
        return dict(r) if r else None

    def recall_by_affect(self, emotion=None, min_valence=None, max_valence=None,
                         min_arousal=None, max_arousal=None, min_intensity=None,
                         limit=50) -> list[dict]:
        """Recall live Concepts filtered by structured affect.

        Categorical (`emotion`, case-insensitive exact match) and numeric range
        bounds, all combinable. A NULL dimension never satisfies a numeric bound
        (so a partially-scored memory is excluded from range queries it can't
        answer). Returns full Concept dicts ordered by intensity desc (NULLs
        last) then recency.
        """
        clauses, params = [], []
        if emotion is not None:
            clauses.append("a.emotion = ? COLLATE NOCASE"); params.append(emotion)
        if min_valence is not None:
            clauses.append("a.valence >= ?"); params.append(min_valence)
        if max_valence is not None:
            clauses.append("a.valence <= ?"); params.append(max_valence)
        if min_arousal is not None:
            clauses.append("a.arousal >= ?"); params.append(min_arousal)
        if max_arousal is not None:
            clauses.append("a.arousal <= ?"); params.append(max_arousal)
        if min_intensity is not None:
            clauses.append("a.intensity >= ?"); params.append(min_intensity)
        where = " AND ".join(clauses) if clauses else "1=1"
        params.append(limit)
        rows = self.con.execute(
            "SELECT c.* FROM concepts c JOIN affect a ON a.concept_id = c.id "
            f"WHERE c.deleted_at IS NULL AND ({where}) "
            "ORDER BY a.intensity DESC, c.updated_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [self._row_to_concept(r) for r in rows]

    # -- bi-temporal validity (G09 / R11) -------------------------------------

    def _normalize_validity(self, valid_from, valid_to, supersedes) -> tuple | None:
        """Coerce validity inputs to a (valid_from, valid_to, supersedes) tuple of
        trimmed strings (or None per field), or None when there is nothing to
        record. ISO strings are stored verbatim; non-strings are dropped."""
        def _s(v):
            return v.strip() if isinstance(v, str) and v.strip() else None
        vf, vt, sup = _s(valid_from), _s(valid_to), _s(supersedes)
        if vf is None and vt is None and sup is None:
            return None
        return (vf, vt, sup)

    def _sync_validity_for(self, concept_id: str, valid_from, valid_to, supersedes) -> None:
        """Upsert (or, when empty, delete) one Concept's validity row."""
        row = self._normalize_validity(valid_from, valid_to, supersedes)
        if row is None:
            self.con.execute("DELETE FROM validity WHERE concept_id=?", (concept_id,))
            return
        vf, vt, sup = row
        self.con.execute(
            "INSERT INTO validity (concept_id, valid_from, valid_to, supersedes) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(concept_id) DO UPDATE SET "
            "  valid_from=excluded.valid_from, valid_to=excluded.valid_to, "
            "  supersedes=excluded.supersedes",
            (concept_id, vf, vt, sup),
        )

    def rebuild_validity_index(self) -> int:
        """Full re-sync of the validity table from concepts.metadata. Used by
        bundle.rebuild(). Returns the validity-row count."""
        self.con.execute("DELETE FROM validity")
        n = 0
        for r in self.con.execute(
            "SELECT id, metadata, deleted_at FROM concepts"
        ).fetchall():
            if r["deleted_at"]:
                continue
            try:
                meta = json.loads(r["metadata"] or "{}")
            except (ValueError, TypeError):
                meta = {}
            vf, vt, sup = (meta.get("sb_valid_from"), meta.get("sb_valid_to"),
                          meta.get("sb_supersedes"))
            if self._normalize_validity(vf, vt, sup) is not None:
                self._sync_validity_for(r["id"], vf, vt, sup)
                n += 1
        self.con.commit()
        return n

    def validity(self, concept_id: str) -> dict | None:
        """Return {valid_from, valid_to, supersedes} for a Concept, or None if it
        carries no validity window (→ valid since created_at, still valid)."""
        r = self.con.execute(
            "SELECT valid_from, valid_to, supersedes FROM validity WHERE concept_id=?",
            (concept_id,),
        ).fetchone()
        return dict(r) if r else None

    def supersede(self, old_id, title, content, collection=None, tags=None,
                  sources=None, sb_subject=None, sb_affect=None, as_of=None) -> dict:
        """Record a contradiction bi-temporally: create a NEW Concept that
        supersedes `old_id`, set the new fact's `valid_from = as_of`, and CLOSE
        the old fact's window at `valid_to = as_of`. The old Concept is PRESERVED
        (its history stays queryable) — this is the core bi-temporal invariant.
        `as_of` defaults to today (ISO date). Returns the new Concept.
        """
        if as_of is None:
            as_of = _date.today().isoformat()
        if self.get(old_id) is None:
            raise ValueError(f"cannot supersede unknown concept: {old_id}")
        # Close the old fact's window at as_of (its valid_from, if any, is kept).
        self.update(old_id, sb_valid_to=as_of)
        # Create the new fact, linked to the old via sb_supersedes.
        return self.add(title, content, collection=collection, tags=tags,
                        sources=sources, sb_subject=sb_subject, sb_affect=sb_affect,
                        sb_valid_from=as_of, sb_supersedes=old_id)

    def get(self, concept_id):
        row = self.con.execute(
            "SELECT * FROM concepts WHERE id = ? AND deleted_at IS NULL", (concept_id,)
        ).fetchone()
        return self._row_to_concept(row) if row else None

    def get_by_title(self, needle):
        """Substring match on title, live concepts only, most recent first."""
        rows = self.con.execute(
            "SELECT * FROM concepts WHERE title LIKE ? AND deleted_at IS NULL "
            "ORDER BY updated_at DESC LIMIT 10",
            (f"%{needle}%",),
        ).fetchall()
        return [self._row_to_concept(r) for r in rows]

    def update(self, concept_id, title=None, content=None, tags=None,
               collection=None, sources=None, sb_subject=_UNSET, sb_affect=_UNSET,
               sb_valid_from=_UNSET, sb_valid_to=_UNSET, sb_supersedes=_UNSET):
        cur = self.get(concept_id)
        if not cur:
            return None
        new_title = title if title is not None else cur["title"]
        new_content = content if content is not None else cur["content"]
        new_collection = collection if collection is not None else cur["collection"]
        new_sources = sources if sources is not None else cur["sources"]
        cur_meta = json.loads(self.con.execute(
            "SELECT metadata FROM concepts WHERE id=?", (concept_id,)
        ).fetchone()["metadata"] or "{}")
        # _UNSET = preserve current; None = clear; value = set. Applies to
        # sb_subject, sb_affect, and the three temporal-validity fields.
        new_sb_subject = cur_meta.get("sb_subject") if sb_subject is _UNSET else sb_subject
        new_sb_affect = cur_meta.get("sb_affect") if sb_affect is _UNSET else sb_affect
        new_vf = cur_meta.get("sb_valid_from") if sb_valid_from is _UNSET else sb_valid_from
        new_vt = cur_meta.get("sb_valid_to") if sb_valid_to is _UNSET else sb_valid_to
        new_sup = cur_meta.get("sb_supersedes") if sb_supersedes is _UNSET else sb_supersedes
        new_meta = dict(cur_meta)
        if new_sb_subject:
            new_meta["sb_subject"] = new_sb_subject
        else:
            new_meta.pop("sb_subject", None)
        if new_sb_affect:
            new_meta["sb_affect"] = new_sb_affect
        else:
            new_meta.pop("sb_affect", None)
        for _k, _v in (("sb_valid_from", new_vf), ("sb_valid_to", new_vt),
                       ("sb_supersedes", new_sup)):
            if _v:
                new_meta[_k] = _v
            else:
                new_meta.pop(_k, None)
        self.con.execute(
            "UPDATE concepts SET title=?, content=?, collection=?, sources=?, "
            "metadata=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_title, new_content, new_collection, json.dumps(new_sources),
             json.dumps(new_meta), concept_id),
        )
        if tags is not None:
            self._set_tags(concept_id, tags)
        if content is not None:
            self._sync_wikilinks(concept_id, new_content)
        if title is not None and title != cur["title"]:
            self._resolve_pending_to(concept_id, new_title)
        # Re-sync subject index if sb_subject changed (or was explicitly passed)
        if sb_subject is not _UNSET or (cur_meta.get("sb_subject") != new_sb_subject):
            # Remove old link (if any) and re-link to new subject
            self.con.execute("DELETE FROM concept_subject WHERE concept_id=?", (concept_id,))
            self._sync_subject_index_for(concept_id, new_sb_subject)
        # Re-sync affect row if sb_affect was explicitly set or cleared
        if sb_affect is not _UNSET:
            self._sync_affect_for(concept_id, new_sb_affect)
        # Re-sync validity row if any temporal field was explicitly set or cleared
        if sb_valid_from is not _UNSET or sb_valid_to is not _UNSET or sb_supersedes is not _UNSET:
            self._sync_validity_for(concept_id, new_vf, new_vt, new_sup)
        self.con.commit()
        return self.get(concept_id)

    def delete(self, concept_id, hard=False):
        if hard:
            # FK ON DELETE CASCADE cleans relations/tags/pending; AD trigger fixes FTS.
            n = self.con.execute("DELETE FROM concepts WHERE id=?", (concept_id,)).rowcount
        else:
            n = self.con.execute(
                "UPDATE concepts SET deleted_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND deleted_at IS NULL",
                (concept_id,),
            ).rowcount
        self.con.commit()
        return n > 0

    def restore(self, concept_id):
        n = self.con.execute(
            "UPDATE concepts SET deleted_at=NULL WHERE id=? AND deleted_at IS NOT NULL",
            (concept_id,),
        ).rowcount
        if n:
            d = self.con.execute(
                "SELECT title, content FROM concepts WHERE id=?", (concept_id,)
            ).fetchone()
            self._sync_wikilinks(concept_id, d["content"])
            self._resolve_pending_to(concept_id, d["title"])
            self.con.commit()
        return n > 0

    # -- search & list -------------------------------------------------------

    def search(self, query, collection=None, tag=None, limit=10):
        # Join FTS rowid back to concepts.rowid, then filter soft-deleted.
        sql = [
            "SELECT d.* FROM concepts_fts f",
            "JOIN concepts d ON d.rowid = f.rowid",
            "WHERE concepts_fts MATCH ? AND d.deleted_at IS NULL",
        ]
        params = [query]
        if collection is not None:
            sql.append("AND d.collection = ?")
            params.append(collection)
        if tag is not None:
            sql.append(
                "AND d.id IN (SELECT dt.concept_id FROM concept_tags dt "
                "JOIN tags t ON t.id = dt.tag_id WHERE t.name = ?)"
            )
            params.append(tag)
        sql.append("ORDER BY rank LIMIT ?")
        params.append(limit)
        rows = self.con.execute(" ".join(sql), params).fetchall()
        return [self._row_to_concept(r) for r in rows]

    def list(self, collection=None, tag=None, limit=20, offset=0, sort="updated"):
        order = {"updated": "updated_at DESC", "created": "created_at DESC",
                 "title": "title COLLATE NOCASE ASC"}.get(sort, "updated_at DESC")
        sql = ["SELECT d.* FROM concepts d WHERE d.deleted_at IS NULL"]
        params = []
        if collection is not None:
            sql.append("AND d.collection = ?")
            params.append(collection)
        if tag is not None:
            sql.append(
                "AND d.id IN (SELECT dt.concept_id FROM concept_tags dt "
                "JOIN tags t ON t.id = dt.tag_id WHERE t.name = ?)"
            )
            params.append(tag)
        sql.append(f"ORDER BY {order} LIMIT ? OFFSET ?")
        params += [limit, offset]
        rows = self.con.execute(" ".join(sql), params).fetchall()
        return [self._row_to_concept(r) for r in rows]

    def collections(self):
        rows = self.con.execute(
            "SELECT COALESCE(collection, '(none)') AS name, COUNT(*) AS n "
            "FROM concepts WHERE deleted_at IS NULL GROUP BY collection "
            "ORDER BY (collection IS NULL), n DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def tags(self, sort="usage", limit=None):
        order = "n DESC, t.name" if sort == "usage" else "t.name COLLATE NOCASE"
        sql = (
            "SELECT t.name, t.color, COUNT(dt.concept_id) AS n FROM tags t "
            "LEFT JOIN concept_tags dt ON dt.tag_id = t.id "
            "LEFT JOIN concepts d ON d.id = dt.concept_id AND d.deleted_at IS NULL "
            f"GROUP BY t.id ORDER BY {order}"
        )
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [dict(r) for r in self.con.execute(sql).fetchall()]

    # -- graph ---------------------------------------------------------------

    def relate(self, from_id, to_id, relation_type="related", strength=0.5):
        if relation_type not in VALID_REL_TYPES:
            raise ValueError(f"relation_type must be one of {sorted(VALID_REL_TYPES)}")
        if not self.get(from_id) or not self.get(to_id):
            raise ValueError("both concepts must exist and be live")
        rid = _uuid()
        self.con.execute(
            "INSERT OR IGNORE INTO relations "
            "(id, from_id, to_id, relation_type, strength, source) "
            "VALUES (?, ?, ?, ?, ?, 'manual')",
            (rid, from_id, to_id, relation_type, strength),
        )
        self.con.commit()
        return rid

    def related(self, concept_id, limit=20, source="all"):
        src_filter = "" if source == "all" else "AND r.source = :src"
        # Both directions; exclude edges touching soft-deleted concepts.
        rows = self.con.execute(
            f"""
            SELECT r.relation_type, r.strength, r.source, d.id, d.title, d.collection,
                   CASE WHEN r.from_id = :id THEN 'out' ELSE 'in' END AS dir
            FROM relations r
            JOIN concepts d ON d.id = CASE WHEN r.from_id = :id THEN r.to_id ELSE r.from_id END
            WHERE (r.from_id = :id OR r.to_id = :id)
              AND d.deleted_at IS NULL {src_filter}
            ORDER BY r.strength DESC LIMIT :lim
            """,
            {"id": concept_id, "src": source, "lim": limit},
        ).fetchall()
        return [dict(r) for r in rows]

    def traverse(self, concept_id, depth=2, limit=20):
        rows = self.con.execute(
            """
            WITH RECURSIVE walk(id, hop) AS (
                SELECT :id, 0
                UNION
                SELECT CASE WHEN r.from_id = w.id THEN r.to_id ELSE r.from_id END, w.hop + 1
                FROM relations r JOIN walk w
                  ON (r.from_id = w.id OR r.to_id = w.id)
                WHERE w.hop < :depth
            )
            SELECT DISTINCT d.id, d.title, d.collection, MIN(w.hop) AS hop
            FROM walk w JOIN concepts d ON d.id = w.id
            WHERE d.deleted_at IS NULL AND w.id != :id
            GROUP BY d.id ORDER BY hop, d.title LIMIT :lim
            """,
            {"id": concept_id, "depth": depth, "lim": limit},
        ).fetchall()
        return [dict(r) for r in rows]

    # -- data ----------------------------------------------------------------

    def stats(self, collection=None):
        where = "WHERE deleted_at IS NULL"
        params = []
        if collection is not None:
            where += " AND collection = ?"
            params.append(collection)
        total = self.con.execute(
            f"SELECT COUNT(*) c FROM concepts {where}", params
        ).fetchone()["c"]
        uncolld = self.con.execute(
            "SELECT COUNT(*) c FROM concepts WHERE deleted_at IS NULL AND collection IS NULL"
        ).fetchone()["c"]
        softdel = self.con.execute(
            "SELECT COUNT(*) c FROM concepts WHERE deleted_at IS NOT NULL"
        ).fetchone()["c"]
        rels = self.con.execute(
            "SELECT source, COUNT(*) c FROM relations GROUP BY source"
        ).fetchall()
        pending = self.con.execute("SELECT COUNT(*) c FROM pending_links").fetchone()["c"]
        return {
            "concepts": total,
            "uncollected": uncolld,
            "soft_deleted": softdel,
            "relations": {r["source"]: r["c"] for r in rels},
            "pending_links": pending,
            "tags": self.tags(sort="usage", limit=5),
            "collections": self.collections(),
        }

    # -- markdown helpers ----------------------------------------------------

    @staticmethod
    def _yaml_scalar(v: str) -> str:
        """Serialize a scalar to YAML; JSON-quotes strings with special chars."""
        if not v:
            return '""'
        if re.match(r'^[A-Za-z0-9 _\-\.]+$', v) and not v[0].isspace() and not v[-1].isspace():
            return v
        return json.dumps(v, ensure_ascii=False)

    @staticmethod
    def _yaml_frontmatter(fields: dict) -> str:
        """Render a dict as a YAML frontmatter block (--- ... ---)."""
        lines = ["---"]
        for k, v in fields.items():
            if v is None:
                continue
            if isinstance(v, list):
                if v:
                    lines.append(f"{k}:")
                    for item in v:
                        lines.append(f"  - {SecondBrain._yaml_scalar(str(item))}")
                else:
                    lines.append(f"{k}: []")
            else:
                lines.append(f"{k}: {SecondBrain._yaml_scalar(str(v))}")
        lines.append("---")
        return "\n".join(lines)

    @staticmethod
    def _safe_filename(title: str) -> str:
        """Convert a note title to a filesystem-safe filename stem (no extension)."""
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title)
        safe = safe.strip('. ')
        return safe[:200] or "untitled"

    def _concept_to_md(self, d: dict) -> str:
        """Render one concept as a Markdown document with YAML frontmatter."""
        fm = self._yaml_frontmatter({
            "id": d["id"],
            "title": d["title"],
            "collection": d.get("collection"),
            "tags": d.get("tags", []),
            "sources": d.get("sources", []),
            "created_at": d.get("created_at", ""),
            "updated_at": d.get("updated_at", ""),
        })
        return f"{fm}\n\n# {d['title']}\n\n{d['content']}\n"

    # -- export / import -----------------------------------------------------

    def export(self, collection=None, fmt="json"):
        concepts = self.list(collection=collection, limit=10**9)
        if fmt == "json":
            return json.dumps(concepts, indent=2, ensure_ascii=False)
        if fmt == "markdown":
            return "\n".join(self._concept_to_md(d) for d in concepts)
        if fmt == "csv":
            import csv, io
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "title", "collection", "tags", "content"])
            for d in concepts:
                w.writerow([d["id"], d["title"], d["collection"] or "",
                            ";".join(d["tags"]), d["content"]])
            return buf.getvalue()
        raise ValueError("format must be json|markdown|csv")

    def export_vault(self, output_dir, collection=None) -> dict:
        """Write one Markdown file per concept into output_dir (Obsidian-compatible vault).
        Filenames are derived from titles; duplicates get a short-id suffix.
        Returns {"concepts": N, "path": str(output_dir)}."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        concepts = self.list(collection=collection, limit=10**9)
        seen: dict = {}
        written = 0
        for d in concepts:
            stem = self._safe_filename(d["title"])
            if stem in seen:
                stem = f"{stem}_{d['id'][:8]}"
            seen[stem] = True
            (output_dir / f"{stem}.md").write_text(
                self._concept_to_md(d), encoding="utf-8"
            )
            written += 1
        return {"concepts": written, "path": str(output_dir)}

    @staticmethod
    def _parse_md_note(text: str) -> "dict | None":
        """Parse a single Markdown note (YAML frontmatter + # heading + body).
        Returns a raw concept dict or None if the text is not a valid note."""
        text = text.strip()
        if not text or not text.startswith("---"):
            return None
        lines = text.split("\n")
        fm_lines, i = [], 1
        while i < len(lines) and lines[i].rstrip() != "---":
            fm_lines.append(lines[i])
            i += 1
        if i >= len(lines):
            return None  # no closing ---
        rest_lines = lines[i + 1:]

        # Minimal YAML parser for the known frontmatter format.
        fm: dict = {}
        cur_list: "str | None" = None
        for line in fm_lines:
            if not line.strip():
                continue
            if line.startswith("  - ") and cur_list is not None:
                raw = line[4:].strip()
                val = json.loads(raw) if raw.startswith('"') else raw
                fm[cur_list].append(val)
            elif ": " in line or line.rstrip().endswith(":"):
                cur_list = None
                stripped = line.rstrip()
                if stripped.endswith(": []"):
                    key = stripped[:-4].strip()
                    fm[key] = []
                elif stripped.endswith(":"):
                    key = stripped[:-1].strip()
                    fm[key] = []
                    cur_list = key
                else:
                    key, _, raw_val = line.partition(": ")
                    key = key.strip()
                    raw_val = raw_val.strip()
                    val = json.loads(raw_val) if raw_val.startswith('"') else raw_val
                    fm[key] = val

        # Extract title from # heading; body is everything after it.
        title = fm.get("title") or ""
        body_start = 0
        for j, bl in enumerate(rest_lines):
            if not bl.strip():
                continue
            if bl.startswith("# "):
                if not title:
                    title = bl[2:].strip()
                body_start = j + 1
            break

        content = "\n".join(rest_lines[body_start:]).strip()
        if not title:
            return None

        return {
            "id": fm.get("id") or _uuid(),
            "title": title,
            "content": content,
            "collection": fm.get("collection") or None,
            "tags": fm.get("tags", []) if isinstance(fm.get("tags"), list) else [],
            "sources": fm.get("sources", []) if isinstance(fm.get("sources"), list) else [],
            "metadata": {},
        }

    def _import_concepts(self, data: list, mode: str) -> dict:
        """Core import loop: insert a list of raw concept dicts."""
        added = skipped = 0
        for d in data:
            exists = self.con.execute(
                "SELECT 1 FROM concepts WHERE id=?", (d["id"],)
            ).fetchone()
            if exists and mode == "merge":
                skipped += 1
                continue
            if exists and mode == "replace":
                self.con.execute("DELETE FROM concepts WHERE id=?", (d["id"],))
            self.con.execute(
                "INSERT INTO concepts (id, title, content, collection, sources, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (d["id"], d["title"], d["content"], d.get("collection"),
                 json.dumps(d.get("sources", [])), json.dumps(d.get("metadata", {}))),
            )
            self._set_tags(d["id"], d.get("tags", []))
            added += 1
        # Re-derive all wikilinks after the full set exists (resolves cross-refs).
        for d in self.list(limit=10**9):
            self._sync_wikilinks(d["id"], d["content"])
            self._resolve_pending_to(d["id"], d["title"])
        self.con.commit()
        return {"added": added, "skipped": skipped}

    def _import_vault(self, vault_dir: Path, mode: str) -> dict:
        """Import all .md files from a vault directory."""
        concepts = []
        for f in sorted(vault_dir.glob("*.md")):
            d = self._parse_md_note(f.read_text(encoding="utf-8"))
            if d:
                concepts.append(d)
        return self._import_concepts(concepts, mode)

    def import_(self, path, mode="merge"):
        path = Path(path)
        if path.is_dir():
            return self._import_vault(path, mode)
        if path.suffix.lower() in (".md", ".markdown"):
            d = self._parse_md_note(path.read_text(encoding="utf-8"))
            return self._import_concepts([d] if d else [], mode)
        data = json.loads(path.read_text())
        return self._import_concepts(data, mode)

    def close(self):
        if getattr(self, "_closed", False):
            return
        self.con.close()
        self._closed = True

    # -- lifecycle / size ---------------------------------------------------

    def checkpoint(self):
        """Flush the WAL to the main DB file. Idempotent. Safe to call repeatedly.
        Use this before renaming the db file on disk so the WAL/SHM don't follow."""
        try:
            self.con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.DatabaseError:
            pass

    def checkpoint_and_close(self):
        self.checkpoint()
        self.close()

    # -- summary / distill / archive ----------------------------------------

    def _humanize_bytes(self, n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
            n /= 1024
        return f"{n:.1f} PB"

    def _count_alive(self) -> int:
        return self.con.execute(
            "SELECT COUNT(*) c FROM concepts WHERE deleted_at IS NULL"
        ).fetchone()["c"]

    def _build_filter(self, tags=None, collection=None, query=None,
                      since=None, until=None, alias="d"):
        """Build a WHERE clause + params that selects concepts matching all
        the given filters. Within a category (multiple tags) it's IN/OR.
        Across categories it's AND."""
        a = alias
        clauses = [f"{a}.deleted_at IS NULL"]
        params = []
        if tags:
            placeholders = ",".join("?" * len(tags))
            clauses.append(
                f"{a}.id IN (SELECT dt.concept_id FROM concept_tags dt "
                f"JOIN tags t ON t.id = dt.tag_id WHERE t.name IN ({placeholders}))"
            )
            params.extend(tags)
        if collection:
            clauses.append(f"{a}.collection = ?")
            params.append(collection)
        if query:
            clauses.append(
                f"{a}.rowid IN (SELECT rowid FROM concepts_fts WHERE concepts_fts MATCH ?)"
            )
            params.append(query)
        if since:
            clauses.append(f"{a}.updated_at >= ?")
            params.append(since)
        if until:
            clauses.append(f"{a}.updated_at <= ?")
            params.append(until)
        return " AND ".join(clauses), params

    def _copy_subset_to(self, output_path, concept_ids) -> dict:
        """Copy a set of concept_ids (and their tags/relations/pending_links)
        into a fresh brain.db at output_path. Returns counts."""
        output_path = Path(output_path)
        if output_path.exists():
            raise FileExistsError(
                f"{output_path} already exists; remove it or pick another path"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Open fresh brain — _ensure_schema creates all tables.
        out = SecondBrain(output_path)

        if not concept_ids:
            out.close()
            return {"concepts": 0, "tags": 0, "relations": 0, "pending_links": 0,
                    "path": str(output_path)}

        placeholders = ",".join("?" * len(concept_ids))
        ids = list(concept_ids)

        # Concepts (preserve original ids, timestamps, metadata)
        concept_rows = self.con.execute(
            f"SELECT * FROM concepts WHERE id IN ({placeholders})", ids
        ).fetchall()
        for d in concept_rows:
            out.con.execute(
                "INSERT INTO concepts (id, title, content, collection, sources, "
                "created_at, updated_at, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (d["id"], d["title"], d["content"], d["collection"], d["sources"],
                 d["created_at"], d["updated_at"], d["metadata"]),
            )

        # Tags: only those actually used by the subset; mint new tag ids.
        tag_rows = self.con.execute(
            f"SELECT dt.concept_id, t.name FROM concept_tags dt "
            f"JOIN tags t ON t.id = dt.tag_id "
            f"WHERE dt.concept_id IN ({placeholders})", ids
        ).fetchall()
        tag_name_to_id = {}
        for tn in sorted({r["name"] for r in tag_rows}):
            tid = _uuid()
            out.con.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (tid, tn))
            tag_name_to_id[tn] = tid
        for r in tag_rows:
            out.con.execute(
                "INSERT INTO concept_tags (concept_id, tag_id) VALUES (?, ?)",
                (r["concept_id"], tag_name_to_id[r["name"]]),
            )

        # Relations: edges where BOTH endpoints are in the subset.
        rel_rows = self.con.execute(
            f"SELECT * FROM relations WHERE from_id IN ({placeholders}) "
            f"AND to_id IN ({placeholders})", ids + ids
        ).fetchall()
        for r in rel_rows:
            out.con.execute(
                "INSERT INTO relations (id, from_id, to_id, relation_type, "
                "strength, source) VALUES (?, ?, ?, ?, ?, ?)",
                (r["id"], r["from_id"], r["to_id"], r["relation_type"],
                 r["strength"], r["source"]),
            )

        # Pending links: from a concept in the subset (target may or may not be).
        pend_rows = self.con.execute(
            f"SELECT * FROM pending_links WHERE from_id IN ({placeholders})", ids
        ).fetchall()
        for r in pend_rows:
            out.con.execute(
                "INSERT INTO pending_links (id, from_id, target_title) "
                "VALUES (?, ?, ?)",
                (r["id"], r["from_id"], r["target_title"]),
            )

        out.con.commit()
        out.close()
        return {
            "concepts": len(concept_rows),
            "tags": len(tag_name_to_id),
            "relations": len(rel_rows),
            "pending_links": len(pend_rows),
            "path": str(output_path),
        }

    def summary(self, cold_threshold_days: int = 180) -> dict:
        """Brain health snapshot: size, concept counts (alive / cold / soft-del),
        relation counts, pending links, and a one-line recommendation.

        Cold = alive concepts whose updated_at is older than cold_threshold_days."""
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        alive = self._count_alive()
        cold = self.con.execute(
            "SELECT COUNT(*) c FROM concepts WHERE deleted_at IS NULL "
            "AND updated_at < datetime('now', ?)",
            (f"-{int(cold_threshold_days)} days",),
        ).fetchone()["c"]
        soft = self.con.execute(
            "SELECT COUNT(*) c FROM concepts WHERE deleted_at IS NOT NULL"
        ).fetchone()["c"]
        rels = {r["source"]: r["c"] for r in self.con.execute(
            "SELECT source, COUNT(*) c FROM relations GROUP BY source"
        ).fetchall()}
        pending = self.con.execute(
            "SELECT COUNT(*) c FROM pending_links"
        ).fetchone()["c"]

        size_mb = size_bytes / 1024 / 1024
        rec = None
        if alive and (cold / alive) > 0.5:
            rec = "archive"
        if size_mb > 100:
            rec = rec or "archive"
        if alive and (cold / alive) > 0.7 and alive > 5000:
            rec = "archive-then-distill"

        return {
            "db_path": str(self.db_path),
            "size_bytes": size_bytes,
            "size_human": self._humanize_bytes(size_bytes),
            "concepts": {
                "alive": alive,
                "cold": cold,
                "soft_deleted": soft,
                "cold_threshold_days": cold_threshold_days,
            },
            "relations": rels,
            "pending_links": pending,
            "recommendation": rec,
        }

    def distill(self, output_path, tags=None, collection=None, query=None,
                since=None, until=None, include_related_depth: int = 0,
                min_strength: float = 0.0) -> dict:
        """Create a new brain.db at output_path containing only the concepts
        that match the given filters. NON-DESTRUCTIVE: the working brain is
        not modified. The CLI's --activate flag handles swapping.

        Filters AND across categories (a concept must satisfy all given filters)
        and OR within a category (any tag, any collection). Returns counts.
        """
        if not any([tags, collection, query, since, until]):
            raise ValueError(
                "distill needs at least one filter: --tag / --collection / "
                "--query / --since / --until"
            )
        where, params = self._build_filter(tags, collection, query, since, until)
        seed_ids = {r["id"] for r in self.con.execute(
            f"SELECT id FROM concepts d WHERE {where}", params
        ).fetchall()}

        # Optional N-hop expansion around the seeds.
        if include_related_depth > 0 and seed_ids:
            for sid in list(seed_ids):
                for row in self.traverse(sid, depth=include_related_depth,
                                         limit=10**6):
                    seed_ids.add(row["id"])

        if not seed_ids:
            return {"concepts": 0, "tags": 0, "relations": 0,
                    "pending_links": 0, "path": str(Path(output_path)),
                    "note": "no concepts matched the filter"}

        return self._copy_subset_to(output_path, seed_ids)

    def archive(self, output_path, older_than_days: int = 180,
                before_date: str = None, tags=None, collection=None,
                dry_run: bool = False) -> dict:
        """Move cold concepts to output_path (a new brain.db) and hard-delete
        them from the working brain. The whole operation is atomic — if the
        copy fails, nothing is deleted.

        Default criterion: updated_at < (now - older_than_days).
        If before_date is given, use that instead.
        If tags/collection are given, archive matching concepts regardless of age.
        """
        if tags or collection or before_date is not None:
            where, params = self._build_filter(tags, collection,
                                               since=None, until=before_date)
            target_ids = {r["id"] for r in self.con.execute(
                f"SELECT id FROM concepts d WHERE {where}", params
            ).fetchall()}
            criterion = "explicit filter"
        else:
            target_ids = {r["id"] for r in self.con.execute(
                "SELECT id FROM concepts WHERE deleted_at IS NULL "
                "AND updated_at < datetime('now', ?)",
                (f"-{int(older_than_days)} days",),
            ).fetchall()}
            criterion = f"untouched {older_than_days}+ days"

        alive_before = self._count_alive()
        if not target_ids:
            return {
                "archived": 0,
                "would_archive": 0,
                "remaining": alive_before,
                "would_remain": alive_before,
                "criterion": criterion,
                "path": str(Path(output_path)),
                "dry_run": dry_run,
            }
        if target_ids == {r["id"] for r in self.con.execute(
                "SELECT id FROM concepts WHERE deleted_at IS NULL").fetchall()}:
            raise ValueError(
                "archive would remove every alive concept — refusing. "
                "Pass a narrower filter or check your --older-than-days."
            )

        if dry_run:
            return {
                "would_archive": len(target_ids),
                "would_remain": alive_before - len(target_ids),
                "criterion": criterion,
                "path": str(Path(output_path)),
                "dry_run": True,
            }

        # Atomic: copy first, then delete. If the copy fails the working
        # brain is untouched.
        copy_stats = self._copy_subset_to(output_path, target_ids)

        placeholders = ",".join("?" * len(target_ids))
        self.con.execute(
            f"DELETE FROM concepts WHERE id IN ({placeholders})", list(target_ids)
        )
        self.con.commit()
        self.checkpoint()  # flush WAL so renames are clean
        self.con.execute("VACUUM")  # reclaim space

        size_after = self.db_path.stat().st_size
        return {
            "archived": copy_stats["concepts"],
            "archived_relations": copy_stats["relations"],
            "remaining": self._count_alive(),
            "criterion": criterion,
            "path": str(Path(output_path)),
            "size_remaining_bytes": size_after,
            "size_remaining_human": self._humanize_bytes(size_after),
        }

    def merge_brain(self, source_path) -> dict:
        """Bring concepts from another brain.db into this one. Idempotent:
        concepts whose id already exists are skipped (relations, tags and
        pending_links are likewise skipped via UNIQUE constraints)."""
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        # Source is read-only; never use the same DB_PATH global.
        src = SecondBrain(source_path)

        # Build id-set of already-present concepts for fast skip.
        existing = {r["id"] for r in self.con.execute("SELECT id FROM concepts").fetchall()}
        existing_tag_names = {r["name"] for r in self.con.execute("SELECT name FROM tags").fetchall()}

        # Tags: copy any missing tag names (mint new ids).
        src_tag_rows = src.con.execute("SELECT id, name FROM tags").fetchall()
        src_tag_id_to_name = {r["id"]: r["name"] for r in src_tag_rows}
        name_to_new_id = {}
        for name in {r["name"] for r in src_tag_rows}:
            if name not in existing_tag_names:
                tid = _uuid()
                self.con.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (tid, name))
                name_to_new_id[name] = tid
                existing_tag_names.add(name)
        # Map source tag id -> our tag id (either pre-existing or newly minted).
        # For tags that already existed by name, find our id.
        src_tag_id_to_our_id = {}
        for src_tid, name in src_tag_id_to_name.items():
            if name in name_to_new_id:
                src_tag_id_to_our_id[src_tid] = name_to_new_id[name]
            else:
                src_tag_id_to_our_id[src_tid] = self.con.execute(
                    "SELECT id FROM tags WHERE name = ?", (name,)
                ).fetchone()["id"]

        # Concepts: skip those we already have.
        src_concept_rows = src.con.execute("SELECT * FROM concepts").fetchall()
        added_concepts = 0
        skipped_concepts = 0
        newly_added_ids = []
        for d in src_concept_rows:
            if d["id"] in existing:
                skipped_concepts += 1
                continue
            self.con.execute(
                "INSERT INTO concepts (id, title, content, collection, sources, "
                "created_at, updated_at, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (d["id"], d["title"], d["content"], d["collection"], d["sources"],
                 d["created_at"], d["updated_at"], d["metadata"]),
            )
            existing.add(d["id"])
            added_concepts += 1
            newly_added_ids.append(d["id"])

        # Concept_tags: re-bind source tag ids to our tag ids.
        src_dt_rows = src.con.execute("SELECT concept_id, tag_id FROM concept_tags").fetchall()
        added_tags_links = 0
        for r in src_dt_rows:
            if r["concept_id"] not in existing:
                continue
            our_tag_id = src_tag_id_to_our_id.get(r["tag_id"])
            if our_tag_id is None:
                continue
            self.con.execute(
                "INSERT OR IGNORE INTO concept_tags (concept_id, tag_id) "
                "VALUES (?, ?)",
                (r["concept_id"], our_tag_id),
            )
            added_tags_links += 1

        # Relations: only those touching concepts we now have.
        src_rel_rows = src.con.execute(
            "SELECT * FROM relations"
        ).fetchall()
        added_rels = 0
        for r in src_rel_rows:
            if r["from_id"] not in existing or r["to_id"] not in existing:
                continue
            self.con.execute(
                "INSERT OR IGNORE INTO relations "
                "(id, from_id, to_id, relation_type, strength, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (r["id"], r["from_id"], r["to_id"], r["relation_type"],
                 r["strength"], r["source"]),
            )
            added_rels += 1

        # Pending links: only from concepts we now have.
        src_pend_rows = src.con.execute(
            "SELECT * FROM pending_links"
        ).fetchall()
        added_pend = 0
        for r in src_pend_rows:
            if r["from_id"] not in existing:
                continue
            self.con.execute(
                "INSERT OR IGNORE INTO pending_links "
                "(id, from_id, target_title) VALUES (?, ?, ?)",
                (r["id"], r["from_id"], r["target_title"]),
            )
            added_pend += 1

        # Re-derive wikilinks for newly added concepts so cross-refs into
        # the existing brain resolve correctly.
        for did in newly_added_ids:
            d = self.con.execute(
                "SELECT content FROM concepts WHERE id=?", (did,)
            ).fetchone()
            if d:
                self._sync_wikilinks(did, d["content"])
        # And resolve any pending links pointing at the new titles.
        for did in newly_added_ids:
            d = self.con.execute(
                "SELECT title FROM concepts WHERE id=?", (did,)
            ).fetchone()
            if d:
                self._resolve_pending_to(did, d["title"])

        self.con.commit()
        src.close()
        return {
            "concepts_added": added_concepts,
            "concepts_skipped": skipped_concepts,
            "tag_links_added": added_tags_links,
            "relations_added": added_rels,
            "pending_links_added": added_pend,
            "source_path": str(source_path),
        }
