"""Unit tests for the optional selective-encryption adapter (G13 / R13)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import crypto  # noqa: E402

BACKEND = crypto.backend_available()


@unittest.skipUnless(BACKEND, "cryptography backend not installed")
class TestCrypto(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.key = crypto.generate_key(str(Path(self.tmp.name) / "k.key"))
        os.environ["SECONDBRAIN_KEY_FILE"] = str(self.key)

    def tearDown(self):
        os.environ.pop("SECONDBRAIN_KEY_FILE", None)
        self.tmp.cleanup()

    def test_roundtrip_identity(self):
        s = "private 中文 secret \n multi-line"
        self.assertEqual(crypto.decrypt(crypto.encrypt(s)), s)

    def test_ciphertext_hides_plaintext(self):
        tok = crypto.encrypt("TOPSECRET")
        self.assertNotIn("TOPSECRET", tok)

    def test_available_reflects_key(self):
        self.assertTrue(crypto.available())
        os.environ["SECONDBRAIN_KEY_FILE"] = str(Path(self.tmp.name) / "absent.key")
        self.assertFalse(crypto.available())

    def test_is_private_classification(self):
        self.assertTrue(crypto.is_private({"tags": ["private"], "type": "Note"}))
        self.assertTrue(crypto.is_private({"tags": ["psych"], "type": "Note"}))
        self.assertTrue(crypto.is_private({"tags": [], "type": "Episode"}))
        self.assertTrue(crypto.is_private({"tags": [], "type": "RelationshipModel"}))
        self.assertFalse(crypto.is_private({"tags": ["misc"], "type": "Note"}))

    def test_encrypt_without_key_raises(self):
        os.environ["SECONDBRAIN_KEY_FILE"] = str(Path(self.tmp.name) / "absent.key")
        with self.assertRaises(crypto.EncryptionUnavailable):
            crypto.encrypt("x")


if __name__ == "__main__":
    unittest.main()
