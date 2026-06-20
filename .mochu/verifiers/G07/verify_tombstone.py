#!/usr/bin/env python3
"""G07 verifier — tombstone deletes propagate over git; no resurrection.

Claim: deletes survive sync. A soft-delete on device A moves the concept to
`.trash/` as a tombstone (sb_deleted) and propagates to device B (the drawer
becomes not-alive there); `restore` reverses it across devices; a hard-delete
removes the file so it is gone everywhere and never resurrects on rebuild.
(RELEASE R7, and fixes additive-export resurrection.)

Real git: bare remote + two clones, driving scripts/sync.py.
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


def alive_titles(db):
    b = SecondBrain(db)
    t = sorted(d["title"] for d in b.list(limit=10**9))
    b.close()
    return t


def id_of(db, title):
    b = SecondBrain(db)
    d = next((x for x in b.list(limit=10**9) if x["title"] == title), None)
    b.close()
    return d["id"] if d else None


def live_md_titles(bundle_dir):
    """Titles of concept files NOT under .trash and not reserved."""
    out = []
    for f in Path(bundle_dir).rglob("*.md"):
        rel = f.relative_to(bundle_dir).as_posix()
        if rel.startswith(".trash/") or ".git/" in rel or f.name in ("index.md", "log.md"):
            continue
        for ln in f.read_text(encoding="utf-8").splitlines():
            if ln.startswith("title:"):
                out.append(ln.split(":", 1)[1].strip().strip('"'))
                break
    return out


def trash_titles(bundle_dir):
    out = []
    tdir = Path(bundle_dir) / ".trash"
    if tdir.exists():
        for f in tdir.rglob("*.md"):
            for ln in f.read_text(encoding="utf-8").splitlines():
                if ln.startswith("title:"):
                    out.append(ln.split(":", 1)[1].strip().strip('"'))
                    break
    return out


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        remote = tmp / "remote.git"
        git(["init", "--bare", str(remote)], tmp)
        a_dir, a_db = tmp / "A", tmp / "a.db"
        b_dir, b_db = tmp / "B", tmp / "b.db"

        ba = SecondBrain(a_db)
        ba.add("Keeper", "stays around", collection="Notes")
        ba.add("Doomed", "will be soft-deleted", collection="Notes")
        ba.add("Purged", "will be hard-deleted", collection="Notes")
        ba.close()
        syncmod.sync(a_db, a_dir, remote=remote)
        git(["clone", str(remote), str(b_dir)], tmp)
        syncmod.sync(b_db, b_dir, remote=remote)
        check(alive_titles(b_db) == ["Doomed", "Keeper", "Purged"],
              f"B initial state wrong: {alive_titles(b_db)}")

        # --- soft delete Doomed on A ---
        doomed = id_of(a_db, "Doomed")
        ba = SecondBrain(a_db); ba.delete(doomed); ba.close()
        syncmod.sync(a_db, a_dir, remote=remote)
        check("Doomed" in trash_titles(a_dir), "soft-deleted concept not moved to .trash/ on A")
        check("Doomed" not in live_md_titles(a_dir),
              "soft-deleted concept still present in a live collection dir on A")

        syncmod.sync(b_db, b_dir, remote=remote)
        check("Doomed" not in alive_titles(b_db),
              "soft-delete did not propagate to B (Doomed still alive)")
        check("Keeper" in alive_titles(b_db), "Keeper wrongly affected on B")
        check("Doomed" in trash_titles(b_dir), "tombstone not present under B/.trash")

        # --- restore Doomed on A, propagate ---
        ba = SecondBrain(a_db); ba.restore(doomed); ba.close()
        syncmod.sync(a_db, a_dir, remote=remote)
        check("Doomed" in live_md_titles(a_dir), "restore did not move concept back to live dir")
        check("Doomed" not in trash_titles(a_dir), "restored concept still in .trash on A")
        syncmod.sync(b_db, b_dir, remote=remote)
        check("Doomed" in alive_titles(b_db), "restore did not propagate to B")

        # --- hard delete Purged on A: must vanish everywhere, no resurrection ---
        purged = id_of(a_db, "Purged")
        ba = SecondBrain(a_db); ba.delete(purged, hard=True); ba.close()
        syncmod.sync(a_db, a_dir, remote=remote)
        check("Purged" not in live_md_titles(a_dir) and "Purged" not in trash_titles(a_dir),
              "hard-deleted concept file not removed from bundle (resurrection risk)")
        syncmod.sync(b_db, b_dir, remote=remote)
        check("Purged" not in alive_titles(b_db), "hard-delete did not propagate to B")
        # Re-sync B twice: a resurrection bug would re-add it from a lingering file.
        syncmod.sync(b_db, b_dir, remote=remote)
        check("Purged" not in alive_titles(b_db), "hard-deleted concept RESURRECTED on resync")

        check(alive_titles(a_db) == alive_titles(b_db) == ["Doomed", "Keeper"],
              f"final divergence: A={alive_titles(a_db)} B={alive_titles(b_db)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("TOMBSTONE FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("TOMBSTONE PASS: soft-delete->.trash propagates, restore reverses, "
          "hard-delete removes file with no resurrection")


if __name__ == "__main__":
    main()
