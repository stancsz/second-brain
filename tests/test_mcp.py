#!/usr/bin/env python3
"""Black-box JSON-RPC tests for the stdio MCP server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "scripts" / "brain_mcp.py"
CLI = ROOT / "scripts" / "brain_cli.py"


class TestMCPServer(unittest.TestCase):
    def test_initialize_list_add_and_search_in_isolated_home(self):
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "second-brain-test", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "brain_add",
                    "arguments": {
                        "title": "MCP isolation canary",
                        "content": "mcpisolatedcanary durable knowledge \u77e5\u8bc6",
                        "collection": "Tests",
                        "tags": ["mcp", "isolation"],
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "brain_search",
                    "arguments": {"query": "mcpisolatedcanary", "limit": 5},
                },
            },
        ]
        wire_input = "".join(json.dumps(request) + "\n" for request in requests)

        with tempfile.TemporaryDirectory() as isolated_home:
            env = os.environ.copy()
            env.update(
                {
                    "HOME": isolated_home,
                    "USERPROFILE": isolated_home,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONIOENCODING": "utf-8",
                }
            )
            result = subprocess.run(
                [sys.executable, str(SERVER)],
                input=wire_input,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(
                (Path(isolated_home) / ".secondbrain" / "brain.db").is_file(),
                "MCP test did not create its database under the isolated home",
            )

        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 4, result.stdout)
        responses = {response["id"]: response for response in map(json.loads, lines)}

        initialized = responses[1]["result"]
        self.assertEqual(initialized["protocolVersion"], "2024-11-05")
        self.assertEqual(initialized["serverInfo"]["name"], "second-brain")
        self.assertIn("tools", initialized["capabilities"])

        listed_tools = responses[2]["result"]["tools"]
        tool_names = {tool["name"] for tool in listed_tools}
        self.assertIn("brain_add", tool_names)
        self.assertIn("brain_search", tool_names)
        for tool in listed_tools:
            self.assertEqual(tool["inputSchema"]["type"], "object")

        add_result = responses[3]["result"]
        self.assertNotIn("isError", add_result)
        added = json.loads(add_result["content"][0]["text"])
        self.assertEqual(added["title"], "MCP isolation canary")
        self.assertTrue(added["id"])

        search_result = responses[4]["result"]
        self.assertNotIn("isError", search_result)
        matches = json.loads(search_result["content"][0]["text"])
        self.assertTrue(
            any(item["id"] == added["id"] for item in matches),
            matches,
        )

        self.assertEqual(result.stdout.count("\"jsonrpc\""), 4)
        self.assertIn("starting (stdio transport)", result.stderr)
        self.assertIn("stdin closed, exiting", result.stderr)

    def test_long_lived_server_reopens_after_external_cli_write(self):
        with tempfile.TemporaryDirectory() as isolated_home:
            env = os.environ.copy()
            env.update({
                "HOME": isolated_home,
                "USERPROFILE": isolated_home,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
            })
            proc = subprocess.Popen(
                [sys.executable, str(SERVER)], cwd=ROOT, env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8",
            )
            try:
                proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1,
                                             "method": "initialize", "params": {}}) + "\n")
                proc.stdin.flush()
                self.assertEqual(json.loads(proc.stdout.readline())["id"], 1)

                external = subprocess.run(
                    [sys.executable, str(CLI), "add", "External", "written by CLI"],
                    cwd=ROOT, env=env, capture_output=True, text=True,
                    encoding="utf-8", timeout=30, check=False,
                )
                self.assertEqual(external.returncode, 0, external.stderr)

                proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2,
                                             "method": "tools/call", "params": {
                                                 "name": "brain_search",
                                                 "arguments": {"query": "written by CLI"},
                                             }}) + "\n")
                proc.stdin.flush()
                response = json.loads(proc.stdout.readline())
                self.assertNotIn("isError", response["result"])
                rows = json.loads(response["result"]["content"][0]["text"])
                self.assertTrue(any(row["title"] == "External" for row in rows))
            finally:
                proc.stdin.close()
                proc.wait(timeout=30)
                proc.stdout.close()
                proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
