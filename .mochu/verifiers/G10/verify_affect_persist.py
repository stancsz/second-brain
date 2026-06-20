#!/usr/bin/env python3
"""G10 verifier: R12 — structured affect persists and is QUERYABLE per Concept.

Per docs/04-psychological-memory.md §Affect and gaps.md G10, a memory may carry
`sb_affect: {valence, arousal, emotion, intensity}`. R12's bar is not merely
"the JSON survives a round-trip" (that is already true via concepts.metadata) —
it is that affect is *structured and queryable*: an emotional-mimic agent must
be able to ask "give me this subject's high-intensity grief episodes" and get an
exact set back. That requires a real `affect` table with typed columns, not a
JSON blob hidden in metadata.

This verifier drives the REAL entry points end-to-end on a REAL bundle on disk
(the same paths a user/hook hits), never mocked internals:

  1. Build an OKF Bundle: 5 affect-bearing Concepts (varied valence/arousal/
     emotion/intensity, incl. one PARTIAL affect = emotion only) + 1 with NO
     affect at all.
  2. bundle.rebuild() → populate SQLite.
  3. Assert the `affect` table holds exactly the 5 affect-bearing rows with the
     right typed values; the affectless Concept has NO affect row.
  4. Assert SecondBrain.affect(concept_id) returns the structured dict (None for
     the affectless one; partial fields = NULL for the partial one).
  5. Assert SecondBrain.recall_by_affect(...) answers RANGE + categorical
     queries with the exact right Concept set — the queryable core of R12.
  6. Round-trip: export → wipe brain.db → rebuild → re-query identical.
  7. FK cascade: hard-delete a Concept row → its affect row disappears.
  8. Live path: brain.add(sb_affect=...) populates the table immediately, and
     update() can set and clear affect.
"""
import json
import os
import subprocess
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


# 5 affect-bearing memories + 1 affectless. valence in [-1,1], intensity in [0,1].
MEMORIES = [
    {"sb_id": "e-001", "type": "Episode", "title": "Grief at the funeral",
     "body": "Stood at the grave. Could not speak.", "collection": "episodes",
     "sb_affect": {"valence": -0.8, "arousal": 0.3, "emotion": "grief", "intensity": 0.9}},
    {"sb_id": "e-002", "type": "Episode", "title": "Joy at the wedding",
     "body": "Danced until 2am.", "collection": "episodes",
     "sb_affect": {"valence": 0.9, "arousal": 0.7, "emotion": "joy", "intensity": 0.85}},
    {"sb_id": "e-003", "type": "Episode", "title": "Mild annoyance at the queue",
     "body": "The line barely moved.", "collection": "episodes",
     "sb_affect": {"valence": -0.3, "arousal": 0.4, "emotion": "annoyance", "intensity": 0.4}},
    {"sb_id": "e-004", "type": "Episode", "title": "Quiet grief months later",
     "body": "It comes back in waves.", "collection": "episodes",
     "sb_affect": {"valence": -0.6, "arousal": 0.2, "emotion": "grief", "intensity": 0.6}},
    # PARTIAL affect: only an emotion label, no numeric dimensions.
    {"sb_id": "e-005", "type": "Episode", "title": "A flicker of curiosity",
     "body": "What was behind that door?", "collection": "episodes",
     "sb_affect": {"emotion": "curiosity"}},
    # NO affect at all — must NOT get an affect row.
    {"sb_id": "n-006", "type": "Note", "title": "Standup ran late",
     "body": "Ten minutes over.", "collection": "notes"},
]


def write_bundle(bundle_dir: Path) -> None:
    for coll in ("episodes", "notes"):
        d = bundle_dir / coll
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.md").write_text(
            "---\ntype: Index\n---\n\n# " + coll.title() + "\n", encoding="utf-8")
    for m in MEMORIES:
        slug = m["title"].lower().replace(" ", "-")
        (bundle_dir / m["collection"] / f"{slug}.md").write_text(
            okf.to_markdown(m), encoding="utf-8")


def _id_by_title(brain, title):
    r = brain.con.execute(
        "SELECT id FROM concepts WHERE title=? AND deleted_at IS NULL", (title,)
    ).fetchone()
    return r["id"] if r else None


def _titles(concepts):
    return sorted(c.get("title", "") for c in concepts)


def main() -> int:
    fails = []

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bundle_dir = td / "okf"
        bundle_dir.mkdir()
        db_path = td / "brain.db"
        write_bundle(bundle_dir)

        # === Phase 1: rebuild from bundle ===
        brain = bundle.rebuild(bundle_dir, db_path)

        # The affect table must EXIST (red before this gap is built).
        tbls = {r["name"] for r in brain.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "affect" not in tbls:
            brain.con.close()
            print("[FAIL]\n  - no `affect` table in schema (R12 not built)")
            return 1

        # === Phase 2: affect table populated with exactly the 5 affect rows ===
        rows = {r["concept_id"]: r for r in brain.con.execute(
            "SELECT a.concept_id, a.valence, a.arousal, a.emotion, a.intensity, c.title "
            "FROM affect a JOIN concepts c ON c.id = a.concept_id").fetchall()}
        affect_titles = sorted(r["title"] for r in rows.values())
        expected_titles = sorted(m["title"] for m in MEMORIES if "sb_affect" in m)
        if affect_titles != expected_titles:
            fails.append(f"affect table rows: got {affect_titles}, expected {expected_titles}")

        # affectless Concept must have NO affect row
        n006 = _id_by_title(brain, "Standup ran late")
        if n006 in rows:
            fails.append("affectless Concept 'Standup ran late' got an affect row")

        # === Phase 3: affect(concept_id) returns the structured dict ===
        e001 = _id_by_title(brain, "Grief at the funeral")
        a = brain.affect(e001)
        want = {"valence": -0.8, "arousal": 0.3, "emotion": "grief", "intensity": 0.9}
        if not a or any(abs((a.get(k) or 0) - v) > 1e-9 if isinstance(v, float)
                        else a.get(k) != v for k, v in want.items()):
            fails.append(f"affect(grief funeral): got {a}, expected {want}")

        # affectless → None
        if brain.affect(n006) is not None:
            fails.append(f"affect(affectless): got {brain.affect(n006)}, expected None")

        # partial affect: emotion set, numeric dims NULL (not 0, not crash)
        e005 = _id_by_title(brain, "A flicker of curiosity")
        ap = brain.affect(e005)
        if not ap or ap.get("emotion") != "curiosity":
            fails.append(f"affect(partial): got {ap}, expected emotion=curiosity")
        elif ap.get("valence") is not None or ap.get("intensity") is not None:
            fails.append(f"affect(partial): numeric dims should be None, got {ap}")

        # === Phase 4: recall_by_affect — the queryable core of R12 ===
        # categorical: emotion
        grief = brain.recall_by_affect(emotion="grief")
        if _titles(grief) != ["Grief at the funeral", "Quiet grief months later"]:
            fails.append(f"recall_by_affect(emotion=grief): got {_titles(grief)}")
        # must return full Concept dicts (queryable PER CONCEPT), not bare ids
        if grief and not all(c.get("body") for c in grief):
            fails.append("recall_by_affect returned concepts without body — not full Concept dicts")

        # range: min_intensity
        intense = brain.recall_by_affect(min_intensity=0.7)
        if _titles(intense) != ["Grief at the funeral", "Joy at the wedding"]:
            fails.append(f"recall_by_affect(min_intensity=0.7): got {_titles(intense)}")

        # range: max_valence (strongly negative)
        neg = brain.recall_by_affect(max_valence=-0.5)
        if _titles(neg) != ["Grief at the funeral", "Quiet grief months later"]:
            fails.append(f"recall_by_affect(max_valence=-0.5): got {_titles(neg)}")

        # range: min_valence (positive)
        pos = brain.recall_by_affect(min_valence=0.5)
        if _titles(pos) != ["Joy at the wedding"]:
            fails.append(f"recall_by_affect(min_valence=0.5): got {_titles(pos)}")

        # combined: grief AND high intensity → only the funeral
        gi = brain.recall_by_affect(emotion="grief", min_intensity=0.8)
        if _titles(gi) != ["Grief at the funeral"]:
            fails.append(f"recall_by_affect(grief, min_intensity=0.8): got {_titles(gi)}")

        # a partial-affect row must not satisfy a numeric range (its valence is NULL)
        cur = brain.recall_by_affect(min_intensity=0.0)
        if "A flicker of curiosity" in _titles(cur):
            fails.append("partial-affect (NULL intensity) leaked into min_intensity=0.0 query")

        # === Phase 5: round-trip (export → wipe → rebuild → re-query) ===
        export_dir = td / "okf2"
        bundle.export(brain, export_dir)
        brain.con.close()
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        brain2 = bundle.rebuild(export_dir, db_path)
        e001b = _id_by_title(brain2, "Grief at the funeral")
        if brain2.affect(e001b) != want:
            fails.append(f"round-trip drift: affect now {brain2.affect(e001b)}, was {want}")
        if _titles(brain2.recall_by_affect(emotion="grief")) != \
                ["Grief at the funeral", "Quiet grief months later"]:
            fails.append("round-trip drift: grief query changed after rebuild")

        # === Phase 6: FK cascade — hard-delete Concept → affect row gone ===
        before = brain2.con.execute("SELECT COUNT(*) c FROM affect").fetchone()["c"]
        brain2.con.execute("DELETE FROM concepts WHERE id=?", (e001b,))
        brain2.con.commit()
        after = brain2.con.execute("SELECT COUNT(*) c FROM affect").fetchone()["c"]
        if after != before - 1:
            fails.append(f"FK cascade: affect count {before}->{after}, expected drop of 1 "
                         "(ON DELETE CASCADE not wired)")
        if brain2.con.execute(
                "SELECT 1 FROM affect WHERE concept_id=?", (e001b,)).fetchone():
            fails.append("FK cascade: orphan affect row survived Concept hard-delete")
        brain2.con.close()

        # === Phase 7: live add/update path (not just bundle rebuild) ===
        live_db = td / "live.db"
        from brain import SecondBrain  # noqa: E402
        live = SecondBrain(live_db)
        c = live.add("Live joy", "felt great", collection="episodes",
                     sb_affect={"valence": 0.7, "arousal": 0.5, "emotion": "joy", "intensity": 0.6})
        la = live.affect(c["id"])
        if not la or la.get("emotion") != "joy" or abs((la.get("valence") or 0) - 0.7) > 1e-9:
            fails.append(f"live add(sb_affect): got {la}, expected joy/0.7")
        # update clears affect
        live.update(c["id"], sb_affect=None)
        if live.affect(c["id"]) is not None:
            fails.append(f"update(sb_affect=None) did not clear affect: {live.affect(c['id'])}")
        # update sets new affect
        live.update(c["id"], sb_affect={"emotion": "calm", "intensity": 0.2})
        la2 = live.affect(c["id"])
        if not la2 or la2.get("emotion") != "calm":
            fails.append(f"update(sb_affect=...) did not set affect: {la2}")
        live.con.close()

        # === Phase 8: CLI surface — recall-affect via subprocess (real entry point) ===
        cli_db = td / "cli.db"
        seed = SecondBrain(cli_db)
        seed.add("CLI grief", "a heavy day", collection="episodes",
                 sb_affect={"valence": -0.7, "arousal": 0.3, "emotion": "grief", "intensity": 0.8})
        seed.add("CLI joy", "a bright day", collection="episodes",
                 sb_affect={"valence": 0.8, "arousal": 0.6, "emotion": "joy", "intensity": 0.7})
        seed.con.close()
        cli = REPO / "scripts" / "brain_cli.py"
        proc = subprocess.run(
            [sys.executable, str(cli), "--db", str(cli_db), "--json",
             "recall-affect", "--emotion", "grief"],
            capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            fails.append(f"CLI recall-affect exited {proc.returncode}: {proc.stderr.strip()[:200]}")
        else:
            try:
                payload = json.loads(proc.stdout)
                cli_titles = sorted(c.get("title", "") for c in payload.get("concepts", []))
            except (ValueError, AttributeError):
                cli_titles = None
                fails.append(f"CLI recall-affect --json not parseable: {proc.stdout[:200]}")
            if cli_titles is not None and cli_titles != ["CLI grief"]:
                fails.append(f"CLI recall-affect(emotion=grief): got {cli_titles}, expected ['CLI grief']")

    if fails:
        print("[FAIL]")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("[PASS] R12 structured affect: 5 affect rows persisted (1 partial, affectless gets none), "
          "affect() returns typed dicts, recall_by_affect answers categorical + range + combined "
          "queries with exact sets, round-trip stable, FK cascade wired, live add/update path works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
