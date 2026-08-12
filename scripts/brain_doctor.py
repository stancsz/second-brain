#!/usr/bin/env python3
"""Emit a content-free local compatibility and pairing report.

The doctor is intentionally read-only.  It never opens a writable SQLite
connection, runs a mutation, starts a tool call, or prints note contents.
Use it after installing the skill or before attaching a sanitized report to a
host/provider compatibility issue.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402


REPORT_FORMAT = "secondbrain-doctor-v1"


def _check(check_id: str, status: str, detail: str) -> dict[str, str]:
    return {"id": check_id, "status": status, "detail": detail}


def _source(explicit: str | None, env_name: str, default: Path) -> str:
    if explicit is not None:
        return "explicit"
    if os.environ.get(env_name, "").strip():
        return "environment"
    return "default"


def _read_only_database_state(database: Path) -> dict[str, object]:
    """Compute the pairing projection without opening a writable brain."""
    uri = database.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        class ReadOnlyBrain:
            con = connection

        return store._database_state(ReadOnlyBrain())
    finally:
        connection.close()


def _mcp_check(script: Path) -> tuple[str, str]:
    requests = (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            input="".join(json.dumps(item) + "\n" for item in requests),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return "fail", f"MCP subprocess could not be checked ({type(exc).__name__})"
    if result.returncode != 0:
        return "fail", "MCP subprocess exited unsuccessfully"
    try:
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        initialize = next(item for item in responses if item.get("id") == 1)
        listed = next(item for item in responses if item.get("id") == 2)
        tools = {
            item.get("name")
            for item in listed.get("result", {}).get("tools", [])
            if isinstance(item, dict)
        }
        if "result" not in initialize or not {"brain_add", "brain_search"} <= tools:
            return "fail", "MCP initialize/tools-list contract is incomplete"
    except (ValueError, StopIteration, TypeError, AttributeError):
        return "fail", "MCP returned invalid protocol output"
    return "pass", "MCP initialize and tools/list expose the core brain tools"


def build_report(
    db: str | os.PathLike[str] | None = None,
    bundle: str | os.PathLike[str] | None = None,
) -> dict[str, object]:
    database = store.resolve_db_path(db)
    canonical = store.resolve_bundle_path(database, bundle)
    root = Path(__file__).resolve().parent.parent
    checks: list[dict[str, str]] = []

    checks.append(
        _check(
            "python",
            "pass" if sys.version_info >= (3, 10) else "fail",
            "Python 3.10 or newer" if sys.version_info >= (3, 10) else "Python 3.10 or newer is required",
        )
    )
    required_files = (root / "SKILL.md", root / "scripts" / "brain_cli.py")
    checks.append(
        _check(
            "skill_package",
            "pass" if all(path.is_file() for path in required_files) else "fail",
            "skill instructions and CLI are present"
            if all(path.is_file() for path in required_files)
            else "skill instructions or CLI is missing",
        )
    )
    mcp_script = root / "scripts" / "brain_mcp.py"
    if mcp_script.is_file():
        mcp_status, mcp_detail = _mcp_check(mcp_script)
        checks.append(_check("mcp_protocol", mcp_status, mcp_detail))
    else:
        checks.append(_check("mcp_protocol", "fail", "MCP server script is missing"))

    storage_files = (
        root / "scripts" / "storage.py",
        root / "scripts" / "storage_cli.py",
        root / "references" / "storage.md",
    )
    checks.append(
        _check(
            "storage_surface",
            "pass" if all(path.is_file() for path in storage_files) else "fail",
            "local, rclone, PostgreSQL/Supabase snapshot surfaces are present"
            if all(path.is_file() for path in storage_files)
            else "storage adapter or contract documentation is missing",
        )
    )

    host_matrix = root / "scripts" / "host_matrix.py"
    checks.append(
        _check(
            "host_matrix",
            "pass" if host_matrix.is_file() else "fail",
            "five-host package/MCP readiness report is present"
            if host_matrix.is_file()
            else "host readiness report is missing",
        )
    )

    checks.append(
        _check(
            "database_path",
            "pass" if database.is_file() else "warn",
            "working SQLite index is present" if database.is_file() else "working index is not initialized",
        )
    )
    checks.append(
        _check(
            "bundle_path",
            "pass" if canonical.is_dir() else "warn",
            "canonical Bundle is present" if canonical.is_dir() else "canonical Bundle is not initialized",
        )
    )

    marker_names = (store.DIRTY_MARKER, store.SYNC_MARKER)
    present_markers = [name for name in marker_names if (canonical / name).is_file()]
    checks.append(
        _check(
            "journals",
            "fail" if present_markers else "pass",
            "interrupted write/sync journal present: " + ", ".join(present_markers)
            if present_markers
            else "no interrupted write or sync journal is present",
        )
    )

    if database.is_file() and canonical.is_dir():
        try:
            state = store._read_pair_state(canonical)
            if state is None and store._bundle_has_concepts(canonical):
                checks.append(_check("pairing", "fail", "non-empty Bundle has no pair receipt"))
            elif state is None:
                checks.append(_check("pairing", "warn", "empty Bundle has no pair receipt yet"))
            else:
                actual_database = _read_only_database_state(database)
                actual_bundle = store._bundle_state_sha256(canonical)
                matches = (
                    state.get("database") == actual_database
                    and state.get("bundle_state_sha256") == actual_bundle
                )
                checks.append(
                    _check(
                        "pairing",
                        "pass" if matches else "fail",
                        "read-only database/Bundle receipt matches"
                        if matches
                        else "database/Bundle receipt does not match",
                    )
                )
        except (OSError, sqlite3.Error, store.CanonicalStoreError, ValueError, TypeError):
            checks.append(_check("pairing", "fail", "pair receipt or read-only projection is invalid"))
    elif database.is_file() or canonical.is_dir():
        checks.append(_check("pairing", "warn", "one side exists; explicit bootstrap or restore is required"))
    else:
        checks.append(_check("pairing", "warn", "brain is not initialized yet"))

    return {
        "format": REPORT_FORMAT,
        "status": "fail" if any(item["status"] == "fail" for item in checks) else (
            "warn" if any(item["status"] == "warn" for item in checks) else "pass"
        ),
        "paths": {
            "database": {"present": database.is_file(), "source": _source(db, "SECONDBRAIN_DB", store.DEFAULT_DB_PATH)},
            "bundle": {"present": canonical.is_dir(), "source": _source(bundle, "SECONDBRAIN_BUNDLE", store.DEFAULT_BUNDLE_PATH)},
        },
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="content-free second-brain compatibility and pairing report")
    parser.add_argument("--db", help="working SQLite index (read-only inspection)")
    parser.add_argument("--bundle", help="canonical OKF Bundle (read-only inspection)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="treat warnings as a failed report")
    args = parser.parse_args(argv)
    report = build_report(args.db, args.bundle)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"second-brain doctor: {report['status']}")
        for item in report["checks"]:
            print(f"[{item['status'].upper()}] {item['id']}: {item['detail']}")
    if report["status"] == "fail":
        return 2
    if args.strict and report["status"] == "warn":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
