#!/usr/bin/env python3
"""Git sync spine — the single bidirectional channel for portable memory.

Files are the source of truth; git is the only multi-device sync mechanism (it
already is a hardened multi-master, offline, conflict-resolving engine). One
`sync()` does: serialize brain.db → OKF Bundle, commit, pull --rebase, validate
and rebuild from the merged Bundle, then push. Cloud backends are one-way
mirrors layered on top later (G11+); conflict parking is G06.

stdlib only; shells out to the `git` CLI.
"""
from __future__ import annotations

import subprocess
import os
from pathlib import Path

import bundle
import store
from brain import SecondBrain


BUNDLE_GITIGNORE_RULES = (
    "# second-brain local state and secrets (managed by scripts/sync.py)",
    "*.key",
    "secret.key",
    "*.db",
    "*.db-journal",
    "*.db-wal",
    "*.db-shm",
    ".env",
    ".env.*",
    ".secondbrain-dirty",
    ".secondbrain-state.json",
)


def _ensure_bundle_gitignore(bundle_dir: Path) -> Path:
    """Add the minimum secret/local-state rules without replacing user rules."""
    path = Path(bundle_dir) / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    missing = [rule for rule in BUNDLE_GITIGNORE_RULES if rule not in lines]
    if missing:
        prefix = "\n" if existing and not existing.endswith("\n") else ""
        separator = "\n" if existing.strip() else ""
        path.write_text(
            existing + prefix + separator + "\n".join(missing) + "\n",
            encoding="utf-8",
        )
    return path


def _encryption_preflight(db_path) -> int:
    """Return the private Concept count, refusing strict sync before git changes.

    `bundle.export()` also enforces strict mode. This earlier check exists so a
    refusal happens before `ensure_repo()` initializes a repository, adds a remote,
    stages files, commits, or begins a rebase.
    """
    strict = str(os.environ.get("SECONDBRAIN_REQUIRE_ENCRYPTION", "")).lower() \
        in ("1", "true", "yes", "on")
    brain = SecondBrain(db_path)
    try:
        rows = brain.con.execute("SELECT * FROM concepts WHERE deleted_at IS NULL").fetchall()
        private_count = sum(
            1 for row in rows
            if bundle.crypto.is_private(bundle._concept_to_concept(brain, row))
        )
    finally:
        brain.close()
    if strict and private_count and not bundle.crypto.available():
        raise bundle.crypto.EncryptionUnavailable(
            f"sync refused before touching git: {private_count} private Concept(s) "
            "need encryption, but no encryption backend/key is available. Run "
            "`python scripts/crypto.py init` or unset "
            "SECONDBRAIN_REQUIRE_ENCRYPTION only if plaintext export is intentional."
        )
    return private_count


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
    _ensure_bundle_gitignore(bundle_dir)
    # Pair receipts are portable in verified snapshots but local to each Git
    # checkout. Older versions briefly tracked them, so migrate safely without
    # deleting the working file.
    _git(["rm", "--cached", "--ignore-unmatch", "--", store.PAIR_STATE],
         bundle_dir, check=False)
    return bundle_dir


def _is_fresh_device(db_path, bundle_dir) -> bool:
    """True if the db has zero concepts but the Bundle already holds concept
    files — i.e. a fresh clone whose cache hasn't been imported yet."""
    bundle_dir = Path(bundle_dir)
    has_concepts = any(
        f.name not in ("index.md", "log.md")
        and not f.name.endswith(".conflict.md")
        and ".git" not in f.relative_to(bundle_dir).parts
        for f in bundle_dir.rglob("*.md")
    )
    if not has_concepts:
        return False
    if not Path(db_path).exists():
        return True
    b = SecondBrain(db_path)
    n = b.con.execute("SELECT COUNT(*) c FROM concepts").fetchone()["c"]
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
    """Serialize → commit → pull --rebase → staged rebuild → push.

    `remote` may be a path (local/bare repo) or URL. If given and not yet
    configured as `origin`, it is added.
    """
    bundle_dir = Path(bundle_dir)
    with store.bundle_lock(bundle_dir):
        private_count = _encryption_preflight(db_path)
        bundle_dir = ensure_repo(bundle_dir)
        if remote:
            have = _git(["remote"], bundle_dir).stdout.split()
            if "origin" not in have:
                _git(["remote", "add", "origin", str(remote)], bundle_dir)

    # Detect a fresh device: a db with no concepts but a Bundle that already has
    # concepts (e.g. a brand-new clone). Exporting an empty db would (correctly)
    # mean "delete everything" — so instead we skip the export and let the rebuild
    # below import the Bundle. Once imported, the db is non-empty and subsequent
    # syncs take the normal incremental-export path.
        pending = store.sync_pending(bundle_dir)
        fresh = _is_fresh_device(db_path, bundle_dir)

        committed = False
        if pending:
            # A prior pull/rebase may already have changed Markdown. The Bundle
            # is authoritative for this recovery path; never export the stale
            # pre-pull SQLite back over it.
            fresh = True
        elif not fresh:
            # Validate the existing pair before serializing. This closes the
            # long-lived/stale-writer path where an external Markdown edit would
            # otherwise be silently overwritten by sync.
            existing = store.open_brain(db_path, bundle_dir)
            try:
                # Re-check immediately before the write-through. The outer
                # Bundle lock protects cooperating writers; the export
                # round-trip below also detects a non-cooperating edit that
                # lands during materialization.
                store._validate_existing_pair(existing, bundle_dir)
                store.replace_canonical(existing, bundle_dir)
            finally:
                existing.checkpoint_and_close()

            _git(["add", "-A"], bundle_dir)
            _git(["reset", "--quiet", "--", store.PAIR_STATE], bundle_dir, check=False)
            committed = _git(["diff", "--cached", "--quiet"], bundle_dir,
                             check=False).returncode != 0
            if committed:
                _git(["commit", "-m", message], bundle_dir)

        # The receipt is local to this checkout and is never part of Git
        # history. Once a pull can mutate Markdown, journal that direction.
        store.begin_sync(bundle_dir)
        branch = _current_branch(bundle_dir)
        pulled = pushed = False
        if remote and branch:
            # Pull --rebase if the remote already has this branch. On a conflict
            # (concurrent edits to the same concept), park instead of crashing.
            ls = _git(["ls-remote", "--heads", "origin", branch], bundle_dir, check=False)
            if ls.stdout.strip():
                pr = _git(["pull", "--rebase", "origin", branch], bundle_dir, check=False)
                if pr.returncode != 0:
                    _park_rebase_conflicts(bundle_dir)
                pulled = True

        # Validate the merged Bundle by constructing a complete staged
        # projection before push. bundle.rebuild atomically replaces the DB
        # only after parse/decrypt/relations/index validation succeeds.
        rebuilt = bundle.rebuild(bundle_dir, db_path)
        try:
            store.finish_sync(rebuilt, bundle_dir)
        finally:
            rebuilt.checkpoint_and_close()

        # Normalization may update generated indexes. Commit those bytes, while
        # keeping the per-checkout pair receipt out of Git.
        _git(["add", "-A"], bundle_dir)
        _git(["reset", "--quiet", "--", store.PAIR_STATE], bundle_dir, check=False)
        normalized = _git(["diff", "--cached", "--quiet"], bundle_dir,
                          check=False).returncode != 0
        if normalized:
            _git(["commit", "-m", f"{message} (merged Bundle)"], bundle_dir)
        committed = committed or normalized

        # Push only a validated and locally rebuildable Bundle.
        if remote and branch:
            _git(["push", "-u", "origin", branch], bundle_dir)
            pushed = True

        plaintext_private = private_count if private_count and not bundle.crypto.available() else 0
        return {"branch": branch, "committed": committed, "pulled": pulled,
                "pushed": pushed, "bundle": str(bundle_dir),
                "plaintext_private": plaintext_private}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: sync.py <bundle_dir> [remote] [db_path]")
        sys.exit(0)
    bdir = sys.argv[1]
    rem = sys.argv[2] if len(sys.argv) > 2 else None
    db = sys.argv[3] if len(sys.argv) > 3 else SecondBrain().db_path
    print(sync(db, bdir, remote=rem))
