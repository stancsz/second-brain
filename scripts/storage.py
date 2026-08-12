#!/usr/bin/env python3
"""Verified, immutable snapshot storage for an OKF Bundle.

The Bundle remains the source of truth.  This module only creates deterministic,
content-addressed backup snapshots and restores them after full verification.
It deliberately does not implement bidirectional synchronization.

The core is stdlib-only.  ``rclone`` is invoked only by ``RcloneBackend`` and
``psycopg`` is imported only when ``PostgresBackend`` is used.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import importlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol, runtime_checkable


SNAPSHOT_FORMAT = "secondbrain-okf-snapshot"
SNAPSHOT_VERSION = 1
DIRTY_MARKER = ".secondbrain-dirty"
SYNC_MARKER = ".secondbrain-sync"
PAIR_STATE = ".secondbrain-state.json"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class StorageError(RuntimeError):
    """Base class for an actionable storage failure."""


class SnapshotIntegrityError(StorageError):
    """Snapshot bytes do not match their manifest."""


class UnsafeArchiveError(SnapshotIntegrityError):
    """A snapshot contains a path or tar member that is unsafe to restore."""


class SnapshotChangedError(StorageError):
    """The Bundle changed while it was being captured."""


class BundleDirtyError(StorageError):
    """The Bundle has an interrupted write-through and cannot be snapshotted."""


class DestinationNotEmptyError(StorageError):
    """Restore destination is occupied and --force was not supplied."""


class RestoreError(StorageError):
    """A verified snapshot could not be installed safely."""


class MissingDependencyError(StorageError):
    """An optional adapter dependency is not available."""


class MissingConfigurationError(StorageError):
    """A backend is missing required, non-secret configuration."""


class BackendError(StorageError):
    """A configured backend operation failed."""


class SnapshotNotFoundError(BackendError):
    """The requested snapshot does not exist in the backend."""


class SnapshotConflictError(BackendError):
    """An immutable snapshot id already maps to different bytes."""


class PlaintextPrivateError(StorageError):
    """A remote push contains private Concepts that are not encrypted."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    """Return the one manifest encoding used for hashing and persistence.

    Manifest values contain only strings, integers, lists, and dictionaries, so
    Python's sorted-key compact JSON is stable across supported Python versions.
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotIntegrityError(f"duplicate JSON key in manifest: {key!r}")
        result[key] = value
    return result


def _validate_snapshot_id(snapshot_id: str) -> str:
    value = str(snapshot_id).lower()
    if not _HASH_RE.fullmatch(value):
        raise SnapshotNotFoundError("snapshot id must be a 64-character SHA-256 hex digest")
    return value


def _validate_member_path(raw: str) -> str:
    """Validate a portable, Bundle-relative POSIX path and return it unchanged."""
    if not isinstance(raw, str) or not raw:
        raise UnsafeArchiveError("snapshot member path must be a non-empty string")
    if raw != unicodedata.normalize("NFC", raw):
        raise UnsafeArchiveError(f"snapshot member path is not NFC-normalized: {raw!r}")
    if "\\" in raw or "\x00" in raw:
        raise UnsafeArchiveError(f"unsafe snapshot member path: {raw!r}")
    if any(ord(ch) < 32 for ch in raw):
        raise UnsafeArchiveError(f"control character in snapshot member path: {raw!r}")
    if raw.startswith("/") or PurePosixPath(raw).is_absolute() or PureWindowsPath(raw).drive:
        raise UnsafeArchiveError(f"absolute or drive-qualified snapshot path: {raw!r}")

    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise UnsafeArchiveError(f"traversal or empty component in snapshot path: {raw!r}")
    for part in parts:
        if ":" in part:
            raise UnsafeArchiveError(f"drive-relative or alternate-stream path: {raw!r}")
        if part != part.rstrip(" ."):
            raise UnsafeArchiveError(f"Windows-ambiguous snapshot path: {raw!r}")
        stem = part.split(".", 1)[0].upper()
        if stem in _WINDOWS_RESERVED:
            raise UnsafeArchiveError(f"Windows-reserved snapshot path: {raw!r}")
    return raw


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    size: int
    sha256: str

    def __post_init__(self):
        object.__setattr__(self, "path", _validate_member_path(self.path))
        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size < 0:
            raise SnapshotIntegrityError(f"invalid size for {self.path!r}")
        if not isinstance(self.sha256, str) or not _HASH_RE.fullmatch(self.sha256):
            raise SnapshotIntegrityError(f"invalid SHA-256 for {self.path!r}")

    def to_dict(self) -> dict:
        return {"path": self.path, "sha256": self.sha256, "size": self.size}


@dataclass(frozen=True)
class Manifest:
    archive_sha256: str
    archive_size: int
    files: tuple[ManifestEntry, ...]
    format: str = SNAPSHOT_FORMAT
    version: int = SNAPSHOT_VERSION

    def __post_init__(self):
        object.__setattr__(self, "files", tuple(self.files))
        if self.format != SNAPSHOT_FORMAT or self.version != SNAPSHOT_VERSION:
            raise SnapshotIntegrityError(
                f"unsupported snapshot format/version: {self.format!r} v{self.version!r}"
            )
        if not isinstance(self.archive_sha256, str) or not _HASH_RE.fullmatch(
            self.archive_sha256
        ):
            raise SnapshotIntegrityError("invalid archive SHA-256 in manifest")
        if (
            isinstance(self.archive_size, bool)
            or not isinstance(self.archive_size, int)
            or self.archive_size < 0
        ):
            raise SnapshotIntegrityError("invalid archive size in manifest")

        names = [entry.path for entry in self.files]
        if names != sorted(names):
            raise SnapshotIntegrityError("manifest file entries are not sorted by path")
        if len(names) != len(set(names)):
            raise SnapshotIntegrityError("manifest contains duplicate file paths")
        folded = [name.casefold() for name in names]
        if len(folded) != len(set(folded)):
            raise SnapshotIntegrityError(
                "manifest contains paths that collide on a case-insensitive filesystem"
            )

    @property
    def snapshot_id(self) -> str:
        return _sha256(self.to_bytes())

    def to_dict(self) -> dict:
        return {
            "archive_sha256": self.archive_sha256,
            "archive_size": self.archive_size,
            "files": [entry.to_dict() for entry in self.files],
            "format": self.format,
            "version": self.version,
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def to_json(self) -> str:
        return self.to_bytes().decode("utf-8")

    @classmethod
    def from_dict(cls, raw: dict) -> "Manifest":
        if not isinstance(raw, dict):
            raise SnapshotIntegrityError("manifest must be a JSON object")
        expected = {"archive_sha256", "archive_size", "files", "format", "version"}
        if set(raw) != expected:
            missing = sorted(expected - set(raw))
            extra = sorted(set(raw) - expected)
            raise SnapshotIntegrityError(
                f"manifest fields do not match v1 schema (missing={missing}, extra={extra})"
            )
        files = raw.get("files")
        if not isinstance(files, list):
            raise SnapshotIntegrityError("manifest files must be a list")
        entries = []
        for item in files:
            if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
                raise SnapshotIntegrityError("invalid manifest file entry")
            entries.append(ManifestEntry(item["path"], item["size"], item["sha256"]))
        return cls(
            archive_sha256=raw["archive_sha256"],
            archive_size=raw["archive_size"],
            files=tuple(entries),
            format=raw["format"],
            version=raw["version"],
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "Manifest":
        try:
            raw = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        except SnapshotIntegrityError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SnapshotIntegrityError(f"invalid manifest JSON: {exc}") from exc
        return cls.from_dict(raw)

    @classmethod
    def from_json(cls, text: str) -> "Manifest":
        return cls.from_bytes(text.encode("utf-8"))


@dataclass(frozen=True)
class Snapshot:
    archive: bytes
    manifest: Manifest

    def __post_init__(self):
        if not isinstance(self.archive, bytes):
            object.__setattr__(self, "archive", bytes(self.archive))
        if not isinstance(self.manifest, Manifest):
            raise TypeError("manifest must be a Manifest")

    @property
    def snapshot_id(self) -> str:
        return self.manifest.snapshot_id


@dataclass(frozen=True)
class PushResult:
    snapshot_id: str
    backend: str
    created: bool | None

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "created": self.created,
            "snapshot_id": self.snapshot_id,
        }


@dataclass(frozen=True)
class RemoteEntry:
    snapshot_id: str
    backend: str
    size: int | None = None
    stored_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "size": self.size,
            "snapshot_id": self.snapshot_id,
            "stored_at": self.stored_at,
        }


@dataclass(frozen=True)
class RestoreResult:
    snapshot_id: str
    destination: Path
    backup: Path | None

    def to_dict(self) -> dict:
        return {
            "backup": str(self.backup) if self.backup else None,
            "destination": str(self.destination),
            "snapshot_id": self.snapshot_id,
        }


@runtime_checkable
class Backend(Protocol):
    name: str

    def push(self, snapshot: Snapshot) -> PushResult: ...

    def pull(self, snapshot_id: str | None = None) -> Snapshot: ...

    def list(self) -> list[RemoteEntry]: ...


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if is_junction is not None:
        try:
            if is_junction():
                return True
        except OSError:
            return True
    try:
        attrs = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attrs & reparse_flag)


def _collect_bundle_files(bundle_dir: Path) -> list[tuple[str, Path]]:
    root = bundle_dir.resolve(strict=True)
    if not root.is_dir() or _is_link_or_reparse(bundle_dir):
        raise StorageError(f"Bundle path must be a real directory, not a link: {bundle_dir}")
    if (root / DIRTY_MARKER).exists() or (root / SYNC_MARKER).exists():
        raise BundleDirtyError(
            "Bundle has an incomplete canonical export or Git sync; finish recovery "
            "with the paired database before taking a snapshot"
        )

    found = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs = []
        for name in sorted(dirs):
            if name == ".git":
                continue
            child = current_path / name
            if _is_link_or_reparse(child):
                raise StorageError(f"Bundle contains a linked/reparse directory: {child}")
            kept_dirs.append(name)
        dirs[:] = kept_dirs

        for name in sorted(files):
            if (
                name in {DIRTY_MARKER, SYNC_MARKER}
                or name.startswith(DIRTY_MARKER + ".tmp-")
                or name.startswith(SYNC_MARKER + ".tmp-")
            ):
                raise BundleDirtyError(
                    "Bundle became dirty while snapshotting; retry after canonical recovery"
                )
            if name.startswith(PAIR_STATE + ".tmp-"):
                raise BundleDirtyError(
                    "Bundle pair-state was changing while snapshotting; retry"
                )
            path = current_path / name
            if _is_link_or_reparse(path):
                raise StorageError(f"Bundle contains a linked/reparse file: {path}")
            rel = path.relative_to(root).as_posix()
            rel = _validate_member_path(rel)
            found.append((rel, path))

    found.sort(key=lambda item: item[0])
    names = [name for name, _ in found]
    if len({name.casefold() for name in names}) != len(names):
        raise StorageError("Bundle has paths that collide on a case-insensitive filesystem")
    return found


def _read_stable_file(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise SnapshotChangedError(f"could not open stable Bundle file {path}: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise StorageError(f"Bundle contains a non-regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read()
        after = os.fstat(fd)
    finally:
        os.close(fd)

    fingerprint_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        getattr(before, "st_mtime_ns", None),
        getattr(before, "st_ctime_ns", None),
    )
    fingerprint_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        getattr(after, "st_mtime_ns", None),
        getattr(after, "st_ctime_ns", None),
    )
    if fingerprint_before != fingerprint_after or len(data) != after.st_size:
        raise SnapshotChangedError(f"Bundle file changed while snapshotting: {path}")
    return data


def create_snapshot(bundle_dir: str | os.PathLike[str]) -> Snapshot:
    """Create deterministic tar bytes plus a canonical hash manifest."""
    root = Path(bundle_dir)
    if not root.exists():
        raise StorageError(f"Bundle directory does not exist: {root}")

    # Use the same crash-released cross-process lock as canonical writers so a
    # snapshot is taken from one complete Bundle generation, never between files.
    from store import bundle_lock

    with bundle_lock(root):
        return _create_snapshot_locked(root)


def _create_snapshot_locked(root: Path) -> Snapshot:
    """Create a snapshot while the caller holds the Bundle writer lock."""

    payloads = []
    entries = []
    for rel, path in _collect_bundle_files(root):
        data = _read_stable_file(path)
        payloads.append((rel, data))
        entries.append(ManifestEntry(rel, len(data), _sha256(data)))

    archive_buffer = io.BytesIO()
    with tarfile.open(
        fileobj=archive_buffer,
        mode="w:",
        format=tarfile.PAX_FORMAT,
        dereference=False,
    ) as tar:
        for rel, data in payloads:
            info = tarfile.TarInfo(rel)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.type = tarfile.REGTYPE
            info.pax_headers = {}
            tar.addfile(info, io.BytesIO(data))

    archive = archive_buffer.getvalue()
    manifest = Manifest(
        archive_sha256=_sha256(archive),
        archive_size=len(archive),
        files=tuple(entries),
    )
    snapshot = Snapshot(archive, manifest)
    verify_snapshot(snapshot)
    return snapshot


def verify_snapshot(snapshot: Snapshot) -> Snapshot:
    """Fully verify archive identity, member safety, and every file hash."""
    if not isinstance(snapshot, Snapshot):
        raise TypeError("snapshot must be a Snapshot")
    if len(snapshot.archive) != snapshot.manifest.archive_size:
        raise SnapshotIntegrityError("archive size does not match manifest")
    if _sha256(snapshot.archive) != snapshot.manifest.archive_sha256:
        raise SnapshotIntegrityError("archive SHA-256 does not match manifest")

    expected = {entry.path: entry for entry in snapshot.manifest.files}
    seen = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(snapshot.archive), mode="r:") as tar:
            for member in tar:
                name = _validate_member_path(member.name)
                if name in seen:
                    raise UnsafeArchiveError(f"duplicate tar member: {name!r}")
                seen.add(name)
                if not member.isreg():
                    raise UnsafeArchiveError(f"non-regular tar member: {name!r}")
                entry = expected.get(name)
                if entry is None:
                    raise SnapshotIntegrityError(f"tar member is absent from manifest: {name!r}")
                if member.size != entry.size:
                    raise SnapshotIntegrityError(f"size mismatch for tar member: {name!r}")
                source = tar.extractfile(member)
                if source is None:
                    raise SnapshotIntegrityError(f"cannot read tar member: {name!r}")
                digest = hashlib.sha256()
                count = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    count += len(chunk)
                if count != entry.size or digest.hexdigest() != entry.sha256:
                    raise SnapshotIntegrityError(f"content hash mismatch for: {name!r}")
    except StorageError:
        raise
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise SnapshotIntegrityError(f"invalid snapshot tar: {exc}") from exc

    missing = sorted(set(expected) - seen)
    if missing:
        raise SnapshotIntegrityError(f"manifest entries missing from tar: {missing}")
    return snapshot


def _frontmatter_fields(text: str) -> dict[str, object]:
    """Parse only the small YAML subset needed for the remote privacy gate.

    OKF permits general YAML, but SecondBrain's serializer emits scalar fields
    and inline JSON lists.  We additionally recognize conventional multiline
    YAML lists so hand-authored Obsidian/OKF notes cannot bypass private tags.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise PlaintextPrivateError(
            "remote push refused: a Markdown file has unclosed frontmatter and "
            "cannot be classified safely"
        )

    fields: dict[str, object] = {}
    active_list = None
    for raw_line in lines[1:end]:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if active_list and stripped.startswith("-"):
            fields.setdefault(active_list, []).append(
                stripped[1:].strip().strip("'\"")
            )
            continue
        if active_list and (raw_line.startswith(" ") or raw_line.startswith("\t")):
            continue
        active_list = None
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", stripped)
        if not match:
            continue
        key = match.group(1).lower()
        value = match.group(2).strip()
        if not value:
            fields[key] = []
            active_list = key
        else:
            fields[key] = value
    return fields


def _scalar_value(value: object) -> str:
    if isinstance(value, list):
        return ""
    raw = re.split(r"\s+#", str(value).strip(), maxsplit=1)[0].strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        raw = raw[1:-1]
    return raw.strip()


def _tag_values(value: object) -> set[str]:
    if isinstance(value, list):
        return {_scalar_value(item).lower() for item in value if _scalar_value(item)}
    raw = _scalar_value(value)
    if not raw:
        return set()
    if raw.startswith("[") and "]" in raw:
        raw = raw[: raw.index("]") + 1]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = [item.strip().strip("'\"") for item in raw[1:-1].split(",")]
        if isinstance(parsed, list):
            return {_scalar_value(item).lower() for item in parsed if _scalar_value(item)}
    # Conservative YAML fallback also catches anchors such as
    # ``tags: &sensitive [private]`` without importing a YAML dependency.
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_-]+", raw)}


def _truthy_frontmatter(value: object) -> bool:
    raw = _scalar_value(value).lower()
    tokens = re.findall(r"[a-z0-9]+", raw)
    if not tokens:
        return False
    return tokens[-1] not in {"0", "false", "no", "none", "null", "off"}


def _frontmatter_body(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return ""
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[index + 1 :]).strip()
    return ""


def _is_plausible_fernet_envelope(text: str, fields: dict[str, object]) -> bool:
    """Recognize only the encrypted envelope emitted by ``bundle.py``.

    This is a structural upload gate, not cryptographic authentication (the key
    is intentionally unavailable to storage backends).  Real decryption and HMAC
    verification remain the rebuild path's responsibility.
    """
    if _scalar_value(fields.get("sb_encrypted", "")) != "fernet":
        return False
    token = _frontmatter_body(text)
    if len(token) < 100 or len(token) % 4 != 0:
        return False
    if re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", token) is None:
        return False
    try:
        decoded = base64.b64decode(
            token.encode("ascii"), altchars=b"-_", validate=True
        )
    except (UnicodeEncodeError, ValueError, binascii.Error):
        return False
    # Fernet frame: version(1) + timestamp(8) + IV(16) + AES-CBC ciphertext
    # (one or more 16-byte blocks) + HMAC(32).
    if len(decoded) < 73 or decoded[0] != 0x80 or (len(decoded) - 57) % 16 != 0:
        return False
    return base64.urlsafe_b64encode(decoded).decode("ascii") == token


def find_plaintext_private_concepts(snapshot: Snapshot) -> list[tuple[str, tuple[str, ...]]]:
    """Return private Concept paths/reasons that would leave the device plaintext.

    Only a structurally plausible ``sb_encrypted: fernet`` envelope is accepted.
    The returned paths are intended for local diagnostics; backend/CLI errors
    deliberately report only a count so a sensitive title embedded in a filename
    is not copied into logs.
    """
    verify_snapshot(snapshot)
    findings = []
    try:
        with tarfile.open(fileobj=io.BytesIO(snapshot.archive), mode="r:") as tar:
            for member in tar:
                name = _validate_member_path(member.name)
                if not name.lower().endswith(".md"):
                    continue
                source = tar.extractfile(member)
                if source is None:
                    raise SnapshotIntegrityError(f"cannot inspect verified member: {name!r}")
                try:
                    text = source.read().decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise PlaintextPrivateError(
                        "remote push refused: a Markdown file is not valid UTF-8 and "
                        "cannot be classified safely"
                    ) from exc
                fields = _frontmatter_fields(text)
                if not fields or _is_plausible_fernet_envelope(text, fields):
                    continue

                reasons = []
                tags = _tag_values(fields.get("tags", ""))
                private_tags = sorted(tags & {"private", "psych"})
                if private_tags:
                    reasons.append("tag:" + ",".join(private_tags))
                type_tokens = re.findall(
                    r"[a-z][a-z0-9_-]*",
                    _scalar_value(fields.get("type", "")).lower(),
                )
                private_type = next(
                    (
                        token
                        for token in type_tokens
                        if token in {"episode", "relationshipmodel"}
                    ),
                    None,
                )
                if private_type:
                    reasons.append("type:" + private_type)
                if _truthy_frontmatter(fields.get("sb_private", "")):
                    reasons.append("sb_private")
                if reasons:
                    findings.append((name, tuple(reasons)))
    except StorageError:
        raise
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise SnapshotIntegrityError(f"cannot inspect snapshot privacy metadata: {exc}") from exc
    return findings


def enforce_remote_privacy(
    snapshot: Snapshot, *, allow_plaintext_private: bool = False
) -> list[tuple[str, tuple[str, ...]]]:
    """Fail closed before a remote backend receives plaintext private Concepts."""
    findings = find_plaintext_private_concepts(snapshot)
    if findings and not allow_plaintext_private:
        raise PlaintextPrivateError(
            f"remote push refused: {len(findings)} plaintext private Concept(s) detected; "
            "export with encryption configured, or explicitly opt in with "
            "--allow-plaintext-private"
        )
    return findings


def _path_lexists(path: Path) -> bool:
    return os.path.lexists(str(path))


def _destination_occupied(path: Path) -> bool:
    if not _path_lexists(path):
        return False
    if path.is_symlink() or not path.is_dir():
        return True
    return next(path.iterdir(), None) is not None


def _backup_path(destination: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    base = destination.with_name(f"{destination.name}.pre-restore-{stamp}")
    candidate = base
    counter = 2
    while _path_lexists(candidate):
        candidate = destination.with_name(f"{base.name}-{counter}")
        counter += 1
    return candidate


def _fsync_directory(path: Path) -> None:
    """Best-effort directory durability (not supported for every Windows fs)."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _remove_owned_staging(path: Path, parent: Path) -> None:
    """Remove only the exact staging directory created by this restore call."""
    if not _path_lexists(path):
        return
    try:
        actual_parent = path.parent.resolve(strict=True)
        intended_parent = parent.resolve(strict=True)
    except OSError:
        return
    if actual_parent != intended_parent or not path.name.startswith(".secondbrain-restore-"):
        return
    shutil.rmtree(path)


def restore_snapshot(
    snapshot: Snapshot,
    destination: str | os.PathLike[str],
    *,
    force: bool = False,
) -> RestoreResult:
    """Restore after full verification, preserving an occupied forced target.

    Without ``force``, an absent or empty directory is accepted.  With ``force``,
    any existing destination is renamed to a unique ``.pre-restore-*`` sibling
    and is never deleted automatically.
    """
    verify_snapshot(snapshot)
    destination = Path(destination).expanduser().absolute()
    if destination.parent == destination:
        raise RestoreError("refusing to restore over a filesystem root")
    destination.parent.mkdir(parents=True, exist_ok=True)

    exists = _path_lexists(destination)
    occupied = _destination_occupied(destination)
    if occupied and not force:
        raise DestinationNotEmptyError(
            f"restore destination is not empty: {destination}; use --force to preserve "
            "it as a recoverable sibling backup"
        )

    staging = Path(tempfile.mkdtemp(prefix=".secondbrain-restore-", dir=destination.parent))
    backup = None
    removed_empty_destination = False
    try:
        with tarfile.open(fileobj=io.BytesIO(snapshot.archive), mode="r:") as tar:
            for member in tar:
                name = _validate_member_path(member.name)
                target = staging.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise SnapshotIntegrityError(f"cannot read verified member: {name!r}")
                with target.open("xb") as out:
                    shutil.copyfileobj(source, out, length=1024 * 1024)
                    out.flush()
                    os.fsync(out.fileno())
        _fsync_directory(staging)

        if exists:
            if force:
                backup = _backup_path(destination)
                os.replace(destination, backup)
                _fsync_directory(destination.parent)
            else:
                destination.rmdir()  # known empty, real directory
                removed_empty_destination = True

        try:
            os.replace(staging, destination)
            _fsync_directory(destination.parent)
        except Exception as install_exc:
            rollback_exc = None
            if backup is not None and not _path_lexists(destination):
                try:
                    os.replace(backup, destination)
                    backup = None
                except Exception as exc:  # preserve both paths and report explicitly
                    rollback_exc = exc
            elif removed_empty_destination and not _path_lexists(destination):
                try:
                    destination.mkdir()
                except OSError:
                    pass
            if rollback_exc is not None:
                raise RestoreError(
                    f"restore install and rollback both failed; preserved backup path: "
                    f"{backup}; install={install_exc}; rollback={rollback_exc}"
                ) from install_exc
            raise RestoreError(f"could not install verified snapshot: {install_exc}") from install_exc

        return RestoreResult(snapshot.snapshot_id, destination, backup)
    finally:
        _remove_owned_staging(staging, destination.parent)


def _write_immutable(path: Path, data: bytes) -> bool:
    """Create a file exactly once; an identical existing file is a no-op."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if _path_lexists(path):
        if not _is_link_or_reparse(path) and path.is_file() and path.read_bytes() == data:
            return False
        raise SnapshotConflictError(f"immutable snapshot object conflicts at {path}")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        if (
            _path_lexists(path)
            and not _is_link_or_reparse(path)
            and path.is_file()
            and path.read_bytes() == data
        ):
            return False
        raise SnapshotConflictError(f"immutable snapshot object conflicts at {path}")
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    finally:
        os.close(fd)
    _fsync_directory(path.parent)
    return True


class LocalBackend:
    """Immutable snapshots in a user-selected local directory."""

    name = "local"

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root).expanduser().absolute()

    def _paths(self, snapshot_id: str) -> tuple[Path, Path]:
        sid = _validate_snapshot_id(snapshot_id)
        return self.root / f"{sid}.tar", self.root / f"{sid}.manifest.json"

    def push(self, snapshot: Snapshot) -> PushResult:
        verify_snapshot(snapshot)
        archive_path, manifest_path = self._paths(snapshot.snapshot_id)
        # The manifest is the commit marker: list/pull ignore a tar-only partial.
        archive_created = _write_immutable(archive_path, snapshot.archive)
        manifest_created = _write_immutable(manifest_path, snapshot.manifest.to_bytes())
        return PushResult(
            snapshot.snapshot_id,
            self.name,
            archive_created or manifest_created,
        )

    def list(self) -> list[RemoteEntry]:
        if not self.root.exists():
            return []
        archive_ids = set()
        for archive_path in self.root.glob("*.tar"):
            sid = archive_path.name[: -len(".tar")]
            if _HASH_RE.fullmatch(sid):
                if _is_link_or_reparse(archive_path):
                    raise SnapshotIntegrityError(
                        f"local snapshot archive is a link/reparse point: {archive_path}"
                    )
                archive_ids.add(sid)
        entries = []
        manifest_ids = set()
        for manifest_path in self.root.glob("*.manifest.json"):
            sid = manifest_path.name[: -len(".manifest.json")]
            try:
                if _is_link_or_reparse(manifest_path):
                    raise SnapshotIntegrityError(
                        f"local snapshot manifest is a link/reparse point: {manifest_path}"
                    )
                sid = _validate_snapshot_id(sid)
                manifest_ids.add(sid)
                archive_path, _ = self._paths(sid)
                if not archive_path.is_file() or _is_link_or_reparse(archive_path):
                    raise SnapshotIntegrityError(f"snapshot archive is missing for {sid}")
                snapshot = Snapshot(
                    archive_path.read_bytes(),
                    Manifest.from_bytes(manifest_path.read_bytes()),
                )
                if snapshot.snapshot_id != sid:
                    raise SnapshotIntegrityError(f"manifest id does not match filename for {sid}")
                verify_snapshot(snapshot)
                stored = datetime.fromtimestamp(
                    manifest_path.stat().st_mtime, timezone.utc
                ).isoformat()
                entries.append(RemoteEntry(sid, self.name, len(snapshot.archive), stored))
            except StorageError:
                raise
            except OSError as exc:
                raise BackendError(f"cannot inspect local snapshot {sid}: {exc}") from exc
        orphan_ids = sorted(archive_ids - manifest_ids)
        if orphan_ids:
            raise SnapshotIntegrityError(
                f"local snapshot archive has no manifest: {orphan_ids[0]}"
            )
        return sorted(
            entries,
            key=lambda entry: (entry.stored_at or "", entry.snapshot_id),
            reverse=True,
        )

    def pull(self, snapshot_id: str | None = None) -> Snapshot:
        if snapshot_id is None:
            entries = self.list()
            if not entries:
                raise SnapshotNotFoundError(f"no snapshots in local backend {self.root}")
            snapshot_id = entries[0].snapshot_id
        archive_path, manifest_path = self._paths(snapshot_id)
        if not archive_path.is_file() or not manifest_path.is_file():
            raise SnapshotNotFoundError(f"snapshot not found: {snapshot_id}")
        if _is_link_or_reparse(archive_path) or _is_link_or_reparse(manifest_path):
            raise SnapshotIntegrityError("local snapshot objects must not be links/reparse points")
        try:
            snapshot = Snapshot(
                archive_path.read_bytes(),
                Manifest.from_bytes(manifest_path.read_bytes()),
            )
        except OSError as exc:
            raise BackendError(f"cannot read local snapshot {snapshot_id}: {exc}") from exc
        if snapshot.snapshot_id != _validate_snapshot_id(snapshot_id):
            raise SnapshotIntegrityError("requested snapshot id does not match stored manifest")
        return verify_snapshot(snapshot)


class RcloneBackend:
    """Immutable snapshot objects on any configured rclone remote.

    This adapter uses only ``copyto --immutable --checksum``, ``cat``, and
    ``lsjson``.  It never calls ``sync``, ``delete``, or a shell.
    """

    name = "rclone"

    def __init__(
        self,
        remote: str,
        *,
        executable: str = "rclone",
        allow_plaintext_private: bool = False,
    ):
        if not remote or not isinstance(remote, str):
            raise MissingConfigurationError("rclone backend needs a configured remote path")
        self.remote = remote.rstrip("/")
        self.executable = executable
        self.allow_plaintext_private = bool(allow_plaintext_private)

    def _remote_path(self, name: str) -> str:
        return f"{self.remote}/{name}"

    def _run(self, args: list[str]) -> bytes:
        try:
            result = subprocess.run(
                [self.executable, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise MissingDependencyError(
                "rclone is not installed or not on PATH; install rclone and configure a remote"
            ) from exc
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            if not detail:
                detail = result.stdout.decode("utf-8", errors="replace").strip()
            raise BackendError(
                f"rclone command failed with exit {result.returncode}: {detail[:500]}"
            )
        return result.stdout

    def push(self, snapshot: Snapshot) -> PushResult:
        verify_snapshot(snapshot)
        enforce_remote_privacy(
            snapshot, allow_plaintext_private=self.allow_plaintext_private
        )
        sid = snapshot.snapshot_id
        with tempfile.TemporaryDirectory(prefix="secondbrain-rclone-") as temp:
            temp_path = Path(temp)
            archive_path = temp_path / f"{sid}.tar"
            manifest_path = temp_path / f"{sid}.manifest.json"
            archive_path.write_bytes(snapshot.archive)
            manifest_path.write_bytes(snapshot.manifest.to_bytes())
            for local, suffix in (
                (archive_path, ".tar"),
                (manifest_path, ".manifest.json"),
            ):
                self._run(
                    [
                        "copyto",
                        "--checksum",
                        "--immutable",
                        str(local),
                        self._remote_path(f"{sid}{suffix}"),
                    ]
                )
        # rclone intentionally does not need a preflight read, so it cannot
        # distinguish a transferred object from an identical no-op.
        return PushResult(sid, self.name, None)

    def list(self) -> list[RemoteEntry]:
        raw = self._run(
            ["lsjson", "--files-only", "--recursive", self.remote]
        )
        try:
            items = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BackendError(f"rclone returned invalid lsjson output: {exc}") from exc
        manifests: dict[str, str | None] = {}
        archives: set[str] = set()
        for item in items:
            name = PurePosixPath(str(item.get("Path", ""))).name
            if name.endswith(".manifest.json"):
                sid = name[: -len(".manifest.json")].lower()
                if _HASH_RE.fullmatch(sid):
                    manifests[sid] = item.get("ModTime")
            elif name.endswith(".tar"):
                sid = name[: -len(".tar")].lower()
                if _HASH_RE.fullmatch(sid):
                    archives.add(sid)

        orphan_ids = sorted(archives - set(manifests))
        if orphan_ids:
            raise SnapshotIntegrityError(
                f"rclone snapshot archive has no manifest: {orphan_ids[0]}"
            )

        entries = []
        for sid, stored_at in manifests.items():
            if sid not in archives:
                raise SnapshotIntegrityError(
                    f"rclone snapshot {sid} has a manifest but no archive"
                )
            try:
                manifest = Manifest.from_bytes(
                    self._run(["cat", self._remote_path(f"{sid}.manifest.json")])
                )
            except SnapshotIntegrityError:
                raise
            except (BackendError, UnicodeDecodeError, ValueError) as exc:
                raise SnapshotIntegrityError(
                    f"rclone snapshot {sid} has an unreadable manifest: {exc}"
                ) from exc
            if manifest.snapshot_id != sid:
                raise SnapshotIntegrityError(
                    f"rclone manifest id does not match filename for {sid}"
                )
            entries.append(RemoteEntry(sid, self.name, None, stored_at))
        return sorted(
            entries,
            key=lambda entry: (entry.stored_at or "", entry.snapshot_id),
            reverse=True,
        )

    def pull(self, snapshot_id: str | None = None) -> Snapshot:
        if snapshot_id is None:
            entries = self.list()
            if not entries:
                raise SnapshotNotFoundError(f"no snapshots at rclone remote {self.remote}")
            snapshot_id = entries[0].snapshot_id
        sid = _validate_snapshot_id(snapshot_id)
        manifest_bytes = self._run(["cat", self._remote_path(f"{sid}.manifest.json")])
        archive = self._run(["cat", self._remote_path(f"{sid}.tar")])
        snapshot = Snapshot(archive, Manifest.from_bytes(manifest_bytes))
        if snapshot.snapshot_id != sid:
            raise SnapshotIntegrityError("requested snapshot id does not match rclone manifest")
        return verify_snapshot(snapshot)


def _quote_table_name(table: str) -> str:
    parts = table.split(".")
    if not 1 <= len(parts) <= 2 or any(not _IDENTIFIER_RE.fullmatch(part) for part in parts):
        raise MissingConfigurationError(
            "Postgres table must be an identifier or schema.identifier (letters, digits, underscore)"
        )
    return ".".join(f'"{part}"' for part in parts)


class PostgresBackend:
    """Opaque snapshot rows in Postgres (including Supabase Postgres).

    Both the tar and canonical manifest are BYTEA values in the same row and are
    inserted in one transaction.  ``psycopg`` is imported only on first use.
    """

    name = "postgres"

    def __init__(
        self,
        dsn: str | None = None,
        *,
        dsn_env: str = "SECONDBRAIN_POSTGRES_DSN",
        table: str = "secondbrain_snapshots",
        allow_plaintext_private: bool = False,
    ):
        self._direct_dsn = dsn
        self.dsn_env = dsn_env
        self.table = table
        self._quoted_table = _quote_table_name(table)
        self.allow_plaintext_private = bool(allow_plaintext_private)

    def _dsn(self) -> str:
        dsn = self._direct_dsn or os.environ.get(self.dsn_env)
        if not dsn:
            raise MissingConfigurationError(
                f"Postgres DSN is not configured; set environment variable {self.dsn_env}"
            )
        return dsn

    def _connect(self):
        try:
            psycopg = importlib.import_module("psycopg")
        except (ImportError, ModuleNotFoundError) as exc:
            raise MissingDependencyError(
                "Postgres snapshots need psycopg; install with `pip install psycopg[binary]`"
            ) from exc
        dsn = self._dsn()
        try:
            return psycopg.connect(dsn)
        except Exception as exc:
            raise BackendError(
                f"Postgres connection failed; verify the DSN in {self.dsn_env}"
            ) from exc

    def _ensure_schema(self, cursor) -> None:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._quoted_table} (
                snapshot_id TEXT PRIMARY KEY,
                manifest BYTEA NOT NULL,
                snapshot BYTEA NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def push(self, snapshot: Snapshot) -> PushResult:
        verify_snapshot(snapshot)
        enforce_remote_privacy(
            snapshot, allow_plaintext_private=self.allow_plaintext_private
        )
        sid = snapshot.snapshot_id
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._ensure_schema(cursor)
                cursor.execute(
                    f"""
                    INSERT INTO {self._quoted_table} (snapshot_id, manifest, snapshot)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (snapshot_id) DO NOTHING
                    RETURNING snapshot_id
                    """,
                    (sid, snapshot.manifest.to_bytes(), snapshot.archive),
                )
                created = cursor.fetchone() is not None
                if not created:
                    cursor.execute(
                        f"SELECT manifest, snapshot FROM {self._quoted_table} "
                        "WHERE snapshot_id = %s",
                        (sid,),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise BackendError("Postgres conflict row disappeared during transaction")
                    existing = Snapshot(bytes(row[1]), Manifest.from_bytes(bytes(row[0])))
                    if (
                        existing.manifest.to_bytes() != snapshot.manifest.to_bytes()
                        or existing.archive != snapshot.archive
                    ):
                        raise SnapshotConflictError(
                            f"Postgres snapshot id {sid} maps to different bytes"
                        )
                    verify_snapshot(existing)
        return PushResult(sid, self.name, created)

    def list(self) -> list[RemoteEntry]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._ensure_schema(cursor)
                cursor.execute(
                    f"SELECT snapshot_id, manifest, snapshot, created_at "
                    f"FROM {self._quoted_table} "
                    "ORDER BY created_at DESC, snapshot_id DESC"
                )
                rows = cursor.fetchall()
        entries = []
        for sid, manifest_bytes, archive, created_at in rows:
            try:
                snapshot = Snapshot(bytes(archive), Manifest.from_bytes(bytes(manifest_bytes)))
                if snapshot.snapshot_id != str(sid):
                    raise SnapshotIntegrityError(
                        f"Postgres row id does not match stored manifest: {sid}"
                    )
                verify_snapshot(snapshot)
            except StorageError:
                raise
            except (TypeError, ValueError, OSError) as exc:
                raise SnapshotIntegrityError(
                    f"Postgres snapshot {sid} is unreadable: {exc}"
                ) from exc
            stored_at = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
            entries.append(RemoteEntry(str(sid), self.name, len(snapshot.archive), stored_at))
        return entries

    def pull(self, snapshot_id: str | None = None) -> Snapshot:
        sid = _validate_snapshot_id(snapshot_id) if snapshot_id is not None else None
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._ensure_schema(cursor)
                if sid is None:
                    cursor.execute(
                        f"SELECT snapshot_id, manifest, snapshot FROM {self._quoted_table} "
                        "ORDER BY created_at DESC, snapshot_id DESC LIMIT 1"
                    )
                else:
                    cursor.execute(
                        f"SELECT snapshot_id, manifest, snapshot FROM {self._quoted_table} "
                        "WHERE snapshot_id = %s",
                        (sid,),
                    )
                row = cursor.fetchone()
        if row is None:
            raise SnapshotNotFoundError(
                f"snapshot not found in Postgres: {sid or '(latest)'}"
            )
        stored_id, manifest_bytes, archive = row
        snapshot = Snapshot(bytes(archive), Manifest.from_bytes(bytes(manifest_bytes)))
        if snapshot.snapshot_id != str(stored_id):
            raise SnapshotIntegrityError("Postgres row id does not match stored manifest")
        return verify_snapshot(snapshot)


__all__ = [
    "Backend",
    "BackendError",
    "DestinationNotEmptyError",
    "LocalBackend",
    "Manifest",
    "ManifestEntry",
    "MissingConfigurationError",
    "MissingDependencyError",
    "PlaintextPrivateError",
    "PostgresBackend",
    "PushResult",
    "RemoteEntry",
    "RestoreError",
    "RestoreResult",
    "RcloneBackend",
    "Snapshot",
    "SnapshotChangedError",
    "SnapshotConflictError",
    "SnapshotIntegrityError",
    "SnapshotNotFoundError",
    "StorageError",
    "UnsafeArchiveError",
    "create_snapshot",
    "enforce_remote_privacy",
    "find_plaintext_private_concepts",
    "restore_snapshot",
    "verify_snapshot",
]
