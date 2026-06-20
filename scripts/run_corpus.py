#!/usr/bin/env python3
"""Mochu corpus runner: executes every verifier in .mochu/verifiers/REGISTRY.md.
Exit 0 only if all green. Takes an exclusive lock on .mochu/LOCK so parallel
loop instances cannot corrupt state. Usage: python3 scripts/run_corpus.py [repo_root]"""
import os, re, subprocess, sys, time

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
reg = os.path.join(root, ".mochu", "verifiers", "REGISTRY.md")
lock = os.path.join(root, ".mochu", "LOCK")
if not os.path.exists(reg):
    print(f"no registry at {reg}"); sys.exit(2)

# exclusive lock (atomic create); stale if older than 2h
try:
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode()); os.close(fd)
except FileExistsError:
    if time.time() - os.path.getmtime(lock) > 7200:
        print(f"stale lock (>2h) at {lock} — removing"); os.remove(lock)
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
    else:
        print(f"another mochu instance holds the lock at {lock} — refusing to run"); sys.exit(3)

red = []
try:
    rows = [l for l in open(reg) if l.strip().startswith("|") and "---" not in l]
    entries = []
    for l in rows:  # header identified by content, never by position
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) >= 4 and c[0] and c[0].lower() != "id":
            entries.append((c[0], c[3].strip("`")))
    if not entries:
        print("registry has no entries"); sys.exit(2)
    for vid, cmd in entries:
        t = time.time()
        r = subprocess.run(cmd, shell=True, cwd=root, capture_output=True, text=True, timeout=900)
        status = "GREEN" if r.returncode == 0 else "RED"
        print(f"[{status}] {vid} ({time.time()-t:.1f}s)")
        if r.returncode != 0:
            red.append(vid)
            tail = (r.stdout + r.stderr).strip().splitlines()[-5:]
            for ln in tail: print(f"    {ln}")
    print(f"corpus: {len(entries)-len(red)}/{len(entries)} green" + (f" — RED: {', '.join(red)}" if red else ""))
finally:
    if os.path.exists(lock): os.remove(lock)
sys.exit(1 if red else 0)