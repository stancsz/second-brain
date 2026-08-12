#!/usr/bin/env python3
"""Emit a host-neutral readiness matrix for the five supported agent hosts.

This checks the portable package and local MCP entry point. It deliberately
marks native host activation as a separate human gate rather than faking UI
coverage for proprietary applications.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


HOSTS = {
    "claude-code": {"skill_locations": ["~/.claude/skills/second-brain", ".claude/skills/second-brain"]},
    "codex": {"skill_locations": ["Agent Skills discovery", "agents/openai.yaml"]},
    "gemini-cli": {"skill_locations": ["~/.gemini/skills/second-brain", ".gemini/skills/second-brain"]},
    "opencode": {"skill_locations": ["~/.config/opencode/skills/second-brain", ".opencode/skills/second-brain", ".agents/skills/second-brain"]},
    "cline": {"skill_locations": ["~/.cline/skills/second-brain", ".cline/skills/second-brain"]},
}


def _mcp_ready(root: Path) -> bool:
    script = root / "scripts" / "brain_mcp.py"
    if not script.is_file():
        return False
    requests = (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            input="".join(json.dumps(item) + "\n" for item in requests),
            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=10,
            check=False,
        )
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        listing = next(item for item in responses if item.get("id") == 2)
        tools = {item.get("name") for item in listing["result"]["tools"]}
        return result.returncode == 0 and {"brain_add", "brain_search"} <= tools
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, StopIteration, TypeError):
        return False


def build_report(root: str | Path | None = None, host: str = "all") -> dict:
    package_root = Path(root or Path(__file__).resolve().parent.parent).resolve()
    selected = list(HOSTS) if host == "all" else [host]
    if any(item not in HOSTS for item in selected):
        raise ValueError(f"host must be one of: {', '.join(HOSTS)}")
    package_files = all(
        (package_root / relative).is_file()
        for relative in ("SKILL.md", "scripts/brain_cli.py", "scripts/brain_mcp.py")
    )
    mcp = _mcp_ready(package_root)
    rows = []
    for name in selected:
        rows.append({
            "host": name,
            "skill_locations": HOSTS[name]["skill_locations"],
            "package": "pass" if package_files else "fail",
            "mcp": "pass" if mcp else "fail",
            "native_handshake": "manual",
            "status": "package-ready" if package_files and mcp else "blocked",
        })
    return {
        "format": "secondbrain-host-matrix-v1",
        "scope": "portable package and local MCP only; native host launch remains manual",
        "hosts": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="content-free five-host readiness matrix")
    parser.add_argument("--host", choices=["all", *HOSTS], default="all")
    parser.add_argument("--root", help="repository or installed skill root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.root, args.host)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"second-brain host matrix: {report['format']}")
        for row in report["hosts"]:
            print(f"[{row['status']}] {row['host']} (native handshake: {row['native_handshake']})")
    return 0 if all(row["status"] == "package-ready" for row in report["hosts"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
