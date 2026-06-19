#!/usr/bin/env python3
"""G04 M1 verifier — SQLite schema rename `drawers` → `concepts`.

R4 / G04 M1: the code uses `Concept` as the canonical model name (per
OKF v0.1). For a fresh brain.db, the SQLite table must be called
`concepts`, not `drawers`. For a v2.1 brain.db (legacy `drawers` table),
opening it via `SecondBrain(db_path)` must auto-migrate: rename the
table, rebuild the FTS5 index, replace triggers, preserve all rows.

What this verifier checks (drives `SecondBrain` end-to-end, not raw
SQLite — the public API is the contract):

  (a) FRESH DB: a brand-new brain.db has `concepts` in `sqlite_master`
      and does NOT have `drawers`.
  (b) FRESH DB + FTS5: a concept inserted via `SecondBrain.add()` is
      findable via FTS5 search (the index is wired correctly).
  (c) FRESH DB + PERSISTENCE: closing the DB and reopening via
      `SecondBrain` preserves all concepts (FTS5 still finds them).
  (d) MIGRATION + ROWS: opening a v2.1 DB (with `drawers` table) via
      `SecondBrain` preserves the row count; `concepts` now exists;
      `drawers` does not.
  (e) MIGRATION + FTS5: after migration, a concept inserted into the
      v2.1 DB before migration is findable via FTS5 search.
  (f) MIGRATION + NEW WRITES: after migration, a NEW concept inserted
      via `SecondBrain.add()` is also findable (triggers were rebuilt
      with the new table name).
  (g) FK: the renamed `concept_tags` table's FK to `concepts` is still
      valid; cascading delete works.

Exits nonzero with a per-check diagnostic on any failure.
"""
import os
import shutil
import sqlite3 as sql
import subprocess
import sys
import tempfile
import textwrap
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
from brain import SecondBrain  # noqa: E402

V21_SCHEMA = textwrap.dedent("""\
    CREATE TABLE drawers (
        id          TEXT      PRIMARY KEY,
        title       TEXT      NOT NULL,
        content     TEXT      NOT NULL,
        collection  TEXT      DEFAULT NULL,
        sources     TEXT      DEFAULT '[]',
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_at  TIMESTAMP DEFAULT NULL,
        metadata    TEXT      DEFAULT '{}'
    );
    CREATE TABLE tags (
        id         TEXT      PRIMARY KEY,
        name       TEXT      NOT NULL UNIQUE,
        color      TEXT      DEFAULT '#3b82f6',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE drawer_tags (
        drawer_id TEXT NOT NULL,
        tag_id    TEXT NOT NULL,
        PRIMARY KEY (drawer_id, tag_id),
        FOREIGN KEY (drawer_id) REFERENCES drawers(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id)    REFERENCES tags(id)    ON DELETE CASCADE
    );
    CREATE VIRTUAL TABLE drawers_fts USING fts5(
        title, content, content=drawers, content_rowid=rowid
    );
    CREATE TRIGGER drawers_ai AFTER INSERT ON drawers BEGIN
      INSERT INTO drawers_fts(rowid, title, content)
      VALUES (new.rowid, new.title, new.content);
    END;
    CREATE TRIGGER drawers_ad AFTER DELETE ON drawers BEGIN
      INSERT INTO drawers_fts(drawers_fts, rowid, title, content)
      VALUES ('delete', old.rowid, old.title, old.content);
    END;
    CREATE TRIGGER drawers_au AFTER UPDATE ON drawers BEGIN
      INSERT INTO drawers_fts(drawers_fts, rowid, title, content)
      VALUES ('delete', old.rowid, old.title, old.content);
      INSERT INTO drawers_fts(rowid, title, content)
      VALUES (new.rowid, new.title, new.content);
    END;
""")


def _has_table(con, name: str) -> bool:
    r = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return r is not None


def _has_trigger(con, name: str) -> bool:
    r = con.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name=?", (name,)
    ).fetchone()
    return r is not None


def _all_table_names(con) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]


def _all_trigger_names(con) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'"
    ).fetchall()]


def _temp_db_path() -> Path:
    """Return a path that won't fight Windows file locks. We use a
    named-tempfile path but DON'T rely on TemporaryDirectory() for
    cleanup — we delete the file (and WAL/SHM siblings) explicitly
    after closing every connection. On Windows, SQLite's WAL mode
    leaves -wal/-shm files that block rmtree, so the explicit unlink
    is required."""
    td = Path(tempfile.gettempdir()) / f"g04-m1-{uuid.uuid4().hex[:8]}"
    td.mkdir(parents=True, exist_ok=False)
    return td / "brain.db"


def _cleanup(db_path: Path) -> None:
    """Force-unlink the db + wal + shm + parent dir, swallowing errors
    (we tried, the test result is what matters)."""
    for p in [db_path, db_path.with_suffix(db_path.suffix + "-wal"),
              db_path.with_suffix(db_path.suffix + "-shm")]:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    shutil.rmtree(db_path.parent, ignore_errors=True)


def check_test_suite() -> tuple[bool, str]:
    """(h) Run the existing test_brain.py as a subprocess. After M1
    ships, the tests should be updated to use `concepts` (and the
    schema-level SQL strings to use `FROM concepts`). The tests are
    the strongest end-to-end check that the M1 rename didn't break
    the public API of SecondBrain — every method that touches the
    `concepts` table (now) is exercised."""
    r = subprocess.run(
        [sys.executable, "tests/test_brain.py"],
        cwd=str(REPO), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120,
    )
    if r.returncode != 0:
        tail = (r.stdout + r.stderr)[-1500:]
        return False, (f"(h) tests/test_brain.py FAILED (exit {r.returncode}); "
                       f"tail: {tail!r}")
    return True, "(h) tests/test_brain.py: ALL TESTS PASS"


def check_fresh_db() -> tuple[bool, str]:
    """(a)-(c): fresh DB has `concepts` table, FTS5 works, persists."""
    db = _temp_db_path()
    try:
        b = SecondBrain(db)
        # (a) tables
        con = b.con
        if not _has_table(con, "concepts"):
            return False, f"(a) FRESH DB missing 'concepts'; tables={_all_table_names(con)}"
        if _has_table(con, "drawers"):
            return False, "(a) FRESH DB has stale 'drawers' table"
        if not _has_table(con, "concepts_fts"):
            return False, f"(a) FRESH DB missing 'concepts_fts'; tables={_all_table_names(con)}"
        # (b) FTS5 round-trip
        b.add(title="TestConcept", content="canary_word_for_fts_test", tags=["t1"])
        hits = b.search("canary_word_for_fts_test")
        if not hits or hits[0]["title"] != "TestConcept":
            return False, f"(b) FTS5 search did not return TestConcept; got {hits!r}"
        # (c) persistence
        b.con.close()
        b2 = SecondBrain(db)
        hits2 = b2.search("canary_word_for_fts_test")
        if not hits2 or hits2[0]["title"] != "TestConcept":
            return False, "(c) FTS5 search after reopen did not return TestConcept"
        b2.con.close()
    finally:
        _cleanup(db)
    return True, "(a-c) fresh DB: concepts/concepts_fts exist, FTS5 works, persists"


def check_v21_migration() -> tuple[bool, str]:
    """(d)-(g): v2.1 DB with `drawers` migrates cleanly on open."""
    db = _temp_db_path()
    try:
        # Build a v2.1 schema with rows in it
        v21 = sql.connect(db)
        v21.executescript(V21_SCHEMA)
        v21.execute(
            "INSERT INTO drawers(id, title, content) VALUES (?,?,?)",
            ("legacy1", "LegacyNote", "legacy_canary_word_42"),
        )
        v21.execute(
            "INSERT INTO drawers(id, title, content) VALUES (?,?,?)",
            ("legacy2", "SecondNote", "another_canary_phrase"),
        )
        v21.commit()
        v21.close()
        # Open via SecondBrain — must trigger migration
        b = SecondBrain(db)
        con = b.con
        # (d) tables renamed, rows preserved
        if not _has_table(con, "concepts"):
            return False, f"(d) MIGRATION: 'concepts' not present; tables={_all_table_names(con)}"
        if _has_table(con, "drawers"):
            return False, "(d) MIGRATION: 'drawers' table still present"
        n_rows = con.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        if n_rows != 2:
            return False, f"(d) MIGRATION: row count lost (expected 2, got {n_rows})"
        # (e) FTS5 finds legacy data
        hits = b.search("legacy_canary_word_42")
        if not hits or hits[0]["title"] != "LegacyNote":
            return False, f"(e) MIGRATION + FTS5: legacy content not searchable; got {hits!r}"
        # (f) NEW writes post-migration wire up to FTS5
        b.add(title="PostMigNote", content="post_migration_canary_99", tags=["p1"])
        hits2 = b.search("post_migration_canary_99")
        if not hits2 or hits2[0]["title"] != "PostMigNote":
            return False, (f"(f) MIGRATION + new write: post-mig insert not "
                           f"indexed; got {hits2!r}")
        # (g) triggers renamed
        legacy_triggers = [t for t in _all_trigger_names(con) if t.startswith("drawers_")]
        if legacy_triggers:
            return False, f"(g) MIGRATION: legacy triggers not dropped: {legacy_triggers}"
        for needed in ("concepts_ai", "concepts_ad", "concepts_au"):
            if not _has_trigger(con, needed):
                return False, f"(g) MIGRATION: trigger {needed!r} missing"
        b.con.close()
    finally:
        _cleanup(db)
    return True, ("(d-g) v2.1 -> concepts: tables renamed, 2 rows preserved, "
                  "FTS5 finds legacy, new writes work, triggers renamed")


def check_fk_cascade() -> tuple[bool, str]:
    """(g extra): concept_tags FK cascade still works post-rename."""
    db = _temp_db_path()
    try:
        b = SecondBrain(db)
        b.add(title="CascadeTest", content="cascade target", tags=["alpha", "beta"])
        c = b.search("cascade target")
        if not c:
            return False, "FK: test concept not found after add"
        cid = c[0]["id"]
        n_tags = len(c[0]["tags"])
        if n_tags != 2:
            return False, f"FK: expected 2 tags, got {n_tags}"
        # Soft-delete should NOT cascade (per design — soft delete keeps tags)
        b.delete(cid)
        # Hard-delete via raw SQL: simulate archive (the cascade target)
        b.con.execute("DELETE FROM concepts WHERE id=?", (cid,))
        b.con.commit()
        n_concept_tags = b.con.execute(
            "SELECT COUNT(*) FROM concept_tags WHERE concept_id=?", (cid,)
        ).fetchone()[0]
        if n_concept_tags != 0:
            return False, f"FK cascade: concept_tags rows not deleted (got {n_concept_tags})"
        b.con.close()
    finally:
        _cleanup(db)
    return True, "(g) FK cascade: hard-delete on concepts cascades to concept_tags"


def main() -> int:
    fails = []
    for fn in (check_fresh_db, check_v21_migration, check_fk_cascade, check_test_suite):
        ok, msg = fn()
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {msg}")
        if not ok:
            fails.append(msg)
    if fails:
        return 1
    print()
    print("G04 M1: PASS — schema rename `drawers` -> `concepts` is end-to-end clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
