#!/usr/bin/env python3
"""G14 verifier: README.md and SKILL.md describe OKF terminology and shipped capabilities.

Strongest-pattern check (per D001 + mochu skill's docs dimension guidance):
  - README/SKILL must mention OKF v0.1, Bundle export, git sync, Concept.
  - SKILL.md must document the psychological fields (sb_subject/sb_valid_from/sb_affect).
  - README/SKILL must contain ZERO residual `drawer`/`drawers`/`Drawers` references
    (D001 coherence rule: docs and code use `Concept`; any drawer hit = coherence gap
    that G14 must close, since T002 only renames code, not docs).
  - EXEC: docs claim `python3 scripts/brain_cli.py stats` runs out-of-the-box with
    zero pip install — we EXECUTE that command in a clean subprocess and assert the
    brain.db file is created. Proves the docs' headline claim (zero dependencies,
    one file, runs immediately) is true, not just textually asserted.
"""
import os
import re
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path


def check_file_content(path: Path, checks: list) -> list:
    """Run a list of regex checks against file content. Returns list of failures."""
    if not path.exists():
        return [f"File not found: {path}"]

    text = path.read_text(encoding="utf-8")
    failures = []
    for check in checks:
        pattern = check["pattern"]
        name = check["name"]
        if not re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            failures.append(f"{name}: pattern not found in {path.name}")
    return failures


def _scan_drawers(text: str) -> list:
    """Return list of offending drawer mentions with their line numbers.

    Used by both README and SKILL.md. Per D001 the canonical model term is
    `Concept`; any `drawer`/`drawers`/`Drawers` in user-facing docs is a docs/
    code coherence gap and the iteration that claims G14 must not ship while
    they remain."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in re.finditer(r"\b(drawer|drawers|Drawers)\b", line):
            hits.append(f"L{i}: {m.group(0)} -> {line.strip()[:120]}")
    return hits


def _check_zero_dependency_install(repo_root: Path) -> list:
    """EXEC: prove the docs' zero-dependency claim by running `brain_cli.py stats`
    in a clean subprocess and asserting the SQLite brain.db is created. This is
    the operational half of the docs claim — without this, a future refactor that
    silently added an import-time dependency would still pass the content checks."""
    failures = []
    tmp = Path(tempfile.mkdtemp(prefix="g14-brainci-"))
    try:
        target_db = tmp / "brain.db"
        cli = repo_root / "scripts" / "brain_cli.py"
        if not cli.exists():
            return [f"EXEC: {cli} not found — docs claim a CLI but it is missing"]
        r = subprocess.run([sys.executable, str(cli), "--db", str(target_db), "stats"],
                           cwd=str(repo_root),
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            failures.append(
                f"EXEC: `python brain_cli.py --db <tmp> stats` exited {r.returncode}; "
                f"docs claim zero-dependency install. stderr={r.stderr.strip()[:200]}"
            )
        elif not target_db.exists():
            failures.append(
                f"EXEC: `python brain_cli.py --db <tmp> stats` exited 0 but did NOT create "
                f"{target_db} — docs claim `first run creates ~/.secondbrain/brain.db`"
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return failures


def main():
    repo_root = Path(__file__).parent.parent.parent.parent
    readme_path = repo_root / "README.md"
    skill_path = repo_root / "SKILL.md"

    readme_checks = [
        {"name": "OKF v0.1 mentioned", "pattern": r"okf.*v0\.1|v0\.1.*okf"},
        {"name": "Bundle export mentioned", "pattern": r"bundle|okf.*export|export.*okf"},
        {"name": "Git sync mentioned", "pattern": r"git.*sync|sync.*git|multi.device"},
        {"name": "Concept terminology", "pattern": r"\b[Cc]oncept\b"},  # at least one mention
    ]
    skill_checks = [
        {"name": "Concept, not drawer", "pattern": r"\b[Cc]oncept\b"},
        {"name": "OKF in description", "pattern": r"okf|bundle"},
        {"name": "Psychological fields documented",
         "pattern": r"sb_subject|sb_valid_from|sb_affect|psychological|psychological memory"},
    ]

    failures = []

    # README: OKF/Bundle terminology + ZERO residual drawer mentions.
    failures.extend(check_file_content(readme_path, readme_checks))
    drawer_hits = _scan_drawers(readme_path.read_text(encoding="utf-8"))
    if drawer_hits:
        failures.append("README.md still references drawer/drawers (must be Concept per D001): "
                        + "; ".join(drawer_hits))

    # SKILL.md: OKF terminology + psychological memory + ZERO residual drawer mentions.
    failures.extend(check_file_content(skill_path, skill_checks))
    drawer_hits_skill = _scan_drawers(skill_path.read_text(encoding="utf-8"))
    if drawer_hits_skill:
        failures.append("SKILL.md still references drawer/drawers (must be Concept per D001): "
                        + "; ".join(drawer_hits_skill))

    # EXEC: prove the docs' install claim operationally.
    failures.extend(_check_zero_dependency_install(repo_root))

    if failures:
        print("FAIL: Documentation gaps:")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS: Documentation updated with OKF terminology and capabilities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
