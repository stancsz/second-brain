#!/usr/bin/env python3
"""CLI for immutable, verified OKF Bundle snapshots.

Examples:
  python scripts/storage_cli.py push --backend local --store D:\\brain-backups --bundle D:\\brain\\okf
  python scripts/storage_cli.py list --backend local --store D:\\brain-backups
  python scripts/storage_cli.py pull --backend local --store D:\\brain-backups --dest D:\\restored-okf
"""
from __future__ import annotations

import argparse
import json
import sys

from storage import (
    LocalBackend,
    MissingConfigurationError,
    PostgresBackend,
    RcloneBackend,
    StorageError,
    create_snapshot,
    restore_snapshot,
)


try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


def _add_backend_arguments(
    parser: argparse.ArgumentParser, *, include_plaintext_override: bool = False
) -> None:
    parser.add_argument("--backend", choices=("local", "rclone", "postgres"), required=True)
    parser.add_argument("--store", help="directory used by the local backend")
    parser.add_argument("--remote", help="configured rclone remote path, e.g. s3:bucket/brain")
    parser.add_argument("--rclone", default="rclone", help="rclone executable name or path")
    parser.add_argument(
        "--dsn-env",
        default="SECONDBRAIN_POSTGRES_DSN",
        help="environment variable containing the Postgres/Supabase DSN",
    )
    parser.add_argument(
        "--table",
        default="secondbrain_snapshots",
        help="Postgres table or schema.table",
    )
    if include_plaintext_override:
        parser.add_argument(
            "--allow-plaintext-private",
            action="store_true",
            help=(
                "DANGEROUS: explicitly permit unencrypted private/psych Concepts "
                "on a remote backend"
            ),
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secondbrain-storage",
        description="Push, list, and safely restore immutable OKF Bundle snapshots.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    commands = parser.add_subparsers(dest="command", required=True)

    push = commands.add_parser("push", help="snapshot a Bundle and push it")
    _add_backend_arguments(push, include_plaintext_override=True)
    push.add_argument("--bundle", required=True, help="OKF Bundle directory to snapshot")

    listing = commands.add_parser("list", help="list stored snapshots")
    _add_backend_arguments(listing)

    pull = commands.add_parser("pull", help="pull and restore a verified snapshot")
    _add_backend_arguments(pull)
    pull.add_argument("--dest", required=True, help="destination OKF Bundle directory")
    pull.add_argument("--snapshot", help="snapshot id; defaults to the backend's latest")
    pull.add_argument(
        "--force",
        action="store_true",
        help="rename an existing destination to a recoverable sibling before restore",
    )
    return parser


def _backend(args):
    allow_plaintext_private = bool(getattr(args, "allow_plaintext_private", False))
    if args.backend == "local":
        if not args.store:
            raise MissingConfigurationError("local backend requires --store")
        return LocalBackend(args.store)
    if args.backend == "rclone":
        if not args.remote:
            raise MissingConfigurationError("rclone backend requires --remote")
        return RcloneBackend(
            args.remote,
            executable=args.rclone,
            allow_plaintext_private=allow_plaintext_private,
        )
    return PostgresBackend(
        dsn_env=args.dsn_env,
        table=args.table,
        allow_plaintext_private=allow_plaintext_private,
    )


def _print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        backend = _backend(args)
        if args.command == "push":
            snapshot = create_snapshot(args.bundle)
            if (
                args.backend in {"rclone", "postgres"}
                and args.allow_plaintext_private
            ):
                print(
                    "warning: explicit plaintext-private remote upload override enabled",
                    file=sys.stderr,
                )
            result = backend.push(snapshot)
            payload = result.to_dict()
            payload["archive_size"] = snapshot.manifest.archive_size
            payload["files"] = len(snapshot.manifest.files)
            if args.json:
                _print_json(payload)
            else:
                status = "stored" if result.created is not False else "already stored"
                print(
                    f"{status}: {result.snapshot_id} "
                    f"({len(snapshot.manifest.files)} files, {snapshot.manifest.archive_size} bytes)"
                )
            return 0

        if args.command == "list":
            entries = backend.list()
            if args.json:
                _print_json([entry.to_dict() for entry in entries])
            elif not entries:
                print("no snapshots")
            else:
                for entry in entries:
                    size = str(entry.size) if entry.size is not None else "unknown-size"
                    when = entry.stored_at or "unknown-time"
                    print(f"{entry.snapshot_id}  {size}  {when}")
            return 0

        snapshot = backend.pull(args.snapshot)
        result = restore_snapshot(snapshot, args.dest, force=args.force)
        if args.json:
            _print_json(result.to_dict())
        else:
            print(f"restored: {result.snapshot_id} -> {result.destination}")
            if result.backup:
                print(f"previous destination preserved at: {result.backup}")
        return 0
    except StorageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
