#!/usr/bin/env python3
"""Public pre-commit/release gate for second-brain.

Exit zero only when the Agent Skill validates, no secret-shaped value appears in
the current diff or untracked files, and the public compile/test corpus passes.

Usage: python scripts/ship_gate.py [repo_root]
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SECRET_PATTERN = re.compile(
    r"(AKIA[0-9A-Z]{16}"
    r"|ghp_[A-Za-z0-9]{36}"
    r"|github_pat_[A-Za-z0-9_]{22,}"
    r"|xox[bporas]-[A-Za-z0-9-]{10,}"
    r"|sk-[A-Za-z0-9_-]{20,}"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY)"
)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.setdefault("PYTHONUTF8", "1")
    return subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *arguments], capture=True)


def secret_scan() -> list[str]:
    candidates: list[tuple[str, str]] = []
    diff = git("diff", "HEAD", "--no-ext-diff", "--unified=0")
    if diff.returncode != 0:
        return ["could not read the git diff for the secret scan"]
    candidates.append(("git diff", diff.stdout))

    untracked = git("ls-files", "--others", "--exclude-standard", "-z")
    if untracked.returncode != 0:
        return ["could not enumerate untracked files for the secret scan"]

    for relative in filter(None, untracked.stdout.split("\0")):
        path = (ROOT / relative).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError:
            return [f"untracked path escapes the repository: {relative}"]
        try:
            if path.is_file() and path.stat().st_size <= 1_000_000:
                candidates.append((relative, path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue

    findings: list[str] = []
    for source, text in candidates:
        for match in SECRET_PATTERN.finditer(text):
            redacted = match.group(0)[:6] + "..."
            findings.append(f"{source}: {redacted}")
    return sorted(set(findings))


def main() -> int:
    if not (ROOT / ".git").exists():
        print(f"SHIP GATE: FAIL\n  - not a git repository: {ROOT}")
        return 2

    failures: list[str] = []

    validator = run([sys.executable, "scripts/validate_skill.py", "."])
    if validator.returncode != 0:
        failures.append("Agent Skill validation failed")
    elif validator.stdout:
        print(validator.stdout, end="" if validator.stdout.endswith("\n") else "\n")

    secrets = secret_scan()
    if secrets:
        failures.append("secret-shaped values found: " + ", ".join(secrets))

    corpus = run([sys.executable, "scripts/run_corpus.py", str(ROOT)])
    if corpus.stdout:
        print(corpus.stdout, end="" if corpus.stdout.endswith("\n") else "\n")
    if corpus.returncode != 0:
        failures.append("public compile/test corpus is not green")

    if failures:
        print("SHIP GATE: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("SHIP GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
