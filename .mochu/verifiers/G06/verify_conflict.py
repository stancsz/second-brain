#!/usr/bin/env python3
"""G06 verifier — per-concept conflict parking (no clobber, no crash).

Claim: when two devices edit the SAME concept concurrently, sync does not crash
and does not silently clobber one side. The incoming rebase conflict is parked:
the bundle keeps one canonical version plus a `<slug>.conflict.md` holding the
other, `conflicts()` lists it, the rebuilt brain imports the canonical concept
only (conflict copies are not imported), and the working tree is left clean
(no rebase in progress). Both edits are preserved. (RELEASE R6)

Real git: bare remote + two clones driving scripts/sync.py.
"""
import sys, subprocess, tempfile, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
from brain import SecondBrain  # noqa: E402
import sync as syncmod  # noqa: E402

fails = []


def check(c, m):
    if not c:
        fails.append(m)


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def id_of(db, title):
    b = SecondBrain(db)
    d = next((x for x in b.list(limit=99) if x["title"] == title), None)
    b.close()
    return d["id"] if d else None


def body_of(db, title):
    b = SecondBrain(db)
    d = next((x for x in b.list(limit=99) if x["title"] == title), None)
    b.close()
    return d["content"] if d else None


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        remote = tmp / "remote.git"
        git(["init", "--bare", str(remote)], tmp)
        a_dir, a_db = tmp / "A", tmp / "a.db"
        b_dir, b_db = tmp / "B", tmp / "b.db"

        ba = SecondBrain(a_db)
        ba.add("Shared", "original body", collection="Notes")
        ba.close()
        syncmod.sync(a_db, a_dir, remote=remote)
        git(["clone", str(remote), str(b_dir)], tmp)
        syncmod.sync(b_db, b_dir, remote=remote)

        # A edits Shared and pushes.
        sid_a = id_of(a_db, "Shared")
        ba = SecondBrain(a_db); ba.update(sid_a, content="A's version of the body"); ba.close()
        syncmod.sync(a_db, a_dir, remote=remote)

        # B edits the SAME concept differently, then syncs -> conflict.
        sid_b = id_of(b_db, "Shared")
        bb = SecondBrain(b_db); bb.update(sid_b, content="B's totally different body"); bb.close()
        try:
            res = syncmod.sync(b_db, b_dir, remote=remote)
        except Exception as e:  # noqa: BLE001
            fails.append(f"sync CRASHED on a concurrent same-concept edit: {e!r}")
            res = {}

        # Working tree must be clean — no rebase left in progress.
        rebase_dirs = (b_dir / ".git" / "rebase-merge", b_dir / ".git" / "rebase-apply")
        check(not any(d.exists() for d in rebase_dirs),
              "rebase left in progress after sync (conflict not resolved)")
        st = git(["status", "--porcelain"], b_dir).stdout.strip()
        check(st == "", f"working tree not clean after conflict parking: {st!r}")

        # A conflict copy exists and is listed.
        listed = syncmod.conflicts(b_dir)
        check(len(listed) >= 1, "conflicts() did not list the parked conflict")
        conflict_files = list(b_dir.rglob("*.conflict.md"))
        check(len(conflict_files) >= 1, "no *.conflict.md file parked in the bundle")

        # Both versions are preserved across canonical + conflict copy.
        all_text = ""
        for f in b_dir.rglob("*.md"):
            all_text += f.read_text(encoding="utf-8")
        check("A's version of the body" in all_text, "device A's edit was lost (clobbered)")
        check("B's totally different body" in all_text, "device B's edit was lost (clobbered)")

        # Rebuilt brain has exactly ONE 'Shared' drawer (conflict copy not imported).
        nshared = sum(1 for d in SecondBrain(b_db).list(limit=99) if d["title"] == "Shared")
        check(nshared == 1, f"expected 1 'Shared' drawer after rebuild, got {nshared} "
                            "(conflict copy wrongly imported?)")

        # A subsequent sync is clean (no crash, no perpetual conflict).
        try:
            syncmod.sync(b_db, b_dir, remote=remote)
        except Exception as e:  # noqa: BLE001
            fails.append(f"follow-up sync crashed: {e!r}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("CONFLICT FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("CONFLICT PASS: concurrent same-concept edits park as *.conflict.md, no clobber, "
          "no crash, clean tree, single canonical import")


if __name__ == "__main__":
    main()
