"""Focused tests for deterministic, verified OKF Bundle snapshots."""
import base64
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import storage  # noqa: E402
import storage_cli  # noqa: E402
import store  # noqa: E402


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_bundle(self, name="bundle"):
        bundle = self.root / name
        (bundle / "Work").mkdir(parents=True)
        (bundle / "index.md").write_text(
            '---\nokf_version: "0.1"\n---\n\n# Brain\n', encoding="utf-8"
        )
        (bundle / "Work" / "decision.md").write_text(
            "---\ntype: Note\ntitle: Decision\n---\n\nUse files as truth.\n",
            encoding="utf-8",
        )
        (bundle / "Work" / "中文.md").write_text(
            "---\ntype: Note\ntitle: 中文\n---\n\n可移植。\n", encoding="utf-8"
        )
        return bundle


class TestSnapshots(StorageTestCase):
    def test_snapshot_is_deterministic_and_git_metadata_is_excluded(self):
        bundle = self.make_bundle()
        (bundle / ".git").mkdir()
        (bundle / ".git" / "config").write_text("secret-ish remote metadata", encoding="utf-8")

        first = storage.create_snapshot(bundle)
        # Filesystem metadata is deliberately not part of a content snapshot.
        for path in bundle.rglob("*.md"):
            changed = path.stat().st_mtime + 60
            os.utime(path, (changed, changed))
        second = storage.create_snapshot(bundle)

        self.assertEqual(first.archive, second.archive)
        self.assertEqual(first.manifest.to_bytes(), second.manifest.to_bytes())
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertNotIn(".git/config", [entry.path for entry in first.manifest.files])
        storage.verify_snapshot(first)

    def test_corrupt_archive_is_rejected(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        damaged = bytearray(snapshot.archive)
        damaged[0] ^= 0xFF
        with self.assertRaises(storage.SnapshotIntegrityError):
            storage.verify_snapshot(storage.Snapshot(bytes(damaged), snapshot.manifest))

    def test_dirty_bundle_is_refused_and_pair_state_is_snapshotted(self):
        bundle = self.make_bundle()
        (bundle / store.DIRTY_MARKER).write_text("interrupted\n", encoding="utf-8")
        with self.assertRaises(storage.BundleDirtyError):
            storage.create_snapshot(bundle)

        (bundle / store.DIRTY_MARKER).unlink()
        (bundle / store.PAIR_STATE).write_text('{"concept_count":2}\n', encoding="utf-8")
        snapshot = storage.create_snapshot(bundle)
        self.assertIn(store.PAIR_STATE, [entry.path for entry in snapshot.manifest.files])

    def test_interrupted_sync_bundle_is_refused_until_recovery(self):
        bundle = self.make_bundle("sync-bundle")
        store.begin_sync(bundle)
        with self.assertRaises(storage.BundleDirtyError):
            storage.create_snapshot(bundle)

    def test_snapshot_and_writer_share_the_same_bundle_lock(self):
        bundle = self.make_bundle()
        with store.bundle_lock(bundle):
            # Reentrant in-process use is required because storage takes the
            # same cross-process lock for the complete capture.
            snapshot = storage.create_snapshot(bundle)
        self.assertTrue(snapshot.snapshot_id)

    def test_traversal_member_is_rejected_even_with_matching_archive_hash(self):
        payload = b"escape"
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:", format=tarfile.PAX_FORMAT) as tar:
            info = tarfile.TarInfo("../outside.md")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        archive = stream.getvalue()
        manifest = storage.Manifest(
            archive_sha256=hashlib.sha256(archive).hexdigest(),
            archive_size=len(archive),
            files=(
                storage.ManifestEntry(
                    "safe.md", len(payload), hashlib.sha256(payload).hexdigest()
                ),
            ),
        )
        with self.assertRaises(storage.UnsafeArchiveError):
            storage.verify_snapshot(storage.Snapshot(archive, manifest))
        self.assertFalse((self.root / "outside.md").exists())

    def test_link_member_is_rejected(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:") as tar:
            info = tarfile.TarInfo("safe.md")
            info.type = tarfile.SYMTYPE
            info.linkname = "../outside.md"
            tar.addfile(info)
        archive = stream.getvalue()
        manifest = storage.Manifest(
            archive_sha256=hashlib.sha256(archive).hexdigest(),
            archive_size=len(archive),
            files=(
                storage.ManifestEntry(
                    "safe.md", 0, hashlib.sha256(b"").hexdigest()
                ),
            ),
        )
        with self.assertRaises(storage.UnsafeArchiveError):
            storage.verify_snapshot(storage.Snapshot(archive, manifest))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_bundle_symlink_is_rejected_when_platform_allows_creation(self):
        bundle = self.make_bundle()
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = bundle / "linked.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("current account cannot create symlinks")
        with self.assertRaises(storage.StorageError):
            storage.create_snapshot(bundle)


class TestLocalBackend(StorageTestCase):
    def test_round_trip_and_idempotent_push(self):
        bundle = self.make_bundle()
        snapshot = storage.create_snapshot(bundle)
        backend = storage.LocalBackend(self.root / "store")

        first = backend.push(snapshot)
        second = backend.push(snapshot)

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual([snapshot.snapshot_id], [entry.snapshot_id for entry in backend.list()])
        pulled = backend.pull(snapshot.snapshot_id)
        restored = self.root / "restored"
        result = storage.restore_snapshot(pulled, restored)
        self.assertIsNone(result.backup)
        for entry in snapshot.manifest.files:
            self.assertEqual(
                (bundle / Path(entry.path)).read_bytes(),
                (restored / Path(entry.path)).read_bytes(),
            )

    def test_corrupt_local_object_is_rejected_on_pull_and_list(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        store = self.root / "store"
        backend = storage.LocalBackend(store)
        backend.push(snapshot)
        archive_path = store / f"{snapshot.snapshot_id}.tar"
        archive_path.write_bytes(archive_path.read_bytes()[:-1] + b"X")

        with self.assertRaises(storage.SnapshotIntegrityError):
            backend.pull(snapshot.snapshot_id)
        with self.assertRaises(storage.SnapshotIntegrityError):
            backend.list()

    def test_archive_without_manifest_is_rejected_on_list(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        store = self.root / "store"
        store.mkdir()
        (store / f"{snapshot.snapshot_id}.tar").write_bytes(snapshot.archive)
        with self.assertRaisesRegex(storage.SnapshotIntegrityError, "no manifest"):
            storage.LocalBackend(store).list()

    def test_pull_without_id_selects_latest_complete_snapshot(self):
        backend = storage.LocalBackend(self.root / "store")
        first_bundle = self.make_bundle("first")
        first = storage.create_snapshot(first_bundle)
        backend.push(first)
        second_bundle = self.make_bundle("second")
        (second_bundle / "new.md").write_text("---\ntype: Note\n---\nnew\n", encoding="utf-8")
        second = storage.create_snapshot(second_bundle)
        backend.push(second)
        manifest = self.root / "store" / f"{second.snapshot_id}.manifest.json"
        newer = manifest.stat().st_mtime + 10
        os.utime(manifest, (newer, newer))
        self.assertEqual(second.snapshot_id, backend.pull().snapshot_id)


class FakeRcloneBackend(storage.RcloneBackend):
    """Deterministic in-memory rclone transport for adapter contract tests."""

    def __init__(self, objects=None):
        super().__init__("fake:secondbrain")
        self.objects = dict(objects or {})

    def _run(self, args):
        if args[0] == "lsjson":
            return json.dumps(
                [{"Path": name, "ModTime": "2026-08-12T00:00:00Z"} for name in self.objects]
            ).encode("utf-8")
        if args[0] == "cat":
            name = args[-1].rsplit("/", 1)[-1]
            try:
                return self.objects[name]
            except KeyError as exc:
                raise storage.BackendError(f"missing fake object {name}") from exc
        raise AssertionError(f"unexpected fake rclone operation: {args[0]}")


class TestRcloneBackendContract(StorageTestCase):
    def objects_for(self, snapshot):
        return {
            f"{snapshot.snapshot_id}.manifest.json": snapshot.manifest.to_bytes(),
            f"{snapshot.snapshot_id}.tar": snapshot.archive,
        }

    def test_round_trip_list_and_pull(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        backend = FakeRcloneBackend(self.objects_for(snapshot))
        self.assertEqual([snapshot.snapshot_id], [e.snapshot_id for e in backend.list()])
        pulled = backend.pull(snapshot.snapshot_id)
        self.assertEqual(snapshot.snapshot_id, pulled.snapshot_id)
        storage.verify_snapshot(pulled)

    def test_list_refuses_manifest_without_archive(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        backend = FakeRcloneBackend(
            {f"{snapshot.snapshot_id}.manifest.json": snapshot.manifest.to_bytes()}
        )
        with self.assertRaises(storage.SnapshotIntegrityError):
            backend.list()

    def test_list_refuses_archive_without_manifest(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        backend = FakeRcloneBackend({f"{snapshot.snapshot_id}.tar": snapshot.archive})
        with self.assertRaisesRegex(storage.SnapshotIntegrityError, "no manifest"):
            backend.list()

    def test_list_refuses_manifest_id_mismatch(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        other = storage.create_snapshot(self.make_bundle("other"))
        (self.root / "other" / "Work" / "decision.md").write_text(
            "---\ntype: Note\ntitle: Other\n---\n\nDifferent bytes.\n",
            encoding="utf-8",
        )
        other = storage.create_snapshot(self.root / "other")
        backend = FakeRcloneBackend(
            {
                f"{snapshot.snapshot_id}.manifest.json": other.manifest.to_bytes(),
                f"{snapshot.snapshot_id}.tar": snapshot.archive,
            }
        )
        with self.assertRaises(storage.SnapshotIntegrityError):
            backend.list()


class TestRestore(StorageTestCase):
    def test_nonempty_destination_refuses_without_force(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        destination = self.root / "destination"
        destination.mkdir()
        old = destination / "old.txt"
        old.write_text("keep me", encoding="utf-8")

        with self.assertRaises(storage.DestinationNotEmptyError):
            storage.restore_snapshot(snapshot, destination)

        self.assertEqual("keep me", old.read_text(encoding="utf-8"))
        self.assertEqual([], list(self.root.glob("destination.pre-restore-*")))

    def test_force_restore_renames_existing_destination_recoverably(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        destination = self.root / "destination"
        destination.mkdir()
        (destination / "old.txt").write_text("recoverable", encoding="utf-8")

        result = storage.restore_snapshot(snapshot, destination, force=True)

        self.assertIsNotNone(result.backup)
        self.assertTrue(result.backup.is_dir())
        self.assertEqual("recoverable", (result.backup / "old.txt").read_text(encoding="utf-8"))
        self.assertTrue((destination / "Work" / "decision.md").is_file())
        self.assertFalse((destination / "old.txt").exists())

    def test_empty_existing_destination_is_allowed(self):
        snapshot = storage.create_snapshot(self.make_bundle())
        destination = self.root / "empty"
        destination.mkdir()
        result = storage.restore_snapshot(snapshot, destination)
        self.assertIsNone(result.backup)
        self.assertTrue((destination / "index.md").is_file())


class TestOptionalBackends(StorageTestCase):
    def test_rclone_is_lazy_and_missing_executable_is_actionable(self):
        backend = storage.RcloneBackend(
            "configured:brain", executable="definitely-not-a-real-rclone-executable-82371"
        )
        with self.assertRaisesRegex(storage.MissingDependencyError, "rclone"):
            backend.list()

    def test_postgres_import_is_lazy_and_missing_dependency_is_actionable(self):
        backend = storage.PostgresBackend(dsn="postgresql://example.invalid/db")
        with mock.patch.object(
            storage.importlib, "import_module", side_effect=ModuleNotFoundError("psycopg")
        ):
            with self.assertRaisesRegex(storage.MissingDependencyError, "psycopg"):
                backend.list()

    def test_supabase_can_be_selected_by_dsn_environment_name(self):
        backend = storage.PostgresBackend(dsn_env="SUPABASE_DB_URL")
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                storage.importlib,
                "import_module",
                return_value=mock.Mock(connect=mock.Mock()),
            ):
                with self.assertRaisesRegex(
                    storage.MissingConfigurationError, "SUPABASE_DB_URL"
                ):
                    backend.list()

    def test_postgres_table_name_rejects_sql(self):
        with self.assertRaises(storage.MissingConfigurationError):
            storage.PostgresBackend(dsn="x", table="snapshots; DROP TABLE users")

    def test_postgres_list_verifies_stored_snapshot_bytes(self):
        snapshot = storage.create_snapshot(self.make_bundle("postgres-list"))

        class Cursor:
            def __init__(self):
                self.rows = []
                self.executed = []

            def execute(self, sql, params=None):
                self.executed.append((sql, params))
                if sql.lstrip().startswith("SELECT snapshot_id, manifest, snapshot"):
                    self.rows = [(snapshot.snapshot_id, snapshot.manifest.to_bytes(), snapshot.archive, "now")]
                elif sql.lstrip().startswith("CREATE TABLE"):
                    self.rows = []

            def fetchall(self):
                return self.rows

            def fetchone(self):
                return None

        class Connection:
            def __init__(self):
                self.cursor_value = Cursor()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def cursor(self):
                class CursorContext:
                    def __enter__(_self):
                        return self.cursor_value

                    def __exit__(_self, *args):
                        return False

                return CursorContext()

        connection = Connection()
        backend = storage.PostgresBackend(dsn="postgresql://example.invalid/db")
        with mock.patch.object(backend, "_connect", return_value=connection):
            entries = backend.list()
        self.assertEqual([snapshot.snapshot_id], [entry.snapshot_id for entry in entries])
        self.assertEqual(len(snapshot.archive), entries[0].size)

    def test_postgres_list_refuses_manifest_id_mismatch(self):
        snapshot = storage.create_snapshot(self.make_bundle("postgres-bad-list"))
        other_bundle = self.make_bundle("postgres-bad-list-other")
        (other_bundle / "different.md").write_text("---\ntype: Note\n---\nother\n", encoding="utf-8")
        other = storage.create_snapshot(other_bundle)

        class Cursor:
            def execute(self, sql, params=None):
                self.rows = [(snapshot.snapshot_id, other.manifest.to_bytes(), snapshot.archive, "now")]

            def fetchall(self):
                return self.rows

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def cursor(self):
                cursor = Cursor()
                class CursorContext:
                    def __enter__(_self): return cursor
                    def __exit__(_self, *args): return False
                return CursorContext()

        backend = storage.PostgresBackend(dsn="postgresql://example.invalid/db")
        with mock.patch.object(backend, "_connect", return_value=Connection()):
            with self.assertRaises(storage.SnapshotIntegrityError):
                backend.list()


class TestRemotePrivacyGate(StorageTestCase):
    def snapshot_with_frontmatter(self, frontmatter, body="content"):
        bundle = self.root / f"privacy-{len(list(self.root.iterdir()))}"
        bundle.mkdir()
        (bundle / "concept.md").write_text(
            f"---\n{frontmatter.strip()}\n---\n\n{body}\n", encoding="utf-8"
        )
        return storage.create_snapshot(bundle)

    @staticmethod
    def plausible_fernet_token():
        # Structural Fernet frame: version + timestamp + IV + one ciphertext
        # block + HMAC. The storage gate checks shape; rebuild verifies the HMAC.
        frame = b"\x80" + (b"\x00" * 8) + (b"\x01" * 16) + (b"\x02" * 16) + (b"\x03" * 32)
        return base64.urlsafe_b64encode(frame).decode("ascii")

    def test_remote_backends_refuse_plaintext_private_concepts_before_io(self):
        private_cases = (
            "type: Note\ntags: [private]",
            "type: Note\ntags:\n  - psych",
            "type: Note\ntags: &sensitive [private]",
            "type: Episode",
            "type: RelationshipModel",
        )
        for frontmatter in private_cases:
            with self.subTest(frontmatter=frontmatter):
                snapshot = self.snapshot_with_frontmatter(frontmatter)
                rclone = storage.RcloneBackend(
                    "configured:brain", executable="definitely-missing-rclone"
                )
                postgres = storage.PostgresBackend(dsn="postgresql://example.invalid/db")
                with self.assertRaises(storage.PlaintextPrivateError):
                    rclone.push(snapshot)
                with self.assertRaises(storage.PlaintextPrivateError):
                    postgres.push(snapshot)

    def test_encrypted_private_concept_is_accepted(self):
        snapshot = self.snapshot_with_frontmatter(
            "type: Episode\ntags: [private]\nsb_encrypted: fernet",
            body=self.plausible_fernet_token(),
        )
        backend = storage.RcloneBackend("configured:brain")
        with mock.patch.object(backend, "_run", return_value=b"") as run:
            result = backend.push(snapshot)
        self.assertEqual(snapshot.snapshot_id, result.snapshot_id)
        self.assertEqual([], storage.find_plaintext_private_concepts(snapshot))
        self.assertEqual(2, run.call_count)

    def test_public_concept_is_accepted(self):
        snapshot = self.snapshot_with_frontmatter("type: Note\ntags: [public, work]")
        backend = storage.RcloneBackend("configured:brain")
        with mock.patch.object(backend, "_run", return_value=b""):
            result = backend.push(snapshot)
        self.assertEqual(snapshot.snapshot_id, result.snapshot_id)

    def test_explicit_plaintext_override_allows_remote_push(self):
        snapshot = self.snapshot_with_frontmatter("type: Note\ntags: [private]")
        backend = storage.RcloneBackend(
            "configured:brain", allow_plaintext_private=True
        )
        with mock.patch.object(backend, "_run", return_value=b"") as run:
            result = backend.push(snapshot)
        self.assertEqual(snapshot.snapshot_id, result.snapshot_id)
        self.assertEqual(2, run.call_count)
        self.assertEqual(
            1,
            len(
                storage.enforce_remote_privacy(
                    snapshot, allow_plaintext_private=True
                )
            ),
        )

    def test_false_encryption_marker_does_not_bypass_gate(self):
        snapshot = self.snapshot_with_frontmatter(
            "type: Episode\nsb_encrypted: !!bool false"
        )
        with self.assertRaises(storage.PlaintextPrivateError):
            storage.enforce_remote_privacy(snapshot)

    def test_truthy_wrong_encryption_marker_does_not_bypass_gate(self):
        for marker in ("true", "aes256", "FERNET"):
            with self.subTest(marker=marker):
                snapshot = self.snapshot_with_frontmatter(
                    f"type: Episode\nsb_encrypted: {marker}",
                    body=self.plausible_fernet_token(),
                )
                with self.assertRaises(storage.PlaintextPrivateError):
                    storage.enforce_remote_privacy(snapshot)

    def test_fernet_marker_with_plaintext_body_does_not_bypass_gate(self):
        snapshot = self.snapshot_with_frontmatter(
            "type: Episode\nsb_encrypted: fernet",
            body="This is still private plaintext, not a Fernet token.",
        )
        with self.assertRaises(storage.PlaintextPrivateError):
            storage.enforce_remote_privacy(snapshot)


class TestStorageCli(StorageTestCase):
    def test_local_push_list_pull_runtime(self):
        bundle = self.make_bundle()
        store = self.root / "store"
        restored = self.root / "restored"

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                0,
                storage_cli.main(
                    [
                        "push",
                        "--backend",
                        "local",
                        "--store",
                        str(store),
                        "--bundle",
                        str(bundle),
                    ]
                ),
            )
            self.assertEqual(
                0,
                storage_cli.main(
                    ["list", "--backend", "local", "--store", str(store)]
                ),
            )
            self.assertEqual(
                0,
                storage_cli.main(
                    [
                        "pull",
                        "--backend",
                        "local",
                        "--store",
                        str(store),
                        "--dest",
                        str(restored),
                    ]
                ),
            )

        text = output.getvalue()
        self.assertIn("stored:", text)
        self.assertIn("restored:", text)
        self.assertEqual(
            (bundle / "Work" / "decision.md").read_bytes(),
            (restored / "Work" / "decision.md").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
