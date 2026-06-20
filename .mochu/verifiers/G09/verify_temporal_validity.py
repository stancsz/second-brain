#!/usr/bin/env python3
"""G09 verifier — M1: bi-temporal validity STORAGE + supersession write-path.

R11's full bar (`--as-of` recall returns the historically-valid state) is M2.
THIS milestone (M1) proves the foundation R11 stands on: a Concept's validity
window (`sb_valid_from` / `sb_valid_to` / `sb_supersedes`) persists into a typed,
queryable `validity` table, round-trips through the OKF Bundle, and the
`supersede()` write-path correctly CLOSES the old fact's window and links the new
fact to it (the "a contradiction closes the old window rather than deleting it"
operation that Zep/Graphiti bi-temporal is built on).

Drives the REAL entry points end-to-end on a REAL SQLite + Bundle on disk:
  1. live add() with explicit validity → typed `validity` row.
  2. supersede(old, new) → old.valid_to set, new.supersedes=old, new.valid_from set.
  3. validity(id) getter (None when absent; partial window persists).
  4. round-trip: export → wipe → rebuild → validity identical.
  5. FK cascade: hard-delete a Concept → its validity row disappears.
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
from brain import SecondBrain  # noqa: E402


def main() -> int:
    fails = []

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        db_path = td / "brain.db"
        brain = SecondBrain(db_path)

        # validity table must EXIST (red before M1 is built)
        tbls = {r["name"] for r in brain.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "validity" not in tbls:
            brain.con.close()
            print("[FAIL]\n  - no `validity` table in schema (G09 M1 not built)")
            return 1

        # === 1. add() with an explicit validity window persists a typed row ===
        nyc = brain.add("Lives in NYC", "moved to Brooklyn", collection="facts",
                        sb_valid_from="2020-01-01", sb_valid_to="2023-06-01")
        v = brain.validity(nyc["id"])
        if not v or v.get("valid_from") != "2020-01-01" or v.get("valid_to") != "2023-06-01":
            fails.append(f"validity(nyc): got {v}, expected window 2020-01-01..2023-06-01")

        # a Concept with no validity has NO row and validity()==None
        plain = brain.add("Likes coffee", "espresso", collection="facts")
        if brain.validity(plain["id"]) is not None:
            fails.append(f"validity(plain): expected None, got {brain.validity(plain['id'])}")
        if brain.con.execute("SELECT 1 FROM validity WHERE concept_id=?",
                             (plain["id"],)).fetchone():
            fails.append("plain Concept (no validity) got a validity row")

        # partial window (valid_from only) persists; valid_to stays NULL
        part = brain.add("Started job", "new gig", collection="facts",
                         sb_valid_from="2024-01-15")
        vp = brain.validity(part["id"])
        if not vp or vp.get("valid_from") != "2024-01-15" or vp.get("valid_to") is not None:
            fails.append(f"validity(partial): got {vp}, expected valid_from only")

        # === 2. supersede() closes the old window and links the new fact ===
        sf = brain.supersede(nyc["id"], "Lives in SF", "moved to the Mission",
                             collection="facts", as_of="2023-06-01")
        # new fact links back to the old via sb_supersedes
        vsf = brain.validity(sf["id"])
        if not vsf or vsf.get("supersedes") != nyc["id"]:
            fails.append(f"supersede: new fact's supersedes={vsf and vsf.get('supersedes')}, "
                         f"expected {nyc['id']}")
        if not vsf or vsf.get("valid_from") != "2023-06-01":
            fails.append(f"supersede: new fact valid_from={vsf and vsf.get('valid_from')}, "
                         "expected 2023-06-01")
        # old fact's window is now CLOSED at as_of (not deleted)
        vnyc = brain.validity(nyc["id"])
        if not vnyc or vnyc.get("valid_to") != "2023-06-01":
            fails.append(f"supersede: old fact valid_to={vnyc and vnyc.get('valid_to')}, "
                         "expected closed at 2023-06-01")
        # the old fact still EXISTS (history preserved, not discarded)
        if brain.get(nyc["id"]) is None:
            fails.append("supersede deleted the old fact — bi-temporal must PRESERVE history")

        # === 3. update() can set and clear validity ===
        brain.update(part["id"], sb_valid_to="2024-12-31")
        if brain.validity(part["id"]).get("valid_to") != "2024-12-31":
            fails.append("update(sb_valid_to=...) did not set valid_to")
        brain.update(part["id"], sb_valid_from=None, sb_valid_to=None)
        if brain.validity(part["id"]) is not None:
            fails.append("update clearing both bounds did not remove the validity row")

        # === 4. round-trip: export → wipe → rebuild → validity identical ===
        export_dir = td / "okf"
        bundle.export(brain, export_dir)
        brain.con.close()
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        brain2 = bundle.rebuild(export_dir, db_path)
        # find rebuilt ids by title
        def _id(b, title):
            r = b.con.execute("SELECT id FROM concepts WHERE title=? AND deleted_at IS NULL",
                              (title,)).fetchone()
            return r["id"] if r else None
        nyc2 = _id(brain2, "Lives in NYC")
        sf2 = _id(brain2, "Lives in SF")
        v2 = brain2.validity(nyc2)
        if not v2 or v2.get("valid_from") != "2020-01-01" or v2.get("valid_to") != "2023-06-01":
            fails.append(f"round-trip drift (nyc validity): {v2}")
        vsf2 = brain2.validity(sf2)
        # supersedes is a Bundle path/id; after rebuild the new fact must still
        # reference the old fact's (preserved) id
        if not vsf2 or vsf2.get("supersedes") != nyc2:
            fails.append(f"round-trip drift (sf supersedes): {vsf2 and vsf2.get('supersedes')} "
                         f"vs {nyc2}")

        # === 5. FK cascade: hard-delete → validity row gone ===
        before = brain2.con.execute("SELECT COUNT(*) c FROM validity").fetchone()["c"]
        brain2.con.execute("DELETE FROM concepts WHERE id=?", (nyc2,))
        brain2.con.commit()
        after = brain2.con.execute("SELECT COUNT(*) c FROM validity").fetchone()["c"]
        if after != before - 1:
            fails.append(f"FK cascade: validity count {before}->{after}, expected drop of 1")
        brain2.con.close()

        # === 6. CLI surface: `brain show` prints the validity window ===
        cli_db = td / "cli.db"
        seed = SecondBrain(cli_db)
        seed.add("Tenure fact", "worked there", collection="facts",
                 sb_valid_from="2021-03-01", sb_valid_to="2022-09-01")
        seed.con.close()
        cli = REPO / "scripts" / "brain_cli.py"
        proc = subprocess.run(
            [sys.executable, str(cli), "--db", str(cli_db), "show", "Tenure fact"],
            capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            fails.append(f"CLI show exited {proc.returncode}: {proc.stderr.strip()[:200]}")
        elif "2021-03-01" not in proc.stdout or "2022-09-01" not in proc.stdout:
            fails.append(f"CLI show did not print the validity window; stdout: {proc.stdout[:200]}")

    if fails:
        print("[FAIL]")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("[PASS] G09 M1 bi-temporal storage: validity windows persist (partial + full), "
          "supersede() closes the old window and links the new fact WITHOUT deleting history, "
          "update sets/clears bounds, round-trip stable, FK cascade wired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
