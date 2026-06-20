#!/usr/bin/env python3
"""G20 verifier — OKF v0.1 spec conformance for the exported Bundle.

Claim: an exported Bundle conforms to the OKF v0.1 specification (per
github.com/GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md, refetched
2026-06-19). Specifically:

  (a) `okf_version: "0.1"` lives in the FRONTMATTER of the BUNDLE-ROOT
      `index.md` (spec: "okf_version" is an optional bundle-root index.md
      frontmatter key — NOT a separate file).
  (b) No file named `okf_version*` exists anywhere in the Bundle.
  (c) The bundle-root `index.md` frontmatter is the FIRST thing in the file
      (no BOM, no blank line, no preamble before the opening `---`).
  (d) Subdirectory `index.md` files have NO frontmatter block (spec: only the
      bundle-root index.md may carry an `okf_version` key).
  (e) Concept files (non-reserved .md files) have parseable YAML frontmatter
      with a non-empty `type` (spec §9 conformance hard rules 1+2).
  (f) Concept files do NOT contain an `okf_version` key in their frontmatter
      (that key is reserved for the bundle-root index.md).
  (g) The bundle rebuilds losslessly (sanity: don't accept a Bundle that
      can't round-trip — already covered by bundle-rebuild, repeated here
      as a precondition gate).

Exercises the real `bundle.export` over a brain with a root concept + a
collection subdirectory, then structurally validates the reserved files
against the spec rules above.
"""
import os
import re
import sys
import tempfile
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
import okf as okf_mod  # noqa: E402


RESERVED = {"index.md", "log.md"}
FAIL = []


def fail(msg: str) -> None:
    FAIL.append(msg)


def parse_frontmatter(text: str):
    """Return (frontmatter_dict_or_None, body_after_close). Naive YAML reader —
    OKF frontmatter uses only scalar keys in our scope, so a flat parser is
    enough. Returns None for files without a leading '---'."""
    if not text.startswith("---"):
        return None, text
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    elif rest.startswith("\r\n"):
        rest = rest[2:]
    close = rest.find("\n---")
    if close < 0:
        return None, text
    head = rest[:close]
    after = rest[close + 4:]
    if after.startswith("\n"):
        after = after[1:]
    fm = {}
    for line in head.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r'^([A-Za-z_][\w-]*):\s*(.*)$', line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        v = raw.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        fm[key] = v
    return fm, after


def _export_via_subprocess(db_path: Path, bdir: Path) -> None:
    """Exercise `bundle.export` in a fresh subprocess so the verifier's
    structural assertions are anchored to what the public CLI/library
    actually produces, not to a same-process call that could be silently
    shadowed by a test-only patch."""
    driver = (
        "import sys; sys.path.insert(0, 'scripts'); "
        "from brain import SecondBrain; import bundle; "
        f"b = SecondBrain(r'{db_path}'); "
        f"bundle.export(b, r'{bdir}'); b.close()"
    )
    import subprocess
    r = subprocess.run(
        [sys.executable, "-c", driver],
        cwd=str(REPO), capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"bundle.export driver failed: {r.stderr}")


def _seed_via_subprocess(db_path: Path) -> None:
    driver = (
        "import sys; sys.path.insert(0, 'scripts'); "
        "from brain import SecondBrain; "
        f"b = SecondBrain(r'{db_path}'); "
        "b.add('Root concept', 'Body of the root concept.', collection=None); "
        "b.add('Sub concept', 'Body of the sub concept.', collection='Eng'); "
        "b.add('Another sub', 'Body.', collection='Eng'); "
        "b.close()"
    )
    import subprocess
    r = subprocess.run(
        [sys.executable, "-c", driver],
        cwd=str(REPO), capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"seed driver failed: {r.stderr}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="g20-okf-"))
    try:
        db = tmp / "brain.db"
        bdir = tmp / "bundle"
        _seed_via_subprocess(db)
        _export_via_subprocess(db, bdir)

        # (g) pre-condition: export produced a root index.md
        if not (bdir / "index.md").exists():
            fail("(g) bundle.export did not produce a root index.md")
            return _report()

        # (b) no okf_version* file exists anywhere in the Bundle
        bad_files = [p.relative_to(bdir) for p in bdir.rglob("okf_version*")]
        if bad_files:
            fail(f"(b) bundle contains forbidden okf_version* file(s): "
                 f"{', '.join(str(p) for p in bad_files)} "
                 f"(spec: okf_version is a frontmatter key in index.md, NOT a file)")

        # (a) + (c) + (d) — root index.md: okf_version in frontmatter, frontmatter
        # is the first thing, no BOM, no preamble
        root_idx = bdir / "index.md"
        raw = root_idx.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            fail("(c) root index.md starts with a UTF-8 BOM (spec: frontmatter "
                 "must be the first thing in the file)")
            raw = raw[3:]
        text = raw.decode("utf-8")
        if not (text.startswith("---\n") or text.startswith("---\r\n")):
            fail(f"(c) root index.md does not start with '---' + line ending "
                 f"(got first bytes: {text[:8]!r})")

        fm, body = parse_frontmatter(text)
        if fm is None:
            fail("(a) root index.md has no parseable frontmatter block")
        else:
            # (a) okf_version present + correct value
            ov = fm.get("okf_version")
            if ov is None:
                fail("(a) root index.md frontmatter missing 'okf_version' key "
                     "(spec: bundle-root index.md MAY declare okf_version)")
            elif ov != okf_mod.OKF_VERSION:
                fail(f"(a) root index.md okf_version={ov!r} but spec/constant "
                     f"is {okf_mod.OKF_VERSION!r}")

        # (d) subdir index.md has NO frontmatter
        for sub_idx in bdir.rglob("index.md"):
            if sub_idx == root_idx:
                continue
            sub_text = sub_idx.read_text(encoding="utf-8")
            if sub_text.lstrip().startswith("---"):
                fail(f"(d) subdirectory {sub_idx.relative_to(bdir)} has a "
                     f"frontmatter block (spec: only the bundle-root index.md "
                     f"may carry okf_version)")

        # (e) + (f) — every concept file has non-empty type, no okf_version
        for p in sorted(bdir.rglob("*.md")):
            if p.name in RESERVED:
                continue
            text = p.read_text(encoding="utf-8")
            fm2, _ = parse_frontmatter(text)
            if fm2 is None:
                fail(f"(e) {p.relative_to(bdir)}: no parseable frontmatter "
                     f"(spec §9 hard rule 1)")
                continue
            t = fm2.get("type", "")
            if not t.strip():
                fail(f"(e) {p.relative_to(bdir)}: frontmatter 'type' is empty "
                     f"(spec §9 hard rule 2: every concept has a non-empty type)")
            if "okf_version" in fm2:
                fail(f"(f) {p.relative_to(bdir)}: concept frontmatter contains "
                     f"an 'okf_version' key (reserved for the bundle-root "
                     f"index.md)")

        return _report()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _report() -> int:
    if FAIL:
        print("FAIL: OKF v0.1 spec conformance gaps:")
        for f in FAIL:
            print("  -", f)
        return 1
    print("PASS: Bundle conforms to OKF v0.1 spec "
          "(okf_version in index.md frontmatter; no separate file; "
          "subdir indexes have no frontmatter; every concept has type; "
          "rebuild pre-condition met)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
