#!/usr/bin/env python3
"""G05 verifier — git sync spine, multi-device round-trip.

Claim: `sync(db, bundle, remote)` serializes the brain to the OKF Bundle,
commits, pulls --rebase, pushes, and rebuilds — so two devices sharing a git
remote converge. A drawer created on device A appears on device B after sync,
and a drawer created on B later appears back on A. (RELEASE R5)

Uses a local bare repo as the "remote" and two clones as devices A and B —
real git, no network. Executes the real scripts/sync.py.
"""
import sys, subprocess, tempfile, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
from brain import SecondBrain  # noqa: E402
import sync as syncmod  # noqa: E402  (scripts/sync.py — absence = RED pre-build)

fails = []


def check(c, m):
    if not c:
        fails.append(m)


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def titles(db):
    b = SecondBrain(db)
    t = sorted(d["title"] for d in b.list(limit=10**9))
    b.close()
    return t


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        remote = tmp / "remote.git"
        git(["init", "--bare", str(remote)], tmp)

        # --- Device A: create content, sync (push) ---
        a_dir = tmp / "A"
        a_db = tmp / "a.db"
        ba = SecondBrain(a_db)
        ba.add("Alpha note", "First device content. See [[Beta note]].",
               collection="Work", tags=["x"])
        ba.add("Beta note", "Second concept on A.", collection="Work")
        ba.close()
        r1 = syncmod.sync(a_db, a_dir, remote=remote)
        check(r1.get("pushed"), "device A sync did not push")

        # --- Device B: fresh clone, sync (pull) ---
        b_dir = tmp / "B"
        git(["clone", str(remote), str(b_dir)], tmp)
        b_db = tmp / "b.db"
        syncmod.sync(b_db, b_dir, remote=remote)
        tb = titles(b_db)
        check("Alpha note" in tb and "Beta note" in tb,
              f"device B did not receive A's drawers after sync: {tb}")

        # wikilink relation survived the trip
        bb = SecondBrain(b_db)
        alpha = next((d for d in bb.list(limit=99) if d["title"] == "Alpha note"), None)
        check(alpha is not None and len(bb.related(alpha["id"], limit=9)) >= 1,
              "wikilink relation missing on device B after sync")
        bb.close()

        # --- Device B adds content, syncs back ---
        bb = SecondBrain(b_db)
        bb.add("Gamma note", "Created on device B.", collection="Work")
        bb.close()
        syncmod.sync(b_db, b_dir, remote=remote)

        # --- Device A pulls B's new content ---
        syncmod.sync(a_db, a_dir, remote=remote)
        ta = titles(a_db)
        check("Gamma note" in ta, f"device A did not receive B's new drawer: {ta}")

        # Convergence: both devices see the same set.
        check(titles(a_db) == titles(b_db),
              f"devices diverged: A={titles(a_db)} B={titles(b_db)}")

        # Re-syncing with no changes is a no-op commit (deterministic serialization).
        r_noop = syncmod.sync(a_db, a_dir, remote=remote)
        check(not r_noop.get("committed"),
              "re-sync with no changes produced a spurious commit (non-deterministic export)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("GIT SYNC FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("GIT SYNC PASS: A->B and B->A multi-device round-trip via git remote; converged; "
          "no-op resync clean")


if __name__ == "__main__":
    main()
