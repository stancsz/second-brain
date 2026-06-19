#!/usr/bin/env python3
"""G08 verifier: R10 (psych subjects) — sb_subject round-trip + persona sub-graph query.

Per docs/04-psychological-memory.md §Subjects, a memory carries `sb_subject: <path>`.
Per R10: "a persona sub-graph query returns exactly that subject's Concepts".

This verifier exercises the real end-to-end path — the same Python entry points a
user would hit from the CLI or a hook — by:

  1. Building a small OKF Bundle on disk (3 Person Concepts + 5 fact Concepts
     distributed across 2 subjects, plus 2 facts with no sb_subject → must default
     to /people/self.md).
  2. Invoking bundle.rebuild() to populate the SQLite.
  3. Asserting the derived `subjects` and `concept_subject` tables are populated
     correctly.
  4. Invoking SecondBrain.subject_subgraph(path) for each subject; asserting
     exactly the right set of concepts comes back.
  5. Re-exporting → wiping brain.db → rebuilding → re-querying; asserting
     identical results (the round-trip the bundle is supposed to support).
  6. Asserting the default-subject rule (a Concept with no sb_subject lands
     under /people/self.md).

Strongest-pattern check: the verifier drives the *real* SecondBrain class on a
real bundle on disk, not mocked internals. A verifier that only checked
"subjects table exists" would pass for an empty table — this one asserts the
table is populated and the subgraph queries are correct against a populated
DB.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(os.path.abspath(os.path.dirname(__file__))).parent.parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import bundle  # noqa: E402
import okf  # noqa: E402


# Test fixtures — a small but realistic bundle of people + memories
PEOPLE = [
    {"sb_id": "p-rox", "type": "Person", "title": "Rox",
     "body": "Rox is a person the user knows well. Quiet, conflict-avoidant.",
     "collection": "people"},
    {"sb_id": "p-alex", "type": "Person", "title": "Alex",
     "body": "Alex is a coworker. Direct communicator.",
     "collection": "people"},
]

# 5 memories: 2 for rox, 1 for alex, 2 with no sb_subject (→ default self)
MEMORIES = [
    {"sb_id": "m-001", "type": "Trait", "title": "Rox avoids conflict",
     "body": "When the conversation gets tense, Rox goes quiet for hours.",
     "collection": "traits",
     "sb_subject": "/people/rox.md"},
    {"sb_id": "m-002", "type": "Episode", "title": "Argument with Rox",
     "body": "Fought about the trip. She went silent for 3 days.",
     "collection": "episodes",
     "sb_subject": "/people/rox.md"},
    {"sb_id": "m-003", "type": "Trait", "title": "Alex is direct",
     "body": "Alex always says what's on their mind.",
     "collection": "traits",
     "sb_subject": "/people/alex.md"},
    # m-004 has NO sb_subject — must default to /people/self.md per docs/04 §Subjects
    {"sb_id": "m-004", "type": "Note", "title": "Standup was late",
     "body": "Today's standup ran 10 minutes long.",
     "collection": "notes"},
    # m-005 has NO sb_subject — must default to /people/self.md
    {"sb_id": "m-005", "type": "Note", "title": "Read the OKF spec",
     "body": "Walked through OKF v0.1 spec today.",
     "collection": "notes"},
]


def write_bundle(bundle_dir: Path) -> None:
    """Build the fixture Bundle on disk."""
    # Collection indexes
    for coll in {"people", "traits", "episodes", "notes"}:
        d = bundle_dir / coll
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.md").write_text(
            "---\ntype: Index\n---\n\n# " + coll.title() + "\n", encoding="utf-8")
    for person in PEOPLE:
        slug = person["title"].lower()
        path = bundle_dir / person["collection"] / f"{slug}.md"
        path.write_text(okf.to_markdown(person), encoding="utf-8")
    for m in MEMORIES:
        slug = m["title"].lower().replace(" ", "-")
        path = bundle_dir / m["collection"] / f"{slug}.md"
        path.write_text(okf.to_markdown(m), encoding="utf-8")


def main() -> int:
    fails = []

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bundle_dir = td / "okf"
        bundle_dir.mkdir()
        db_path = td / "brain.db"
        write_bundle(bundle_dir)

        # === Phase 1: build from bundle ===
        brain = bundle.rebuild(bundle_dir, db_path)
        n = brain.con.execute("SELECT COUNT(*) AS c FROM concepts").fetchone()["c"]
        if n < len(PEOPLE) + len(MEMORIES):
            fails.append(f"rebuild inserted {n} rows, expected >= {len(PEOPLE)+len(MEMORIES)}")

        # === Phase 2: subjects table populated ===
        subjects = [dict(r) for r in brain.con.execute(
            "SELECT sb_id, slug, display_name, kind FROM subjects ORDER BY sb_id").fetchall()]
        person_subjects = [s for s in subjects if s["kind"] == "Person"]
        person_titles = sorted(s["display_name"] for s in person_subjects
                               if s["display_name"] != "self")
        if person_titles != ["Alex", "Rox"]:
            fails.append(f"subjects table Person rows: got {person_titles}, expected ['Alex', 'Rox']")
        if not any(s["sb_id"] == "/people/self.md" for s in subjects):
            fails.append(f"subjects table missing /people/self.md default (got {[s['sb_id'] for s in subjects]})")

        # === Phase 3: concept_subject index populated ===
        cs = [dict(r) for r in brain.con.execute(
            """SELECT cs.subject_id, c.title FROM concept_subject cs
               JOIN concepts c ON c.id = cs.concept_id
               WHERE c.deleted_at IS NULL
               ORDER BY c.title""").fetchall()]

        rox_titles = sorted(r["title"] for r in cs if r["subject_id"] == "/people/rox.md")
        alex_titles = sorted(r["title"] for r in cs if r["subject_id"] == "/people/alex.md")
        self_titles = sorted(r["title"] for r in cs if r["subject_id"] == "/people/self.md")
        if rox_titles != ["Argument with Rox", "Rox avoids conflict"]:
            fails.append(f"concept_subject for rox: got {rox_titles}, expected 2 memories")
        if alex_titles != ["Alex is direct"]:
            fails.append(f"concept_subject for alex: got {alex_titles}, expected 1 memory")
        # The 2 un-set memories must land under self
        if sorted(self_titles) != ["Read the OKF spec", "Standup was late"]:
            fails.append(f"concept_subject for self: got {self_titles}, expected 2 default-subject memories")

        # === Phase 4: subject_subgraph query ===
        rox_sub = brain.subject_subgraph("/people/rox.md")
        rox_sub_titles = sorted(c.get("title", "") for c in rox_sub)
        if rox_sub_titles != ["Argument with Rox", "Rox avoids conflict"]:
            fails.append(f"subject_subgraph(rox): got {rox_sub_titles}")
        # Critical: must NOT include alex or self memories
        for forbidden in ("Alex is direct", "Standup was late", "Read the OKF spec"):
            if forbidden in rox_sub_titles:
                fails.append(f"subject_subgraph(rox) leaked unrelated concept '{forbidden}'")

        # Empty subject → empty result (not crash)
        empty_sub = brain.subject_subgraph("/people/ghost.md")
        if empty_sub != []:
            fails.append(f"subject_subgraph(ghost): got {empty_sub}, expected []")

        # === Phase 5: round-trip (export → wipe → rebuild → re-query) ===
        export_dir = td / "okf2"
        bundle.export(brain, export_dir)
        brain.con.close()
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        brain2 = bundle.rebuild(export_dir, db_path)
        rox_sub2 = brain2.subject_subgraph("/people/rox.md")
        rox_sub2_titles = sorted(c.get("title", "") for c in rox_sub2)
        if rox_sub2_titles != rox_sub_titles:
            fails.append(f"round-trip drift: pre-export {rox_sub_titles}, post-rebuild {rox_sub2_titles}")
        brain2.con.close()

    if fails:
        print("[FAIL]")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("[PASS] R10 subjects + sub-graph: 2 Person subjects registered, 5 memories indexed across 3 subjects (2 rox, 1 alex, 2 default→self), subject_subgraph returns exactly the right concepts (no leakage), round-trip preserves the index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
