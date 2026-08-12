#!/usr/bin/env python3
"""Black-box guarantees that CLI/MCP writes reach the canonical OKF Bundle."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CLI = SCRIPTS / "brain_cli.py"
MCP = SCRIPTS / "brain_mcp.py"
sys.path.insert(0, str(SCRIPTS))

import bundle  # noqa: E402
import store  # noqa: E402
import storage  # noqa: E402
from brain import SecondBrain  # noqa: E402
from store import resolve_bundle_path  # noqa: E402


class CanonicalStoreCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "USERPROFILE": str(self.home),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
            }
        )

    def cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *arguments],
            cwd=ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )

    def rebuild(self, source: Path, destination: Path) -> SecondBrain:
        brain = bundle.rebuild(source, destination)
        self.addCleanup(brain.close)
        return brain


class TestCanonicalCli(CanonicalStoreCase):
    def test_default_add_is_rebuildable_from_default_bundle(self):
        result = self.cli(
            "--json",
            "add",
            "Canonical canary",
            "bundle-survival-canary",
            "--collection",
            "Tests",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        added = json.loads(result.stdout)

        canonical = self.home / ".secondbrain" / "okf"
        self.assertTrue((canonical / "Tests" / "canonical-canary.md").is_file())
        rebuilt = self.rebuild(canonical, self.root / "rebuilt.db")
        restored = rebuilt.get(added["id"])
        self.assertIsNotNone(restored)
        self.assertEqual("bundle-survival-canary", restored["content"])

    def test_update_delete_restore_and_relation_flush_to_bundle(self):
        first = json.loads(
            self.cli("--json", "add", "First", "old value").stdout
        )
        second = json.loads(
            self.cli("--json", "add", "Second", "target").stdout
        )
        self.assertEqual(
            self.cli("update", first["id"], "--content", "new value").returncode,
            0,
        )
        self.assertEqual(
            self.cli(
                "relate", first["id"], second["id"], "--type", "expands"
            ).returncode,
            0,
        )
        self.assertEqual(self.cli("delete", second["id"]).returncode, 0)

        canonical = self.home / ".secondbrain" / "okf"
        rebuilt_deleted = self.rebuild(canonical, self.root / "deleted.db")
        self.assertEqual("new value", rebuilt_deleted.get(first["id"])["content"])
        self.assertIsNone(rebuilt_deleted.get(second["id"]))
        relation_rows = rebuilt_deleted.con.execute(
            "SELECT relation_type FROM relations WHERE from_id=? AND to_id=?",
            (first["id"], second["id"]),
        ).fetchall()
        self.assertEqual(["expands"], [row["relation_type"] for row in relation_rows])
        rebuilt_deleted.close()

        self.assertEqual(self.cli("restore", second["id"]).returncode, 0)
        rebuilt_restored = self.rebuild(canonical, self.root / "restored.db")
        self.assertIsNotNone(rebuilt_restored.get(second["id"]))

    def test_custom_db_uses_isolated_sibling_bundle(self):
        custom_db = self.root / "profiles" / "client-a.db"
        result = self.cli(
            "--db",
            str(custom_db),
            "--json",
            "add",
            "Client decision",
            "isolated",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sibling_bundle = Path(str(custom_db) + ".okf")
        self.assertEqual(sibling_bundle, resolve_bundle_path(custom_db))
        self.assertTrue((sibling_bundle / "client-decision.md").is_file())
        self.assertFalse((self.home / ".secondbrain" / "okf").exists())

    def test_explicit_bundle_override_is_honored(self):
        custom_db = self.root / "brain.db"
        custom_bundle = self.root / "vault"
        result = self.cli(
            "--db",
            str(custom_db),
            "--bundle",
            str(custom_bundle),
            "add",
            "Override",
            "explicit vault",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((custom_bundle / "override.md").is_file())
        self.assertFalse(Path(str(custom_db) + ".okf").exists())

    def test_export_failure_rolls_back_database_and_restores_clean_bundle(self):
        database = self.root / "failure.db"
        canonical = self.root / "failure-vault"
        brain = SecondBrain(database)
        self.addCleanup(brain.close)
        store.replace_canonical(brain, canonical)

        real_export = bundle.export
        calls = 0

        def fail_once(active_brain, destination):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("synthetic export failure")
            return real_export(active_brain, destination)

        with mock.patch.object(bundle, "export", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "synthetic export failure"):
                with store.canonical_mutation(brain, canonical):
                    brain.add("Must roll back", "not durable")

        self.assertEqual([], brain.search("durable"))
        self.assertFalse((canonical / store.DIRTY_MARKER).exists())
        rebuilt = self.rebuild(canonical, self.root / "failure-rebuilt.db")
        self.assertEqual([], rebuilt.search("durable"))

    def test_external_bundle_change_during_export_is_not_blessed(self):
        database = self.root / "race.db"
        canonical = self.root / "race-vault"
        brain = SecondBrain(database)
        self.addCleanup(brain.close)
        with store.canonical_mutation(brain, canonical):
            brain.add("Stable", "before")

        real_export = bundle.export

        def export_then_external_edit(active_brain, destination):
            result = real_export(active_brain, destination)
            note = Path(destination) / "stable.md"
            note.write_text(
                note.read_text(encoding="utf-8").replace("before", "outside"),
                encoding="utf-8",
            )
            return result

        with mock.patch.object(bundle, "export", side_effect=export_then_external_edit):
            with self.assertRaises(store.BundlePairMismatch):
                with store.canonical_mutation(brain, canonical):
                    brain.add("New", "must not bless a mixed generation")

        self.assertIn("outside", (canonical / "stable.md").read_text(encoding="utf-8"))
        self.assertTrue((canonical / store.DIRTY_MARKER).exists())

    def test_dirty_marker_blocks_snapshot_until_recovery(self):
        database = self.root / "dirty.db"
        canonical = self.root / "dirty-vault"
        brain = SecondBrain(database)
        self.addCleanup(brain.close)
        brain.add("Committed", "recoverable canary")
        canonical.mkdir()
        (canonical / store.DIRTY_MARKER).write_text("interrupted\n", encoding="utf-8")

        with self.assertRaises(storage.BundleDirtyError):
            storage.create_snapshot(canonical)

        self.assertTrue(store.recover_if_dirty(brain, canonical))
        snapshot = storage.create_snapshot(canonical)
        self.assertTrue(snapshot.snapshot_id)
        self.assertFalse((canonical / store.DIRTY_MARKER).exists())

    def test_missing_database_rebuilds_from_canonical_bundle(self):
        database = self.root / "wipe.db"
        canonical = self.root / "wipe-vault"
        first = SecondBrain(database)
        with store.canonical_mutation(first, canonical):
            saved = first.add("Survives wipe", "bundle-first recovery")
        first.close()
        database.unlink()

        reopened = store.open_brain(database, canonical)
        self.addCleanup(reopened.close)
        self.assertEqual("bundle-first recovery", reopened.get(saved["id"])["content"])

    def test_distinct_custom_database_suffixes_get_distinct_bundles(self):
        first = self.root / "profile.db"
        second = self.root / "profile.sqlite"
        self.assertNotEqual(resolve_bundle_path(first), resolve_bundle_path(second))

    def test_existing_unpaired_database_and_bundle_refuse_to_guess(self):
        database = self.root / "ambiguous.db"
        canonical = self.root / "ambiguous-vault"
        brain = SecondBrain(database)
        brain.add("Database fact", "database")
        brain.close()
        other = SecondBrain(self.root / "other.db")
        other.add("Bundle fact", "bundle")
        bundle.export(other, canonical)
        other.close()

        with self.assertRaisesRegex(store.CanonicalStoreError, "refusing to guess"):
            store.open_brain(database, canonical)

    def test_paired_database_drift_refuses_to_overwrite_bundle(self):
        database = self.root / "drift.db"
        canonical = self.root / "drift-vault"
        brain = SecondBrain(database)
        with store.canonical_mutation(brain, canonical):
            brain.add("Paired", "first")
        brain.add("Bypassed coordinator", "second")
        brain.close()

        with self.assertRaisesRegex(store.CanonicalStoreError, "out of sync"):
            store.open_brain(database, canonical)

    def test_manual_bundle_edit_is_detected_before_open(self):
        database = self.root / "edited.db"
        canonical = self.root / "edited-vault"
        brain = SecondBrain(database)
        with store.canonical_mutation(brain, canonical):
            brain.add("Original", "before")
        brain.close()
        note = canonical / "original.md"
        note.write_text(note.read_text(encoding="utf-8").replace("before", "after"), encoding="utf-8")

        with self.assertRaisesRegex(store.CanonicalStoreError, "out of sync"):
            store.open_brain(database, canonical)

    def test_unknown_pair_state_schema_is_refused(self):
        database = self.root / "schema.db"
        canonical = self.root / "schema-vault"
        brain = SecondBrain(database)
        with store.canonical_mutation(brain, canonical):
            brain.add("Original", "value")
        brain.close()
        (canonical / store.PAIR_STATE).write_text(
            '{"format":"future-v99","database":{},"bundle_state_sha256":"x"}\n',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(store.CanonicalStoreError, "pair-state"):
            store.open_brain(database, canonical)

    def test_strict_encryption_failure_leaves_neither_database_nor_bundle_ahead(self):
        database = self.root / "strict.db"
        canonical = self.root / "strict-vault"
        brain = SecondBrain(database)
        self.addCleanup(brain.close)
        store.replace_canonical(brain, canonical)

        with mock.patch.dict(
            os.environ, {"SECONDBRAIN_REQUIRE_ENCRYPTION": "1"}, clear=False
        ), mock.patch.object(bundle.crypto, "available", return_value=False):
            with self.assertRaises(bundle.crypto.EncryptionUnavailable):
                with store.canonical_mutation(brain, canonical):
                    brain.add("Private", "must not persist", tags=["private"])

        self.assertEqual(0, brain.stats()["concepts"])
        self.assertFalse((canonical / store.DIRTY_MARKER).exists())
        rebuilt = self.rebuild(canonical, self.root / "strict-rebuilt.db")
        self.assertEqual(0, rebuilt.stats()["concepts"])


class TestCanonicalMcp(CanonicalStoreCase):
    def test_mcp_add_is_rebuildable_from_bundle(self):
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "brain_add",
                    "arguments": {
                        "title": "MCP canonical canary",
                        "content": "mcp-bundle-survival",
                    },
                },
            },
        ]
        result = subprocess.run(
            [sys.executable, str(MCP)],
            input="".join(json.dumps(item) + "\n" for item in requests),
            cwd=ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        responses = {item["id"]: item for item in map(json.loads, result.stdout.splitlines())}
        added = json.loads(responses[2]["result"]["content"][0]["text"])

        rebuilt = self.rebuild(
            self.home / ".secondbrain" / "okf", self.root / "mcp-rebuilt.db"
        )
        self.assertEqual("mcp-bundle-survival", rebuilt.get(added["id"])["content"])


if __name__ == "__main__":
    unittest.main()
