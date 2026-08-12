"""Tests for the content-free five-host readiness matrix."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import host_matrix  # noqa: E402


class TestHostMatrix(unittest.TestCase):
    def test_all_named_hosts_are_package_ready_but_native_gate_is_explicit(self):
        report = host_matrix.build_report(ROOT)
        self.assertEqual({row["host"] for row in report["hosts"]}, set(host_matrix.HOSTS))
        self.assertTrue(all(row["status"] == "package-ready" for row in report["hosts"]))
        self.assertTrue(all(row["native_handshake"] == "manual" for row in report["hosts"]))
        self.assertNotIn("content", json.dumps(report).lower())

    def test_cli_json_is_machine_readable(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "host_matrix.py"), "--json", "--host", "opencode"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual([row["host"] for row in report["hosts"]], ["opencode"])
        self.assertEqual(report["hosts"][0]["status"], "package-ready")


if __name__ == "__main__":
    unittest.main()
