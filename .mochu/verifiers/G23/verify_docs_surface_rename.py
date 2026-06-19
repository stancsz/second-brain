#!/usr/bin/env python3
"""G23 verifier: R4/M3 docs surface rename — `drawer`/`drawers`/`Drawers` zero-residual
outside README+SKILL+CHANGELOG.

G14 (docs-okf) only checks README.md and SKILL.md. Per D001 (terminology-rename-before-phase-c),
the canonical model term is `Concept`; ANY residual `drawer` reference in the rest of the
docs surface (commands/, docs/, references/, README.zh.md) is a docs/code coherence gap
and an iteration that claims G23 must not ship while they remain.

Strongest-pattern check (per the docs dimension guidance):
  - Walk every git-tracked file under commands/, docs/, references/, plus README.zh.md.
  - Per file, scan with regex \\b(drawer|drawers|Drawers)\\b and assert zero matches.
  - EXEC a `git ls-files` so the test anchors against the actual tracked tree, not a
    free-form glob (a verifier that scans a stray untracked draft file would silently
    pass while a tracked file with a residual `drawer` is broken).
  - Report every hit with file:line:context so a future drift can be diagnosed in one
    read instead of searching.

Out of scope (intentional):
  - README.md and SKILL.md — covered by G14 (docs-okf) to avoid double-coverage and
    divergence between the two suites.
  - CHANGELOG.md — historical record of iterations that used the old name; rewriting
    past entries would be historical revisionism. G23 is about *current* docs surface.
  - .mochu/ — this skill's own state directory; not user-facing.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.path.abspath(os.path.dirname(__file__))).parent.parent.parent
PAT = re.compile(r"\b(drawer|drawers|Drawers)\b")

# Subdirs the docs surface lives in. Each entry: (dir_relpath, recursive).
# README.zh.md is a single root-level file (handled separately).
DIRS = [
    ("commands", True),
    ("docs", True),
    ("references", True),
]
ROOT_FILES = ["README.zh.md"]


def git(*args):
    r = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {args!r} failed: {r.stderr.strip()}")
    return r.stdout


def tracked_files() -> list:
    """All git-tracked .md files in scope.

    Windows git's pathspec doesn't expand `**/*.md` like POSIX shells do, so we
    list the directory contents via `git ls-files <dir>` and filter by extension
    in Python. The set is anchored to git-tracked files so a stray untracked
    draft cannot be used to make the verifier look green.
    """
    out = []
    for d, _ in DIRS:
        for f in git("ls-files", d).split():
            if f.endswith(".md"):
                out.append(f)
    for f in ROOT_FILES:
        # --error-unmatch makes git exit nonzero if the file is not tracked.
        r = subprocess.run(["git", "ls-files", "--error-unmatch", f],
                           cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode == 0:
            out.append(f)
    return sorted(set(out))


def scan(path: Path) -> list:
    """Return list of (line_no, line) hits for PAT in path."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in PAT.finditer(line):
            hits.append((i, m.group(0), line.strip()[:160]))
    return hits


def main() -> int:
    files = tracked_files()
    failures = []
    scanned = 0
    for rel in files:
        p = ROOT / rel
        scanned += 1
        hits = scan(p)
        for line_no, token, ctx in hits:
            failures.append(f"  {rel}:{line_no} [{token}] {ctx}")
    print(f"scanned {scanned} tracked files in commands/, docs/, references/, README.zh.md")
    if failures:
        print(f"[FAIL] {len(failures)} residual drawer reference(s):")
        for f in failures:
            print(f)
        return 1
    print("[PASS] (a) zero residual `drawer`/`drawers`/`Drawers` in commands/ docs/ references/ README.zh.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
