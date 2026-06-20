#!/usr/bin/env python3
"""Optional selective-encryption adapter for SecondBrain (G13 / R13).

The stdlib-only core NEVER imports this module. Only the export/rebuild path
imports it, and only to protect *private* Concepts: a Concept tagged `private`
or `psych`, or whose OKF `type` is `Episode` / `RelationshipModel`, is encrypted
before it is written into the OKF Bundle that git pushes. Public Concepts stay
plaintext and git-diffable.

Backend: `cryptography`'s Fernet (AES-128-CBC + HMAC-SHA256, URL-safe base64
tokens). It is lazy-imported so the dependency is optional — when it is absent,
or no key is configured, callers must REFUSE to write private data as plaintext
rather than leak it (see `EncryptionUnavailable`).

Key file: `$SECONDBRAIN_KEY_FILE`, else `~/.secondbrain/secret.key` (mode 0600).
Generate one with `generate_key()` or `python scripts/crypto.py init`.
"""
import os
from pathlib import Path

# Concepts classified private (their content is encrypted before export).
PRIVATE_TAGS = {"private", "psych"}
PRIVATE_TYPES = {"episode", "relationshipmodel"}

# Frontmatter marker written on an encrypted Concept file.
MARKER = "sb_encrypted"
SCHEME = "fernet"


class EncryptionUnavailable(RuntimeError):
    """Raised when private data must be encrypted but no backend/key is available.
    Callers MUST let this propagate (refuse to leak), never fall back to plaintext."""


def _key_path() -> Path:
    return Path(os.environ.get("SECONDBRAIN_KEY_FILE",
                               str(Path.home() / ".secondbrain" / "secret.key")))


def backend_available() -> bool:
    """True iff the optional `cryptography` backend can be imported."""
    try:
        import cryptography.fernet  # noqa: F401
        return True
    except Exception:
        return False


def key_available() -> bool:
    return _key_path().exists()


def available() -> bool:
    """True iff we can actually encrypt/decrypt right now (backend + key)."""
    return backend_available() and key_available()


def generate_key(path: str | None = None) -> Path:
    """Create a fresh Fernet key file (0600). Returns its path."""
    from cryptography.fernet import Fernet
    p = Path(path) if path else _key_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(Fernet.generate_key())
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass  # best-effort on platforms without POSIX perms
    return p


def _fernet():
    if not backend_available():
        raise EncryptionUnavailable(
            "the 'cryptography' package is not installed — cannot encrypt private "
            "Concepts; install it or remove the private/psych tag before export")
    from cryptography.fernet import Fernet
    kp = _key_path()
    if not kp.exists():
        raise EncryptionUnavailable(
            f"no encryption key at {kp} — run `python scripts/crypto.py init` (or set "
            f"$SECONDBRAIN_KEY_FILE) before exporting private Concepts")
    return Fernet(kp.read_bytes().strip())


def is_private(concept: dict) -> bool:
    """True iff a Concept must be encrypted before it leaves this device."""
    tags = {str(t).lower() for t in (concept.get("tags") or [])}
    typ = str(concept.get("type") or "").lower()
    return bool(tags & PRIVATE_TAGS) or typ in PRIVATE_TYPES


def encrypt(text: str) -> str:
    """Encrypt UTF-8 text to an ASCII Fernet token. Raises EncryptionUnavailable
    if no backend/key is configured (never returns plaintext)."""
    return _fernet().encrypt(text.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.strip().encode("ascii")).decode("utf-8")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "init":
        dest = generate_key(sys.argv[2] if len(sys.argv) > 2 else None)
        print(f"wrote encryption key: {dest}")
    else:
        print("usage: python scripts/crypto.py init [key_path]")
        print(f"backend_available={backend_available()} key_available={key_available()}")
