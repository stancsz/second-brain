#!/usr/bin/env python3
"""Static regression checks for the GitHub Pages entry point."""

from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
INDEX = DOCS / "index.html"
ZH_INDEX = DOCS / "zh" / "index.html"
PUBLIC_MARKDOWN = (
    ROOT / "README.md",
    ROOT / "README.zh.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "GOVERNANCE.md",
    ROOT / "SECURITY.md",
    DOCS / "README.md",
    DOCS / "HOST_SETUP.md",
    DOCS / "COMPATIBILITY.md",
    DOCS / "OPEN_SOURCE_SAAS.md",
    DOCS / "PROJECT_REVIEW.md",
    DOCS / "THREAT_MODEL.md",
    DOCS / "RELEASE_CHECKLIST.md",
    ROOT / "references" / "storage.md",
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.local_assets: list[str] = []
        self.meta_names: set[str] = set()
        self.title_parts: list[str] = []
        self.text_by_id: dict[str, list[str]] = {}
        self.copy_targets: list[str] = []
        self._in_title = False
        self._active_text_id: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
            self._active_text_id = values["id"]
            self.text_by_id.setdefault(values["id"] or "", [])
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        if tag == "link" and values.get("href"):
            self.local_assets.append(values["href"] or "")
        if tag == "script" and values.get("src"):
            self.local_assets.append(values["src"] or "")
        if tag == "meta" and values.get("name"):
            self.meta_names.add(values["name"] or "")
        if values.get("data-copy-target"):
            self.copy_targets.append(values["data-copy-target"] or "")
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if self._active_text_id and tag in {"code", "pre", "div", "section"}:
            self._active_text_id = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._active_text_id:
            self.text_by_id[self._active_text_id].append(data)


class TestGitHubPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = INDEX.read_text(encoding="utf-8")
        cls.page = PageParser()
        cls.page.feed(cls.html)

    def test_page_has_metadata_and_unique_landmark_ids(self):
        self.assertIn("viewport", self.page.meta_names)
        self.assertIn("description", self.page.meta_names)
        self.assertTrue("".join(self.page.title_parts).strip())
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))
        self.assertIn("main", self.page.ids)

    def test_internal_anchor_links_have_targets(self):
        targets = set(self.page.ids)
        missing = [href for href in self.page.hrefs if href.startswith("#") and href[1:] not in targets]
        self.assertEqual(missing, [])

    def test_local_assets_exist_inside_docs(self):
        missing: list[str] = []
        escaped: list[str] = []
        docs_root = DOCS.resolve()
        for reference in self.page.local_assets:
            parsed = urlparse(reference)
            if parsed.scheme or parsed.netloc or reference.startswith("//"):
                continue
            candidate = (DOCS / parsed.path).resolve()
            try:
                candidate.relative_to(docs_root)
            except ValueError:
                escaped.append(reference)
                continue
            if not candidate.is_file():
                missing.append(reference)
        self.assertEqual(escaped, [])
        self.assertEqual(missing, [])

    def test_pages_discovery_files_exist_and_reference_pages(self):
        robots = (DOCS / "robots.txt").read_text(encoding="utf-8")
        sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("Sitemap: https://stancsz.github.io/second-brain/sitemap.xml", robots)
        self.assertIn("https://stancsz.github.io/second-brain/", sitemap)
        self.assertIn("cp docs/robots.txt _site/robots.txt", (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8"))
        self.assertIn("cp docs/sitemap.xml _site/sitemap.xml", (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8"))
        self.assertIn("cp docs/zh/index.html _site/zh/index.html", (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8"))

    def test_chinese_landing_page_is_complete_and_linked(self):
        chinese = ZH_INDEX.read_text(encoding="utf-8")
        self.assertIn('<html lang="zh-CN"', chinese)
        self.assertIn("长脑子", chinese)
        self.assertIn("给 Agent", chinese)
        self.assertIn("install-command-zh", chinese)
        self.assertIn('href="../assets/site.css"', chinese)
        self.assertIn('src="../assets/site.js"', chinese)
        self.assertIn('href="./zh/"', self.html)
        self.assertIn("https://stancsz.github.io/second-brain/zh/", (DOCS / "sitemap.xml").read_text(encoding="utf-8"))

    def test_install_command_names_every_supported_host(self):
        command = " ".join(self.page.text_by_id["install-command"]).replace("\\", " ")
        tokens = command.split()
        self.assertEqual(
            tokens,
            [
                "npx", "skills", "add", "stancsz/second-brain",
                "--skill", "second-brain", "--global", "--copy", "-y",
                "--agent", "claude-code", "codex", "gemini-cli", "opencode", "cline",
            ],
        )
        self.assertEqual(self.page.copy_targets, ["install-command"])

    def test_public_copy_keeps_evidence_qualified(self):
        self.assertIn("Registration smoke; handshake pending", self.html)
        self.assertIn("Native Obsidian sync is not claimed", self.html)
        self.assertIn("brain_doctor.py --json", self.html)
        public_suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), "test_*.py")
        self.assertGreaterEqual(public_suite.countTestCases(), 200)
        self.assertIn(">262<", self.html)

    def test_host_installer_smoke_is_qualified(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        compatibility = (DOCS / "COMPATIBILITY.md").read_text(encoding="utf-8")
        host_setup = (DOCS / "HOST_SETUP.md").read_text(encoding="utf-8")
        self.assertIn("materialized copies", readme)
        self.assertIn("does not prove that Gemini CLI, OpenCode", readme)
        self.assertIn("copied `.agents` skill was then run", readme)
        self.assertIn("Installer smoke", compatibility)
        self.assertIn("not prove native skill discovery", compatibility)
        self.assertIn("post-copy execution", compatibility)
        self.assertIn("codex mcp add second-brain", host_setup)
        self.assertIn("Claude Code `2.1.146`", host_setup)
        self.assertIn("gemini mcp add second-brain", host_setup)
        self.assertIn("Gemini CLI `0.26.0`", host_setup)
        self.assertIn("`~/.cline/mcp.json`", host_setup)
        self.assertIn('"mcpServers"', host_setup)
        self.assertIn("OpenCode `1.15.10`", host_setup)
        self.assertIn('"enabled": true', host_setup)
        self.assertIn("Cline `3.0.51`", host_setup)

    def test_public_markdown_local_links_resolve(self):
        missing: list[str] = []
        escaped: list[str] = []
        repo_root = ROOT.resolve()
        for document in PUBLIC_MARKDOWN:
            text = document.read_text(encoding="utf-8")
            for raw_target in MARKDOWN_LINK.findall(text):
                target = raw_target.strip().strip("<>")
                parsed = urlparse(target)
                if parsed.scheme or parsed.netloc or target.startswith(("#", "//")):
                    continue
                candidate = (document.parent / unquote(parsed.path)).resolve()
                try:
                    candidate.relative_to(repo_root)
                except ValueError:
                    escaped.append(f"{document.relative_to(ROOT)} -> {target}")
                    continue
                if not candidate.exists():
                    missing.append(f"{document.relative_to(ROOT)} -> {target}")
        self.assertEqual(escaped, [])
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
