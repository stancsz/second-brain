#!/usr/bin/env python3
"""Mochu adequacy floor for a verifier suite. Run at end of Phase 3.5; must PASS before Phase 4.
Checks: (1) adequacy.md lists >=3 lazy artifacts, (2) suite contains at least one verifier that
EXECUTES something (subprocess/run/system/http/browser) or a frozen rubric — presence-only
suites (pure grep/exists/regex) are rejected, (3) folder is non-empty.
Usage: python3 scripts/audit_verifiers.py <gap-verifier-dir>"""
import os, re, sys

d = sys.argv[1] if len(sys.argv) > 1 else ""
fails = []
if not os.path.isdir(d): print(f"no such dir: {d}"); sys.exit(2)
adq = os.path.join(d, "adequacy.md")
if not os.path.exists(adq):
    fails.append("adequacy.md missing — write the three lazy artifacts that would pass a weak suite")
else:
    items = [l for l in open(adq) if re.match(r"\s*(\d+[.)]|[-*])\s+\S", l)]
    if len(items) < 3: fails.append(f"adequacy.md lists {len(items)} lazy artifacts; 3 required")
EXEC = re.compile(r"(subprocess|os\.system|\.run\(|check_call|check_output|popen|requests\.|urllib|http[s]?://|playwright|puppeteer|webdriver|curl |wget |npm |npx |pytest|node |python3? |bash |sh -c|docker |timeout \d)", re.I)
PRESENCE = re.compile(r"(grep|os\.path\.exists|re\.search|re\.match|findall|\.exists\(\)|test -f|test -e|\[ -f)", re.I)
files = [f for f in os.listdir(d) if f not in ("adequacy.md",) and os.path.isfile(os.path.join(d, f))]
if not files: fails.append("no verifier files in suite")
else:
    has_exec = any(EXEC.search(open(os.path.join(d, f), errors="ignore").read()) for f in files)
    has_rubric = any("rubric" in f.lower() for f in files)
    if not (has_exec or has_rubric):
        only_presence = any(PRESENCE.search(open(os.path.join(d, f), errors="ignore").read()) for f in files)
        fails.append("presence-only suite: " + ("greps/exists checks but " if only_presence else "") + "nothing is executed and no rubric file — if the claim is 'users can do X', the verifier must DO X")
print("AUDIT: " + ("PASS" if not fails else "FAIL\n  - " + "\n  - ".join(fails)))
sys.exit(1 if fails else 0)