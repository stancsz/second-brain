#!/usr/bin/env python3
"""Mechanical gap selection for weak executors. Applies mochu's priority rules and prints
a ranked shortlist with reasons. The model's only remaining judgment: veto unverifiable picks.
Priority: open WIP chain > release-linked gaps > score desc; cooldown dims and closed gaps excluded.
Usage: python3 scripts/select_gap.py [repo_root]"""
import os, re, sys, glob

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
m = lambda *p: os.path.join(root, ".mochu", *p)

wips = sorted(glob.glob(m("wip", "*.md")))
if wips:
    w = os.path.splitext(os.path.basename(wips[0]))[0]
    cur = next((l.strip() for l in open(wips[0], encoding="utf-8") if l.lower().startswith("current")), "")
    print(f"{w} [WIP] resume open chain — {cur} (WIP preempts all new gaps)"); sys.exit(0)

cool = set()
if os.path.exists(m("cooldown.md")):
    for l in open(m("cooldown.md"), encoding="utf-8"):
        t = l.split("(")[0].strip().lower()
        if t and not t.startswith("#"): cool.add(t)

release = open(m("RELEASE.md"), encoding="utf-8").read().lower() if os.path.exists(m("RELEASE.md")) else ""
rows = []
for l in open(m("gaps.md"), encoding="utf-8"):
    if not l.strip().startswith("|") or "---" in l: continue
    c = [x.strip() for x in l.strip().strip("|").split("|")]
    if len(c) < 8 or c[0].lower() == "id" or "~~" in c[0] or "shipped" in c[0].lower(): continue
    try: score = float(c[7])
    except ValueError: continue
    dim = c[1].lower()
    rel = bool(re.search(r"- \[ \].*" + re.escape(c[0].lower()), release)) or c[0].lower() in release.replace("[x]", "")
    rows.append((c[0], dim, c[2], score, dim in cool, rel))

rows.sort(key=lambda r: (r[4], -r[5], -r[3]))  # eligible first, release-linked first, score desc
if not rows: print("no open gaps — run a recon iteration"); sys.exit(1)
for i, (gid, dim, desc, score, cooled, rel) in enumerate(rows[:5]):
    tag = "COOLDOWN-BLOCKED" if cooled else ("release-linked, " if rel else "") + f"score {score:g}"
    print(f"{gid} [{dim}] {desc} — {tag}" + ("  <- SELECT unless unverifiable" if i == 0 and not cooled else ""))
sys.exit(0)