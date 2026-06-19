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


def _is_fresh_device(db_path, bundle_dir) -> bool:
    """True if the db has zero drawers but the Bundle already holds concept
    files — i.e. a fresh clone whose cache hasn't been imported yet."""
    bundle_dir = Path(bundle_dir)
    has_concepts = any(
        f.name not in ("index.md", "log.md")
        and ".git/" not in f.relative_to(bundle_dir).as_posix()
        for f in bundle_dir.rglob("*.md")
    )
    if not has_concepts:
        return False
    if not Path(db_path).exists():
        return True
    b = SecondBrain(db_path)
    n = b.con.execute("SELECT COUNT(*) c FROM drawers").fetchone()["c"]
    b.close()
    return n == 0


def _rebase_in_progress(bundle_dir) -> bool:
    g = Path(bundle_dir) / ".git"
    return (g / "rebase-merge").exists() or (g / "rebase-apply").exists()


def _conflict_name(bundle_dir, rel) -> str:
    base = rel[:-3] if rel.endswith(".md") else rel
    cand = f"{base}.conflict.md"
    i = 2
    while (Path(bundle_dir) / cand).exists():
        cand = f"{base}.conflict.{i}.md"
        i += 1
    return cand


def _take_stage(bundle_dir, rel, stage) -> None:
    """Resolve a conflicted path by taking one stage (e.g. ':2' = ours/upstream)."""
    r = _git(["show", f"{stage}:{rel}"], bundle_dir, check=False)
    p = Path(bundle_dir) / rel
    if r.returncode == 0:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(r.stdout, encoding="utf-8")
        _git(["add", "--", rel], bundle_dir, check=False)
    else:
        # Added on only one side / deleted: fall back to checkout --ours.
        if _git(["checkout", "--ours", "--", rel], bundle_dir, check=False).returncode == 0:
            _git(["add", "--", rel], bundle_dir, check=False)
        else:
            _git(["rm", "-f", "--", rel], bundle_dir, check=False)


def _is_concept_rel(rel) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return (rel.endswith(".md") and name not in ("index.md", "log.md")
            and not rel.endswith(".conflict.md"))


def _park_rebase_conflicts(bundle_dir) -> list:
    """Drive a conflicted rebase to completion by parking each conflicting
    concept: keep the upstream version (stage :2, 'ours' during rebase) as
    canonical and write the incoming local version (stage :3) to a sibling
    `<slug>.conflict.md`. Reserved/other files take the upstream side (they are
    regenerated on the next export). Leaves a clean tree."""
    parked = []
    for _ in range(200):  # safety cap over multiple replayed commits
        if not _rebase_in_progress(bundle_dir):
            break
        unmerged = _git(["diff", "--name-only", "--diff-filter=U"], bundle_dir,
                        check=False).stdout.split()
        for rel in unmerged:
            if _is_concept_rel(rel):
                ours = _git(["show", f":2:{rel}"], bundle_dir, check=False).stdout
                theirs = _git(["show", f":3:{rel}"], bundle_dir, check=False).stdout
                cpath = _conflict_name(bundle_dir, rel)
                (Path(bundle_dir) / rel).write_text(ours, encoding="utf-8")
                (Path(bundle_dir) / cpath).write_text(theirs, encoding="utf-8")
                _git(["add", "--", rel, cpath], bundle_dir, check=False)
                parked.append(cpath)
            else:
                _take_stage(bundle_dir, rel, ":2")
        cont = _git(["-c", "core.editor=true", "rebase", "--continue"],
                    bundle_dir, check=False)
        still = _git(["diff", "--name-only", "--diff-filter=U"], bundle_dir,
                     check=False).stdout.strip()
        if cont.returncode != 0 and not still and _rebase_in_progress(bundle_dir):
            # Cannot make progress — abort to guarantee a clean tree.
            _git(["rebase", "--abort"], bundle_dir, check=False)
            break
    return parked


def conflicts(bundle_dir) -> list:
    """List parked conflict copies (bundle-relative paths) awaiting resolution."""
    bundle_dir = Path(bundle_dir)
    return sorted(f.relative_to(bundle_dir).as_posix()
                  for f in bundle_dir.rglob("*.conflict.md"))


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

    # Detect a fresh device: a db with no drawers but a Bundle that already has
    # concepts (e.g. a brand-new clone). Exporting an empty db would (correctly)
    # mean "delete everything" — so instead we skip the export and let the rebuild
    # below import the Bundle. Once imported, the db is non-empty and subsequent
    # syncs take the normal incremental-export path.
    fresh = _is_fresh_device(db_path, bundle_dir)

    committed = False
    if not fresh:
        # 1. Serialize local edits into the Bundle (incremental — only changes).
        b = SecondBrain(db_path)
        bundle.export(b, bundle_dir)
        b.checkpoint_and_close()  # flush WAL so rebuild can replace the file (Windows)

        # 2. Commit local changes (skip if the tree is clean).
        _git(["add", "-A"], bundle_dir)
        committed = _git(["diff", "--cached", "--quiet"], bundle_dir,
                         check=False).returncode != 0
        if committed:
            _git(["commit", "-m", message], bundle_dir)

    branch = _current_branch(bundle_dir)
    pulled = pushed = False
    if remote and branch:
        # 3. Pull --rebase if the remote already has this branch. On a conflict
        #    (concurrent edits to the same concept), park instead of crashing.
        ls = _git(["ls-remote", "--heads", "origin", branch], bundle_dir, check=False)
        if ls.stdout.strip():
            pr = _git(["pull", "--rebase", "origin", branch], bundle_dir, check=False)
            if pr.returncode != 0:
                _park_rebase_conflicts(bundle_dir)
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
