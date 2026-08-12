#!/usr/bin/env python3
"""Run the repository's public compile and test corpus.

The historical private ``.mochu`` registry is intentionally not required. This
runner is deterministic from a clean public clone and is used by ship_gate.py.

Usage: python scripts/run_corpus.py [repo_root]
"""

from __future__ import annotations

import os
from pathlib import Path
import py_compile
import subprocess
import sys
import time


ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

# Windows PowerShell commonly starts Python with a cp1252 console. The test
# corpus contains valid Unicode diagnostics, so the gate itself must not fail
# while printing a green test result.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def compile_python() -> bool:
    started = time.monotonic()
    paths = sorted(
        path
        for directory in ("scripts", "hooks", "tests")
        for path in (ROOT / directory).rglob("*.py")
    )
    failures: list[str] = []
    for path in paths:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{path.relative_to(ROOT)}: {exc.msg}")

    status = "GREEN" if not failures else "RED"
    print(f"[{status}] compile ({len(paths)} files, {time.monotonic() - started:.1f}s)")
    for failure in failures:
        print(f"    {failure}")
    return not failures


def run_tests() -> bool:
    started = time.monotonic()
    environment = os.environ.copy()
    environment.setdefault("PYTHONUTF8", "1")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    status = "GREEN" if result.returncode == 0 else "RED"
    print(f"[{status}] tests ({time.monotonic() - started:.1f}s)")
    return result.returncode == 0


def main() -> int:
    if not (ROOT / "scripts").is_dir() or not (ROOT / "tests").is_dir():
        print(f"invalid repository root: {ROOT}", file=sys.stderr)
        return 2

    checks = [compile_python(), run_tests()]
    passed = sum(checks)
    print(f"corpus: {passed}/{len(checks)} green")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
