import os
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "brain_cli.py"


class TestBrainCLIWrappers(unittest.TestCase):
    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(CLI), *map(str, args)],
                              text=True, capture_output=True, env=env)

    def test_empty_stats_and_summary_offer_first_capture_only_in_human_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "brain.db"
            env = dict(os.environ, SECONDBRAIN_DB=str(db))
            guidance = ('brain add "Project idea" "What I want to remember"',
                        'brain search "Project idea"')
            for command in ("stats", "summary"):
                result = self.run_cli("--db", db, command, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                for phrase in guidance:
                    self.assertIn(phrase, result.stdout)
                machine = self.run_cli("--db", db, "--json", command, env=env)
                self.assertEqual(machine.returncode, 0, machine.stderr)
                parsed = json.loads(machine.stdout)
                self.assertIsInstance(parsed, dict)
                self.assertNotIn("Get started", machine.stdout)

            added = self.run_cli("--db", db, "add", "Existing", "Some durable note", env=env)
            self.assertEqual(added.returncode, 0, added.stderr)
            for command in ("stats", "summary"):
                result = self.run_cli("--db", db, command, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Get started", result.stdout)

    def test_installer_prints_quoted_portable_first_capture_and_recall(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn(' add "First memory" "Something worth remembering"\\n\'', installer)
        self.assertIn(' search "First memory"\\n\'', installer)
        self.assertIn('REPO_DIR="$(cd "$(dirname "$0")" && pwd)"', installer)
        self.assertIn('BRAIN_CLI_PATH="$REPO_DIR/scripts/brain_cli.py"', installer)
        capture_examples = installer[installer.index("Copy/paste these commands"):]
        self.assertNotIn("from any shell", installer)
        self.assertIn('python3 "%s"', capture_examples)
        self.assertIn('"$BRAIN_CLI_PATH"', capture_examples)

    def test_help_lists_wrappers(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("sync", "backup", "key"):
            self.assertIn(name, result.stdout)

    def test_key_status_and_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, SECONDBRAIN_KEY_FILE=str(Path(tmp) / "key"),
                       SECONDBRAIN_REQUIRE_ENCRYPTION="yes")
            status = self.run_cli("key", "status", env=env)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertRegex(status.stdout, r"(?m)^backend=(cryptography\.fernet|unavailable)$")
            self.assertIn("key_present=false", status.stdout)
            self.assertIn("strict_mode=true", status.stdout)
            initialized = self.run_cli("key", "init", env=env)
            if "backend=cryptography.fernet" in status.stdout:
                self.assertEqual(initialized.returncode, 0, initialized.stderr)
                self.assertTrue(Path(env["SECONDBRAIN_KEY_FILE"]).exists())
            else:
                self.assertNotEqual(initialized.returncode, 0)
                self.assertFalse(Path(env["SECONDBRAIN_KEY_FILE"]).exists())
            status = self.run_cli("key", "status", env=env)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn(f"key_present={'true' if Path(env['SECONDBRAIN_KEY_FILE']).exists() else 'false'}", status.stdout)
            key_path = Path(env["SECONDBRAIN_KEY_FILE"])
            if key_path.exists():
                existing_key = key_path.read_bytes()
                repeated_init = self.run_cli("key", "init", env=env)
                self.assertEqual(repeated_init.returncode, 2, repeated_init.stderr)
                self.assertIn("refusing to overwrite", repeated_init.stderr)
                self.assertEqual(key_path.read_bytes(), existing_key)
            else:
                self.assertFalse(key_path.exists())

    @unittest.skipUnless(shutil.which("git"), "git is required for sync integration tests")
    def test_sync_forwards_remote_to_child_local_bare_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "bundle"
            db = root / "brain.db"
            remote = root / "remote.git"
            created = subprocess.run(["git", "init", "--bare", str(remote)],
                                     text=True, capture_output=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            env = dict(os.environ, SECONDBRAIN_DB=str(db))
            env.pop("SECONDBRAIN_BUNDLE", None)
            result = self.run_cli("--db", db, "--bundle", bundle, "sync",
                                  "--remote", remote, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(bundle.exists())
            refs = subprocess.run(["git", "--git-dir", str(remote), "show-ref", "--heads"],
                                  text=True, capture_output=True)
            self.assertEqual(refs.returncode, 0, refs.stderr)
            self.assertIn("refs/heads/", refs.stdout)

    def test_sync_uses_configured_default_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "brain.db"
            bundle = root / "configured-bundle"
            env = dict(os.environ, SECONDBRAIN_DB=str(db),
                       SECONDBRAIN_BUNDLE=str(bundle))
            result = self.run_cli("sync", env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(db.exists())
            self.assertTrue(bundle.exists())
            self.assertTrue((bundle / ".git").is_dir())
            remotes = subprocess.run(["git", "-C", str(bundle), "remote"],
                                     text=True, capture_output=True)
            self.assertEqual(remotes.returncode, 0, remotes.stderr)
            self.assertEqual(remotes.stdout.strip(), "")

    def test_backup_forwards_and_preserves_storage_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            bundle.mkdir()
            store = Path(tmp) / "store"
            result = self.run_cli("backup", "--backend", "local", "--bundle", bundle,
                                  "--store", store)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(store.exists())
            self.assertTrue(any(store.iterdir()))
            invalid = self.run_cli("backup", "--backend", "local", "--bundle", bundle)
            self.assertEqual(invalid.returncode, 2, invalid.stderr)
            self.assertIn("local backend requires --store", invalid.stderr)

    @unittest.skipUnless(shutil.which("git"), "git is required for sync integration tests")
    def test_sync_propagates_child_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_remote = root / "does-not-exist.git"
            result = self.run_cli("--db", root / "brain.db", "--bundle", root / "bundle",
                                  "sync", "--remote", missing_remote,
                                  env=dict(os.environ))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
