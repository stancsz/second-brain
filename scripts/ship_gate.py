#!/usr/bin/env python3
"""Mochu ship gate — the mechanical conscience. Run before ANY merge/commit of product work.
Exit 0 only if: (1) no tracked verifier was modified/deleted since the Phase-3 baseline commit,
(2) no secret-shaped strings in the diff or untracked files, (3) full corpus green.
This exists so that rules which matter cannot be forgotten by the model running the loop.
Usage: python3 scripts/ship_gate.py [repo_root]"""
import os, re, subprocess, sys

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
# Force UTF-8 decoding for git output. On Windows the default child-process encoding
# is cp1252, but our diffs frequently contain CJK titles, emoji, and OKF frontmatter
# (sb_valid_from unicode) that cp1252 cannot decode — and that would crash the gate
# mid-read and exit with a stack trace instead of a real PASS/FAIL verdict.
def git(*a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
fails = []

# 1) verifier tamper check
bl_path = os.path.join(root, ".mochu", "VERIFIER_BASELINE")
if not os.path.exists(bl_path):
    fails.append("no .mochu/VERIFIER_BASELINE — Phase 3 must commit verifiers and write `git rev-parse HEAD` here")
else:
    baseline = open(bl_path).read().strip()
    r = git("diff", "--name-only", "--diff-filter=MD", baseline, "--", ".mochu/verifiers/")
    if r.returncode != 0:
        fails.append(f"baseline commit {baseline[:8]} not found")
    elif r.stdout.strip():
        fails.append("VERIFIERS TAMPERED since baseline: " + ", ".join(r.stdout.split()))

# 2) secrets scan (diff vs baseline-or-HEAD + untracked files)
PAT = re.compile(r"(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|xox[bporas]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY)")
diff_src = git("diff", "HEAD").stdout + git("diff", "--cached").stdout
hits = set(m.group(0)[:12] + "…" for m in PAT.finditer(diff_src))
unt = git("ls-files", "--others", "--exclude-standard").stdout.split()
for f in unt:
    p = os.path.join(root, f)
    try:
        if os.path.getsize(p) < 1_000_000:
            hits |= set(m.group(0)[:12] + "…" for m in PAT.finditer(open(p, errors="ignore").read()))
    except OSError: pass
if hits: fails.append("SECRET-SHAPED STRINGS in diff/untracked: " + ", ".join(sorted(hits)))

# 3) full corpus
r = subprocess.run([sys.executable, os.path.join(root, "scripts", "run_corpus.py"), root],
                   capture_output=True, text=True)
print(r.stdout, end="")
if r.returncode != 0: fails.append("corpus not green")

print("SHIP GATE: " + ("PASS" if not fails else "FAIL\n  - " + "\n  - ".join(fails)))
sys.exit(1 if fails else 0)