"""Content-free, read-only compatibility report tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import store  # noqa: E402
from brain import SecondBrain  # noqa: E402


class TestDoctor(unittest.TestCase):
    def run_doctor(self, db: Path, bundle: Path, *extra: str):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "brain_doctor.py"), "--db", str(db),
             "--bundle", str(bundle), "--json", *extra],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )

    def test_uninitialized_report_is_content_free_and_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_doctor(root / "brain.db", root / "vault")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual("warn", report["status"])
            self.assertEqual("pass", next(c for c in report["checks"] if c["id"] == "mcp_protocol")["status"])
            self.assertNotIn("content", result.stdout.lower())

    def test_paired_report_uses_read_only_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db, vault = root / "brain.db", root / "vault"
            brain = SecondBrain(db)
            store.replace_canonical(brain, vault)
            brain.add("Doctor canary", "private content must not be reported")
            brain.close()

            # The report must detect the intentional DB-ahead state without
            # exporting it or exposing the note text.
            result = self.run_doctor(db, vault)
            self.assertEqual(2, result.returncode)
            report = json.loads(result.stdout)
            self.assertEqual("fail", report["status"])
            self.assertEqual("fail", next(c for c in report["checks"] if c["id"] == "pairing")["status"])
            self.assertNotIn("Doctor canary", result.stdout)
            self.assertNotIn("private content", result.stdout)

    def test_paired_report_passes_after_canonical_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db, vault = root / "brain.db", root / "vault"
            brain = SecondBrain(db)
            store.replace_canonical(brain, vault)
            with store.canonical_mutation(brain, vault):
                brain.add("Healthy canary", "paired")
            brain.close()
            before_db_mtime = db.stat().st_mtime_ns
            before_files = sorted(
                path.relative_to(vault).as_posix() for path in vault.rglob("*") if path.is_file()
            )
            lock_path = vault.parent / (vault.name + ".lock")
            before_lock = (lock_path.exists(), lock_path.stat().st_mtime_ns if lock_path.exists() else None)

            result = self.run_doctor(db, vault)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual("pass", report["status"])
            self.assertEqual("pass", next(c for c in report["checks"] if c["id"] == "pairing")["status"])
            self.assertEqual(before_db_mtime, db.stat().st_mtime_ns)
            self.assertEqual(before_files, sorted(
                path.relative_to(vault).as_posix() for path in vault.rglob("*") if path.is_file()
            ))
            after_lock = (lock_path.exists(), lock_path.stat().st_mtime_ns if lock_path.exists() else None)
            self.assertEqual(before_lock, after_lock)

    def test_strict_mode_turns_uninitialized_warning_into_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_doctor(root / "brain.db", root / "vault", "--strict")
            self.assertEqual(1, result.returncode)


if __name__ == "__main__":
    unittest.main()
