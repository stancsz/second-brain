#!/usr/bin/env python3
"""G22 verifier — secret-history scan + config-shape secret scan.

Strengthens R14 (\"no secrets ever committed\") beyond ship_gate.py's
diff-only secret scan by also checking:

  (a) the FULL git history (every commit) for secret-shaped strings
      (same PAT as ship_gate — AWS keys, GitHub PATs, OpenAI/Anthropic
      keys, Slack tokens, Google API keys, PEM private keys)
  (b) every tracked config file (*.toml, *.ini, *.yaml, *.yml) for
      inline `password = "..."` or `api_key/token/secret = "..."` with
      a non-trivial value — this is the sync.toml-secrets-via-env half
      of R14, asserting the rule (secrets are never inline in committed
      config; they live in env or OS keyring)

Exit 0 only if both scans come up empty. Exit 1 with details otherwise.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

SECRET_PAT = re.compile(
    r"(AKIA[0-9A-Z]{16}"
    r"|ghp_[A-Za-z0-9]{36}"
    r"|github_pat_[A-Za-z0-9_]{22,}"
    r"|xox[bporas]-[A-Za-z0-9-]{10,}"
    r"|sk-[A-Za-z0-9_-]{20,}"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY)"
)

# Config-shape secrets: `password = "literal"` or `api_key = "literal"` etc.
# The value must be at least 16 chars to avoid false-positives on placeholders
# like `password = ""` or `api_key = "CHANGEME"`. Test fixtures and
# docs that mention "password" or "token" in prose (comments, README) are
# not affected because the pattern requires `key = "value"` form.
CONFIG_SECRET_PAT = re.compile(
    r"""(?ix)               # case-insensitive, verbose
    (?:password|passwd|pwd
       |api[_-]?key
       |access[_-]?key
       |secret[_-]?key
       |auth[_-]?token
       |bearer[_-]?token
       |oauth[_-]?token
    )
    \s*[=:]\s*
    ["']?                    # optional quote
    ([^"'\s#]{16,})          # 16+ char value, no whitespace, no comment
    """,
)

CONFIG_EXTS = {".toml", ".ini", ".yaml", ".yml", ".env"}


def main() -> int:
    fails = []

    # (a) history scan
    r = subprocess.run(
        ["git", "log", "--all", "-p", "--no-color"],
        cwd=str(REPO), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    if r.returncode != 0:
        print("FAIL: git log -p failed:", r.stderr.strip()[:200])
        return 1
    hist_hits = sorted(set(SECRET_PAT.findall(r.stdout)))
    if hist_hits:
        for h in hist_hits:
            fails.append(f"history contains secret-shaped string: {h[:20]}…")

    # (b) config-shape secrets in tracked config files
    ls = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(REPO), capture_output=True, text=True, timeout=30,
    )
    if ls.returncode != 0:
        print("FAIL: git ls-files failed:", ls.stderr.strip()[:200])
        return 1
    config_files = [
        p for p in ls.stdout.split("\0")
        if p and Path(p).suffix in CONFIG_EXTS and Path(p).exists()
    ]
    for cf in config_files:
        text = Path(cf).read_text(encoding="utf-8", errors="replace")
        for m in CONFIG_SECRET_PAT.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            value = m.group(1)
            # Skip env-var references: the rule is "secrets via env/keyring,
            # never committed." A value like `${SECRET}` or `$ENV_VAR` is the
            # env-reference pattern we WANT, not a leak.
            if value.startswith("$") or value.startswith("{{"):
                continue
            fails.append(
                f"{cf}:{line_no}: inline secret in config "
                f"({m.group(0).split('=')[0].strip()} = {value[:8]}…)"
            )

    if fails:
        print("FAIL: R14 secret-history + config-shape checks:")
        for f in fails:
            print("  -", f)
        return 1
    print("PASS: R14 secret-history clean "
          f"({r.stdout.count(chr(10))} history lines scanned, "
          f"{len(config_files)} config files checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
