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
    def test_recall_tools_over_stdio_with_synthetic_metadata(self):
        with tempfile.TemporaryDirectory() as isolated_home:
            env = os.environ.copy()
            env.update({
                "HOME": isolated_home,
                "USERPROFILE": isolated_home,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
            })

            def seed(title, affect, subject, valid_from, valid_to=None):
                command = [sys.executable, str(CLI), "add", title, "synthetic recall fixture",
                           "--subject", subject, "--affect", json.dumps(affect),
                           "--valid-from", valid_from]
                if valid_to:
                    command.extend(["--valid-to", valid_to])
                seeded = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                        text=True, encoding="utf-8", timeout=30, check=False)
                self.assertEqual(seeded.returncode, 0, seeded.stderr + seeded.stdout)

            seed("Affect boundary one", {"emotion": "joy", "valence": 0.2,
                 "arousal": 0.4, "intensity": 0.7}, "/people/alex.md", "2024-01-01",
                 "2024-12-31")
            seed("Affect boundary two", {"emotion": "JOY", "valence": 0.8,
                 "arousal": 0.9, "intensity": 0.9}, "/people/alex.md", "2024-01-01",
                 "2024-12-31")
            seed("Affect excluded", {"emotion": "calm", "valence": 0.5,
                 "arousal": 0.5, "intensity": 0.8}, "/people/other.md", "2024-01-01",
                 "2024-12-31")
            seed("Affect zero boundary", {"emotion": "neutral", "valence": 0,
                 "arousal": 0, "intensity": 0}, "/people/alex.md", "2024-01-01",
                 "2024-12-31")

            def call(req_id, name, arguments):
                return {"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                        "params": {"name": name, "arguments": arguments}}

            requests = [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                call(2, "brain_recall_affect", {"emotion": "joy", "min_valence": 0.2,
                     "max_valence": 0.8, "min_arousal": 0.4, "max_arousal": 0.9,
                     "min_intensity": 0.7}),
                call(3, "brain_recall_affect", {"emotion": "joy", "limit": 1}),
                call(4, "brain_recall_subject", {"subject": "alex"}),
                call(5, "brain_recall_as_of", {"as_of": "2024-06-01", "query": "synthetic"}),
                call(6, "brain_recall_as_of", {"as_of": "2025-01-01"}),
                call(7, "brain_recall_affect", {"min_valence": [0.2]}),
                call(8, "brain_recall_affect", {"min_valence": 0, "max_valence": 0,
                     "min_arousal": 0, "max_arousal": 0, "min_intensity": 0}),
                call(9, "brain_recall_affect", {"limit": 0}),
                call(10, "brain_recall_affect", {"limit": None}),
                call(11, "brain_recall_subject", {"subject": "alex", "limit": 1}),
            ]
            result = subprocess.run(
                [sys.executable, str(SERVER)],
                input="".join(json.dumps(request) + "\n" for request in requests),
                cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                timeout=30, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            responses = {item["id"]: item for item in map(json.loads, result.stdout.splitlines())}
            self.assertEqual(set(responses), set(range(1, 12)), result.stdout)

            listed = {tool["name"]: tool for tool in responses[1]["result"]["tools"]}
            required = {"brain_add", "brain_search", "brain_recall_as_of",
                        "brain_recall_affect", "brain_recall_subject"}
            self.assertTrue(required.issubset(listed))
            affect_schema = listed["brain_recall_affect"]["inputSchema"]
            self.assertEqual(affect_schema["properties"]["min_valence"]["type"], "number")
            self.assertEqual(affect_schema["properties"]["limit"]["type"], "integer")

            def payload(req_id):
                response = responses[req_id]["result"]
                self.assertNotIn("isError", response)
                return json.loads(response["content"][0]["text"])

            bounded = payload(2)
            self.assertEqual([row["title"] for row in bounded["concepts"]],
                             ["Affect boundary two", "Affect boundary one"])
            self.assertEqual(len(payload(3)["concepts"]), 1)
            subject = payload(4)
            self.assertEqual(subject["subject"], "/people/alex.md")
            self.assertEqual({row["title"] for row in subject["concepts"]},
                             {"Affect boundary one", "Affect boundary two",
                              "Affect zero boundary"})
            historical = payload(5)
            self.assertEqual(historical["as_of"], "2024-06-01")
            self.assertEqual(len(historical["concepts"]), 4)
            self.assertEqual(payload(6)["concepts"], [])
            self.assertTrue(responses[7]["result"]["isError"])
            zero_bounds = payload(8)
            self.assertEqual(zero_bounds["filters"], {
                "min_valence": 0, "max_valence": 0, "min_arousal": 0,
                "max_arousal": 0, "min_intensity": 0,
            })
            self.assertEqual([row["title"] for row in zero_bounds["concepts"]],
                             ["Affect zero boundary"])
            self.assertEqual(payload(9)["concepts"], [])
            self.assertTrue(responses[10]["result"]["isError"])
            self.assertTrue(responses[10]["result"]["content"][0]["text"].startswith("Error:"))
            self.assertEqual(len(payload(11)["concepts"]), 1)

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
