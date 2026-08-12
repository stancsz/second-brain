import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bundle  # noqa: E402
import sync  # noqa: E402
import store  # noqa: E402
import storage  # noqa: E402
from brain import SecondBrain  # noqa: E402


class TestBundleSecretHygiene(unittest.TestCase):
    def test_bundle_gitignore_preserves_user_rules_and_blocks_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "bundle"
            repo.mkdir()
            (repo / ".gitignore").write_text("custom.tmp\n", encoding="utf-8")

            sync.ensure_repo(repo)
            sync.ensure_repo(repo)  # idempotence

            ignored = (repo / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("custom.tmp", ignored)
            self.assertEqual(ignored.count("secret.key"), 1)

            (repo / "secret.key").write_text("test-only-key-material", encoding="utf-8")
            (repo / "brain.db").write_bytes(b"not-a-real-db")
            (repo / "note.md").write_text("# safe", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            staged = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()

            self.assertIn(".gitignore", staged)
            self.assertIn("note.md", staged)
            self.assertNotIn("secret.key", staged)
            self.assertNotIn("brain.db", staged)

    def test_strict_encryption_refuses_before_bundle_repo_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "brain.db"
            bundle_dir = root / "bundle"
            brain = SecondBrain(db)
            brain.add("Private decision", "sensitive", tags=["private"])
            brain.close()

            with mock.patch.dict(
                os.environ, {"SECONDBRAIN_REQUIRE_ENCRYPTION": "1"}, clear=False
            ), mock.patch.object(bundle.crypto, "available", return_value=False):
                with self.assertRaisesRegex(
                    bundle.crypto.EncryptionUnavailable, "refused before touching git"
                ):
                    sync.sync(db, bundle_dir)

            self.assertFalse(bundle_dir.exists())

    def test_non_strict_sync_surfaces_plaintext_private_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "brain.db"
            bundle_dir = root / "bundle"
            brain = SecondBrain(db)
            brain.add("Private decision", "sensitive", tags=["private"])
            brain.close()

            with mock.patch.dict(os.environ, {}, clear=False), \
                    mock.patch.object(bundle.crypto, "available", return_value=False):
                os.environ.pop("SECONDBRAIN_REQUIRE_ENCRYPTION", None)
                result = sync.sync(db, bundle_dir)

            self.assertEqual(result["plaintext_private"], 1)

    def test_sync_pairs_rebuilt_database_and_next_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "brain.db"
            bundle_dir = root / "bundle"
            brain = SecondBrain(db)
            brain.add("Base", "local canonical fact")
            brain.close()

            result = sync.sync(db, bundle_dir)
            self.assertIn("bundle", result)
            reopened = store.open_brain(db, bundle_dir)
            try:
                self.assertEqual(["Base"], [row["title"] for row in reopened.list()])
            finally:
                reopened.close()

    def test_manual_bundle_edit_is_not_overwritten_by_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "brain.db"
            bundle_dir = root / "bundle"
            brain = SecondBrain(db)
            brain.add("Base", "original")
            brain.close()
            sync.sync(db, bundle_dir)
            note = bundle_dir / "base.md"
            edited = note.read_text(encoding="utf-8").replace("original", "external edit")
            note.write_text(edited, encoding="utf-8")

            with self.assertRaises(store.CanonicalStoreError):
                sync.sync(db, bundle_dir)
            self.assertIn("external edit", note.read_text(encoding="utf-8"))

    def test_interrupted_sync_rebuilds_bundle_without_exporting_stale_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "brain.db"
            bundle_dir = root / "bundle"
            brain = SecondBrain(db)
            brain.add("Base", "base")
            brain.close()
            sync.sync(db, bundle_dir)

            # Simulate a completed pull followed by process death: the Bundle
            # has a newer Concept while SQLite still has only the old one.
            incoming = bundle_dir / "remote.md"
            incoming.write_text(
                "---\ntype: Note\nsb_id: remote-id\ntitle: Remote\n---\n\nfrom remote\n",
                encoding="utf-8",
            )
            store.begin_sync(bundle_dir)
            with self.assertRaises(storage.BundleDirtyError):
                storage.create_snapshot(bundle_dir)

            sync.sync(db, bundle_dir)
            reopened = store.open_brain(db, bundle_dir)
            try:
                self.assertEqual({"Base", "Remote"}, {r["title"] for r in reopened.list()})
            finally:
                reopened.close()

    def test_open_recovers_sync_marker_from_bundle_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "brain.db"
            bundle_dir = root / "bundle"
            brain = SecondBrain(db)
            brain.add("Base", "base")
            brain.close()
            sync.sync(db, bundle_dir)
            store.begin_sync(bundle_dir)

            reopened = store.open_brain(db, bundle_dir)
            try:
                self.assertFalse((bundle_dir / store.SYNC_MARKER).exists())
                self.assertEqual(["Base"], [row["title"] for row in reopened.list()])
            finally:
                reopened.close()

    def test_sync_retries_bundle_authority_after_rebuild_failure(self):
        """A failed post-pull rebuild must not let the next retry export stale DB."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "brain.db"
            bundle_dir = root / "bundle"
            brain = SecondBrain(db)
            brain.add("Base", "base")
            brain.close()
            sync.sync(db, bundle_dir)

            (bundle_dir / "remote.md").write_text(
                "---\ntype: Note\nsb_id: remote-id\ntitle: Remote\n---\n\nfrom remote\n",
                encoding="utf-8",
            )
            # Model the journal written before a pull that has already changed
            # Markdown; the SQLite cache is intentionally still stale.
            store.begin_sync(bundle_dir)
            original_rebuild = bundle.rebuild
            with mock.patch.object(bundle, "rebuild", side_effect=RuntimeError("injected")):
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    sync.sync(db, bundle_dir)
            self.assertTrue((bundle_dir / store.SYNC_MARKER).exists())

            # The retry must consume the Bundle-authority journal first. If it
            # serialized the old SQLite cache, remote.md would disappear.
            with mock.patch.object(bundle, "rebuild", side_effect=original_rebuild):
                sync.sync(db, bundle_dir)
            reopened = store.open_brain(db, bundle_dir)
            try:
                self.assertEqual({"Base", "Remote"}, {r["title"] for r in reopened.list()})
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
