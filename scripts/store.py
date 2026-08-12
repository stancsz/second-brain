#!/usr/bin/env python3
"""Canonical local store helpers.

The OKF Markdown Bundle is authoritative. SQLite remains the fast working index,
but every successful user-facing mutation must flush the current database into
its paired Bundle before the operation is reported as durable.
"""

from __future__ import annotations

import os
import json
import hashlib
import threading
import time
from contextlib import contextmanager
from pathlib import Path


DEFAULT_DB_PATH = Path.home() / ".secondbrain" / "brain.db"
DEFAULT_BUNDLE_PATH = Path.home() / ".secondbrain" / "okf"
DIRTY_MARKER = ".secondbrain-dirty"
SYNC_MARKER = ".secondbrain-sync"
PAIR_STATE = ".secondbrain-state.json"
PAIR_STATE_FORMAT = "secondbrain-pair-state-v1"
LOCK_TIMEOUT_SECONDS = 30.0
_LOCK_STATE = threading.local()


class CanonicalStoreError(RuntimeError):
    """The paired SQLite/Bundle state cannot be opened or reconciled safely."""


class BundlePairMismatch(CanonicalStoreError):
    """The bytes written/read from a Bundle do not represent the working DB."""


def _clean_env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def resolve_db_path(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the working SQLite index without creating it."""
    value = explicit if explicit is not None else _clean_env("SECONDBRAIN_DB")
    return Path(value).expanduser() if value is not None else DEFAULT_DB_PATH


def resolve_bundle_path(
    db_path: str | os.PathLike[str],
    explicit: str | os.PathLike[str] | None = None,
) -> Path:
    """Resolve the Bundle paired with ``db_path``.

    The default brain uses ``~/.secondbrain/okf``. A custom database gets an
    isolated ``<db-stem>.okf`` sibling unless ``SECONDBRAIN_BUNDLE`` or an
    explicit path selects a different Bundle. This prevents tests and alternate
    brains from silently overwriting the default user's canonical files.
    """
    value = explicit if explicit is not None else _clean_env("SECONDBRAIN_BUNDLE")
    if value is not None:
        return Path(value).expanduser()

    db = Path(db_path).expanduser()
    try:
        is_default = db.resolve(strict=False) == DEFAULT_DB_PATH.resolve(strict=False)
    except OSError:
        is_default = db.absolute() == DEFAULT_DB_PATH.absolute()
    if is_default:
        return DEFAULT_BUNDLE_PATH
    return Path(str(db) + ".okf")


def open_brain(
    db_path: str | os.PathLike[str] | None = None,
    bundle_path: str | os.PathLike[str] | None = None,
):
    """Open the working index, rebuilding it after a local wipe when possible."""
    from brain import SecondBrain

    database = resolve_db_path(db_path)
    canonical = resolve_bundle_path(database, bundle_path)
    if database.exists():
        brain = SecondBrain(database)
        try:
            with bundle_lock(canonical):
                if _sync_marker_path(canonical).exists():
                    # A sync marker explicitly transfers authority to Markdown.
                    # Rebuild the disposable projection on the next open; this
                    # makes a crash between rebuild/receipt cleanup recoverable
                    # without allowing stale SQLite to overwrite pulled files.
                    brain.close()
                    import bundle

                    rebuilt = bundle.rebuild(canonical, database)
                    finish_sync(rebuilt, canonical)
                    return rebuilt
                # The dirty marker is the durable record of an interrupted
                # write-through. Recover it before comparing the old receipt.
                if _marker_path(canonical).exists():
                    _flush_locked(brain, canonical)
                state = _read_pair_state(canonical)
                if (
                    canonical.is_dir()
                    and state is None
                    and _bundle_has_concepts(canonical)
                ):
                    raise CanonicalStoreError(
                        "both the working database and an unpaired Bundle contain data; "
                        "refusing to guess which is newer. Back up both, then rebuild or "
                        "export explicitly."
                    )
                if state is not None and state != _pair_state(brain, canonical):
                    raise CanonicalStoreError(
                        "the working database and canonical Bundle are out of sync; "
                        "refusing to overwrite either. Restore the paired database or "
                        "rebuild it from a verified Bundle."
                    )
        except BaseException:
            brain.close()
            raise
        return brain
    if canonical.is_dir() and _bundle_has_concepts(canonical):
        with bundle_lock(canonical):
            if _sync_marker_path(canonical).exists():
                import bundle

                rebuilt = bundle.rebuild(canonical, database)
                finish_sync(rebuilt, canonical)
                return rebuilt
            if _marker_path(canonical).exists():
                raise CanonicalStoreError(
                    "the working database is missing and its Bundle has an incomplete "
                    "export marker; restore a verified snapshot or the paired database"
                )
            # Reject unknown state formats before replacing them. Missing state
            # is accepted for legacy Bundles and regenerated after rebuild.
            _read_pair_state(canonical)
            import bundle

            brain = bundle.rebuild(canonical, database)
            _write_pair_state(brain, canonical)
        return brain
    return SecondBrain(database)


def flush_bundle(brain, bundle_path: str | os.PathLike[str] | None = None) -> dict:
    """Incrementally materialize a committed brain into its canonical Bundle.

    Importing ``bundle`` lazily keeps the data layer free of a circular import:
    ``bundle.py`` itself imports :class:`SecondBrain` for rebuild operations.
    """
    import bundle

    destination = resolve_bundle_path(brain.db_path, bundle_path)
    return bundle.export(brain, destination)


@contextmanager
def bundle_lock(bundle_path: Path, timeout: float = LOCK_TIMEOUT_SECONDS):
    """Serialize writers to one Bundle; OS locks are released after a crash."""
    bundle_path = Path(bundle_path)
    lock_path = bundle_path.with_name(bundle_path.name + ".lock")
    lock_key = str(lock_path.resolve(strict=False)).casefold()
    held = getattr(_LOCK_STATE, "held", set())
    if lock_key in held:
        yield
        return
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    started = time.monotonic()
    acquired = False
    try:
        while not acquired:
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except (BlockingIOError, OSError):
                if time.monotonic() - started >= timeout:
                    raise TimeoutError(
                        f"timed out waiting for canonical Bundle writer: {bundle_path}"
                    )
                time.sleep(0.05)
        _LOCK_STATE.held = held | {lock_key}
        yield
    finally:
        if acquired:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        _LOCK_STATE.held = held
        handle.close()


def _marker_path(bundle_path: Path) -> Path:
    return bundle_path / DIRTY_MARKER


def _sync_marker_path(bundle_path: Path) -> Path:
    return bundle_path / SYNC_MARKER


def _state_path(bundle_path: Path) -> Path:
    return bundle_path / PAIR_STATE


def _bundle_has_concepts(bundle_path: Path) -> bool:
    """Return whether a Bundle contains managed Concept Markdown."""
    for path in bundle_path.rglob("*.md"):
        relative = path.relative_to(bundle_path)
        posix = relative.as_posix()
        if (
            ".git" not in relative.parts
            and path.name not in {"index.md", "log.md"}
            and not posix.endswith(".conflict.md")
        ):
            return True
    return False


def _hash_rows(digest, table: str, rows: list[dict[str, object]]) -> None:
    digest.update(table.encode("ascii") + b"\0")
    for row in rows:
        encoded = json.dumps(
            row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)


def _database_state(brain) -> dict[str, object]:
    """Hash the rebuild-stable meaning of the SQLite projection.

    Projection-only identifiers and timestamps (tag/relation/pending UUIDs and
    ``created_at``) are intentionally excluded because a Bundle rebuild mints
    them again. Everything represented by OKF Markdown is normalized and
    included, so this digest remains stable across devices while still catching
    graph, tag, content, metadata, and soft-delete drift.
    """
    digest = hashlib.sha256()
    metadata_keys = {
        "okf_type",
        "description",
        "sb_subject",
        "sb_valid_from",
        "sb_valid_to",
        "sb_supersedes",
        "sb_affect",
    }
    concepts = []
    for row in brain.con.execute(
        "SELECT id, title, content, collection, sources, updated_at, "
        "deleted_at, metadata FROM concepts ORDER BY id"
    ).fetchall():
        try:
            sources = json.loads(row["sources"] or "[]")
        except (TypeError, json.JSONDecodeError):
            sources = row["sources"]
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {"_invalid_json": row["metadata"]}
        if not isinstance(metadata, dict):
            metadata = {"_invalid_value": metadata}
        concepts.append(
            {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "collection": row["collection"],
                "sources": sources,
                "updated_at": row["updated_at"],
                "deleted_at": row["deleted_at"],
                "metadata": {
                    key: metadata[key]
                    for key in sorted(metadata_keys)
                    if key in metadata
                },
            }
        )

    concept_tags = [
        dict(row)
        for row in brain.con.execute(
            "SELECT ct.concept_id, t.name FROM concept_tags ct "
            "JOIN tags t ON t.id=ct.tag_id ORDER BY ct.concept_id, t.name"
        ).fetchall()
    ]
    # Wikilink relations and pending links are derived from Concept content on
    # every rebuild. Hash only authored/manual edges; hashing derived row timing
    # would make soft-deleted links device-dependent.
    relations = [
        dict(row)
        for row in brain.con.execute(
            "SELECT from_id, to_id, relation_type, strength, source "
            "FROM relations WHERE source='manual' "
            "ORDER BY from_id, to_id, source"
        ).fetchall()
    ]
    logical_tables = {
        "concepts": concepts,
        "concept_tags": concept_tags,
        "relations": relations,
    }
    for table, rows in logical_tables.items():
        _hash_rows(digest, table, rows)
    counts = {table: len(rows) for table, rows in logical_tables.items()}
    return {"state_sha256": digest.hexdigest(), "counts": counts}


def _managed_bundle_files(bundle_path: Path) -> list[Path]:
    files = []
    for path in bundle_path.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(bundle_path)
        posix = relative.as_posix()
        if (
            ".git" in relative.parts
            or posix.endswith(".conflict.md")
            or path.name in {DIRTY_MARKER, SYNC_MARKER, PAIR_STATE, ".gitignore"}
            or path.name.startswith(DIRTY_MARKER + ".tmp-")
            or path.name.startswith(SYNC_MARKER + ".tmp-")
            or path.name.startswith(PAIR_STATE + ".tmp-")
            or path.name.startswith(".") and ".tmp-" in path.name
        ):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(bundle_path).as_posix())


def _bundle_state_sha256(bundle_path: Path) -> str:
    digest = hashlib.sha256()
    for path in _managed_bundle_files(bundle_path):
        relative = path.relative_to(bundle_path).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _pair_state(brain, bundle_path: Path) -> dict[str, object]:
    return {
        "format": PAIR_STATE_FORMAT,
        "database": _database_state(brain),
        "bundle_state_sha256": _bundle_state_sha256(bundle_path),
    }


def _validate_existing_pair(brain, bundle_path: Path) -> None:
    """Refuse a stale writer after it acquires the Bundle lock."""
    state = _read_pair_state(bundle_path)
    if state is None and _bundle_has_concepts(bundle_path):
        raise CanonicalStoreError(
            "the canonical Bundle contains data but has no valid pair-state; "
            "refusing a stale or unpaired write. Rebuild explicitly first."
        )
    if state is not None and state != _pair_state(brain, bundle_path):
        raise CanonicalStoreError(
            "the working database or canonical Bundle changed since it was "
            "opened; refusing a stale write. Reopen or rebuild before retrying."
        )


def _write_pair_state(brain, bundle_path: Path) -> None:
    path = _state_path(bundle_path)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(_pair_state(brain, bundle_path), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _verify_bundle_projection(brain, bundle_path: Path) -> None:
    """Round-trip the just-written Bundle before blessing its pair-state.

    This catches a non-cooperating Markdown/Obsidian writer that changes a file
    between export and receipt creation. The marker remains set on failure, so
    recovery cannot silently bless a mixed generation.
    """
    import bundle

    temporary = bundle_path.with_name(
        f".{bundle_path.name}.verify-{os.getpid()}-{time.time_ns()}.db"
    )
    rebuilt = None
    try:
        rebuilt = bundle.rebuild(bundle_path, temporary)
        expected = _database_state(brain)
        actual = _database_state(rebuilt)
        if expected != actual:
            raise BundlePairMismatch(
                "canonical Bundle changed during export; refusing to bless a mixed "
                "database/Markdown generation"
            )
    finally:
        if rebuilt is not None:
            rebuilt.close()
        for suffix in ("", "-wal", "-shm", "-journal"):
            try:
                Path(str(temporary) + suffix).unlink()
            except FileNotFoundError:
                pass


def _read_pair_state(bundle_path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(_state_path(bundle_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    if value.get("format") != PAIR_STATE_FORMAT:
        raise CanonicalStoreError(
            f"unsupported or corrupt canonical pair-state in {_state_path(bundle_path)}"
        )
    if not isinstance(value.get("database"), dict) or not isinstance(
        value.get("bundle_state_sha256"), str
    ):
        raise CanonicalStoreError(
            f"unsupported or corrupt canonical pair-state in {_state_path(bundle_path)}"
        )
    return value


def _write_dirty_marker(bundle_path: Path) -> None:
    bundle_path.mkdir(parents=True, exist_ok=True)
    marker = _marker_path(bundle_path)
    temporary = marker.with_name(marker.name + f".tmp-{os.getpid()}")
    temporary.write_text("canonical export incomplete; retry from the paired database\n", encoding="utf-8")
    os.replace(temporary, marker)


def _clear_dirty_marker(bundle_path: Path) -> None:
    marker = _marker_path(bundle_path)
    try:
        marker.unlink()
    except FileNotFoundError:
        pass


def begin_sync(bundle_path: str | os.PathLike[str]) -> None:
    """Persist that Git may make the Bundle newer than SQLite."""
    bundle_path = Path(bundle_path)
    bundle_path.mkdir(parents=True, exist_ok=True)
    marker = _sync_marker_path(bundle_path)
    temporary = marker.with_name(marker.name + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps({"format": "secondbrain-sync-v1", "authority": "bundle"}) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, marker)


def sync_pending(bundle_path: str | os.PathLike[str]) -> bool:
    return _sync_marker_path(Path(bundle_path)).exists()


def finish_sync(brain, bundle_path: str | os.PathLike[str]) -> None:
    """Pair a validated post-pull projection and clear the sync journal."""
    bundle_path = Path(bundle_path)
    _write_pair_state(brain, bundle_path)
    try:
        _sync_marker_path(bundle_path).unlink()
    except FileNotFoundError:
        pass


def _export_verified(brain, bundle_path: Path) -> dict:
    result = flush_bundle(brain, bundle_path)
    _verify_bundle_projection(brain, bundle_path)
    return result


def _flush_locked(brain, bundle_path: Path) -> dict:
    result = _export_verified(brain, bundle_path)
    _write_pair_state(brain, bundle_path)
    _clear_dirty_marker(bundle_path)
    return result


def recover_if_dirty(brain, bundle_path: str | os.PathLike[str] | None = None) -> bool:
    """Finish an interrupted write-through before allowing another operation."""
    destination = resolve_bundle_path(brain.db_path, bundle_path)
    if _sync_marker_path(destination).exists():
        raise CanonicalStoreError(
            "the Bundle is authoritative after an interrupted Git sync; reopen "
            "through store.open_brain so SQLite is rebuilt instead of exported"
        )
    if not _marker_path(destination).exists():
        return False
    with bundle_lock(destination):
        if _marker_path(destination).exists():
            _flush_locked(brain, destination)
            return True
    return False


@contextmanager
def canonical_mutation(brain, bundle_path: str | os.PathLike[str] | None = None):
    """Make one SQLite mutation durable, serialized, and recoverable.

    The marker is written before the caller mutates SQLite. A successful exit
    exports the committed database and removes the marker. If the process or
    export fails after the database commit, the marker remains: snapshots refuse
    that Bundle and the next CLI/MCP operation retries the export. An exception
    before commit is rolled back and reconciled to the unchanged database.
    """
    destination = resolve_bundle_path(brain.db_path, bundle_path)
    with bundle_lock(destination):
        previous_defer = getattr(brain, "_defer_commits", False)
        if previous_defer:
            raise CanonicalStoreError("nested canonical mutations are not supported")
        owns_dirty_marker = False
        # A fail-closed pairing check must happen outside the rollback/reconcile
        # block. If it refuses a manually edited Bundle, never overwrite that
        # edit while handling the refusal.
        if _sync_marker_path(destination).exists():
            raise CanonicalStoreError(
                "an interrupted Git sync must finish before another mutation"
            )
        if _marker_path(destination).exists():
            _flush_locked(brain, destination)
        elif destination.exists() and any(destination.iterdir()):
            _validate_existing_pair(brain, destination)
        try:
            _write_dirty_marker(destination)
            owns_dirty_marker = True
            brain._defer_commits = True
            yield
            result = _export_verified(brain, destination)
            brain.con.commit()
            _write_pair_state(brain, destination)
            _clear_dirty_marker(destination)
            return result
        except CanonicalStoreError:
            brain.con.rollback()
            raise
        except BaseException:
            brain.con.rollback()
            if owns_dirty_marker:
                try:
                    _flush_locked(brain, destination)
                except Exception:
                    # Leave the marker so a stale Bundle cannot be snapped.
                    pass
            raise
        finally:
            brain._defer_commits = previous_defer


def replace_canonical(brain, bundle_path: str | os.PathLike[str] | None = None) -> dict:
    """Replace a Bundle after an intentional database swap (for activation)."""
    destination = resolve_bundle_path(brain.db_path, bundle_path)
    with bundle_lock(destination):
        _write_dirty_marker(destination)
        return _flush_locked(brain, destination)


@contextmanager
def canonical_replacement_guard(
    db_path: str | os.PathLike[str],
    bundle_path: str | os.PathLike[str] | None = None,
):
    """Mark and lock a Bundle before replacing its working database.

    The caller must finish with :func:`replace_canonical`. If it crashes or
    raises first, the marker remains so snapshots are refused and the next open
    can recover from whichever complete database occupies ``db_path``.
    """
    destination = resolve_bundle_path(db_path, bundle_path)
    with bundle_lock(destination):
        _write_dirty_marker(destination)
        yield destination
