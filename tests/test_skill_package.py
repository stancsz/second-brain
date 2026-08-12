#!/usr/bin/env python3
"""Tests for the dependency-free Agent Skills package validator."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_skill import validate_skill  # noqa: E402


class TestSkillPackage(unittest.TestCase):
    def make_skill(
        self,
        name: str = "fixture-skill",
        *,
        frontmatter: str | None = None,
        body: str = "# Fixture\n\nFollow these instructions.",
    ) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / name
        root.mkdir()
        metadata = frontmatter or (
            f"name: {name}\n"
            "description: Use this fixture when validating a portable agent skill."
        )
        (root / "SKILL.md").write_text(
            f"---\n{metadata.rstrip()}\n---\n\n{body}\n", encoding="utf-8"
        )
        return root

    def test_checked_in_repository_is_a_valid_package(self):
        self.assertEqual(validate_skill(ROOT), [])

    def test_validator_cli_passes_from_an_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory() as unrelated:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate_skill.py"), str(ROOT)],
                cwd=unrelated,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_minimal_spec_package_needs_only_skill_md(self):
        root = self.make_skill()
        self.assertEqual(validate_skill(root), [])

    def test_standard_optional_fields_and_folded_description_are_supported(self):
        root = self.make_skill(
            frontmatter=(
                "name: fixture-skill  # inline YAML comment\n"
                "description: >\n"
                "  Use this fixture when a portable skill needs folded metadata\n"
                "  and optional Agent Skills fields.\n"
                "license: MIT\n"
                "compatibility: Requires Python 3.10 or newer.\n"
                "metadata:\n"
                "  author: example\n"
                '  version: "1.0"\n'
                "allowed-tools: Bash(python:*)\n"
            ),
        )
        self.assertEqual(validate_skill(root), [])

    def test_name_rejects_consecutive_hyphens(self):
        root = self.make_skill(name="bad--name")
        errors = validate_skill(root)
        self.assertTrue(any("single hyphens" in error for error in errors), errors)

    def test_name_must_match_parent_directory(self):
        root = self.make_skill(
            name="fixture-skill",
            frontmatter=(
                "name: different-skill\n"
                "description: Use this fixture to test directory-name matching.\n"
            ),
        )
        errors = validate_skill(root)
        self.assertTrue(any("must match directory" in error for error in errors), errors)

    def test_description_limit_is_enforced(self):
        root = self.make_skill(
            frontmatter=f"name: fixture-skill\ndescription: {'x' * 1025}\n"
        )
        errors = validate_skill(root)
        self.assertTrue(any("at most 1024" in error for error in errors), errors)

    def test_unknown_top_level_frontmatter_is_rejected(self):
        root = self.make_skill(
            frontmatter=(
                "name: fixture-skill\n"
                "description: Use this fixture to reject non-standard metadata.\n"
                "version: 1.0\n"
            ),
        )
        errors = validate_skill(root)
        self.assertTrue(any("unsupported top-level" in error for error in errors), errors)

    def test_missing_local_markdown_reference_is_rejected(self):
        root = self.make_skill(body="Read [the guide](references/missing.md).")
        errors = validate_skill(root)
        self.assertTrue(any("does not exist" in error for error in errors), errors)

    def test_bundled_python_syntax_is_checked(self):
        root = self.make_skill(body="Run `scripts/broken.py`.")
        scripts = root / "scripts"
        scripts.mkdir()
        (scripts / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        errors = validate_skill(root)
        self.assertTrue(any("does not compile" in error for error in errors), errors)

    def test_codex_metadata_requires_quoted_strings_and_skill_prompt(self):
        root = self.make_skill()
        agents = root / "agents"
        agents.mkdir()
        (agents / "openai.yaml").write_text(
            "interface:\n"
            "  display_name: Fixture Skill\n"
            '  short_description: "A sufficiently long fixture description"\n'
            '  default_prompt: "Use this fixture now."\n',
            encoding="utf-8",
        )
        errors = validate_skill(root)
        self.assertTrue(any("string values must be quoted" in error for error in errors), errors)
        self.assertTrue(any("must mention $fixture-skill" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
