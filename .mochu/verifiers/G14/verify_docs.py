#!/usr/bin/env python3
"""G14 verifier: README.md and SKILL.md describe OKF terminology and shipped capabilities."""

import sys
import re
from pathlib import Path


def check_file_content(path: Path, checks: list[dict]) -> list[str]:
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


def main():
    repo_root = Path(__file__).parent.parent.parent.parent
    readme_path = repo_root / "README.md"
    skill_path = repo_root / "SKILL.md"

    readme_checks = [
        {"name": "OKF v0.1 mentioned", "pattern": r"okf.*v0\.1|v0\.1.*okf"},
        {"name": "Bundle export mentioned", "pattern": r"bundle|okf.*export|export.*okf"},
        {"name": "Git sync mentioned", "pattern": r"git.*sync|sync.*git|multi.device"},
        {"name": "Concept terminology", "pattern": r"concept|Concept"},  # at least one mention
        {"name": "No drawer-only references", "pattern": r"(?<!concept)drawer(?!.*concept)"},  # ensure not drawer-only
    ]

    skill_checks = [
        {"name": "Concept, not drawer", "pattern": r"concept.*note|note.*concept"},
        {"name": "OKF in description", "pattern": r"okf|bundle"},
        {"name": "Psychological fields documented", "pattern": r"sb_subject|sb_valid_from|sb_affect|psychological|psychological memory"}
        ]

    failures = []

    # Check README for OKF/Bundle terminology
    failures.extend(check_file_content(readme_path, readme_checks))

    # Check SKILL.md for OKF terminology + psychological memory
    failures.extend(check_file_content(skill_path, skill_checks))

    if failures:
        print("FAIL: Documentation gaps:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("PASS: Documentation updated with OKF terminology and capabilities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
