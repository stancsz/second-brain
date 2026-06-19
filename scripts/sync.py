#!/usr/bin/env python3
"""Git sync spine — the single bidirectional channel for portable memory.

Files are the source of truth; git is the only multi-device sync mechanism (it
already is a hardened multi-master, offline, conflict-resolving engine). One
`sync()` does: serialize brain.db → OKF Bundle, commit, pull --rebase, push,
then rebuild brain.db from the merged Bundle. Cloud backends are one-way
mirrors layered on top later (G11+); conflict parking is G06.

stdlib only; shells out to the `git` CLI.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import bundle
from brain import SecondBrain


def _git(args, cwd, check=True):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r


def ensure_repo(bundle_dir) -> Path:
    """Make bundle_dir a git repo with a commit identity (idempotent)."""
    bundle_dir = Path(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    if not (bundle_dir / ".git").exists():
        _git(["init"], bundle_dir)
    if _git(["config", "user.email"], bundle_dir, check=False).returncode != 0:
        _git(["config", "user.email", "secondbrain@local"], bundle_dir)
        _git(["config", "user.name", "SecondBrain"], bundle_dir)
    return bundle_dir


def _current_branch(bundle_dir):
    r = _git(["rev-parse", "--abbrev-ref", "HEAD"], bundle_dir, check=False)
    if r.returncode != 0:
        return None
    branch = r.stdout.strip()
    return branch if branch and branch != "HEAD" else None


def sync(db_path, bundle_dir, remote=None, message="secondbrain sync") -> dict:
    """Serialize → commit → pull --rebase → push → rebuild. Returns a summary.

    `remote` may be a path (local/bare repo) or URL. If given and not yet
    configured as `origin`, it is added.
    """
    bundle_dir = ensure_repo(bundle_dir)
    if remote:
        have = _git(["remote"], bundle_dir).stdout.split()
        if "origin" not in have:
            _git(["remote", "add", "origin", str(remote)], bundle_dir)

    # 1. Serialize the brain into the Bundle (files are the source of truth).
    b = SecondBrain(db_path)
    bundle.export(b, bundle_dir)
    b.checkpoint_and_close()  # flush WAL so rebuild can replace the file (Windows)

    # 2. Commit local changes (skip if the tree is clean — deterministic export
    #    means unchanged drawers produce no diff).
    _git(["add", "-A"], bundle_dir)
    committed = _git(["diff", "--cached", "--quiet"], bundle_dir, check=False).returncode != 0
    if committed:
        _git(["commit", "-m", message], bundle_dir)

    branch = _current_branch(bundle_dir)
    pulled = pushed = False
    if remote and branch:
        # 3. Pull --rebase if the remote already has this branch.
        ls = _git(["ls-remote", "--heads", "origin", branch], bundle_dir, check=False)
        if ls.stdout.strip():
            _git(["pull", "--rebase", "origin", branch], bundle_dir)
            pulled = True
        # 4. Push.
        _git(["push", "-u", "origin", branch], bundle_dir)
        pushed = True

    # 5. Rebuild brain.db from the (now merged) Bundle so the cache reflects
    #    everything that arrived from the remote. Close the handle (the rebuilt
    #    brain is a fresh connection we don't keep open here).
    bundle.rebuild(bundle_dir, db_path).checkpoint_and_close()

    return {"branch": branch, "committed": committed, "pulled": pulled,
            "pushed": pushed, "bundle": str(bundle_dir)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: sync.py <bundle_dir> [remote] [db_path]")
        sys.exit(0)
    bdir = sys.argv[1]
    rem = sys.argv[2] if len(sys.argv) > 2 else None
    db = sys.argv[3] if len(sys.argv) > 3 else SecondBrain().db_path
    print(sync(db, bdir, remote=rem))
