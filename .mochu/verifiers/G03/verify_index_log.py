#!/usr/bin/env python3
"""G03 verifier — OKF reserved files: index.md, log.md, okf_version pin.

Claim: an exported Bundle is OKF v0.1-conformant with progressive-disclosure
index files and a change log: a root index.md declaring `okf_version: "0.1"`
that lists collections and root concepts with working links + descriptions, a
per-subdirectory index.md listing that directory's concepts, and a log.md with
ISO date-grouped entries newest-first. The Bundle still rebuilds unchanged.

Executes the real bundle.export over a brain with collections, then validates
the generated reserved files structurally and checks every index link resolves
to a real file.
"""
import sys, re, tempfile, shutil, subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
from brain import SecondBrain  # noqa: E402
import bundle  # noqa: E402

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
fails = []


def check(c, m):
    if not c:
        fails.append(m)


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        b = SecondBrain(tmp / "a.db")
        b.add("Checkout timeout fix", "Raised gateway timeout to 30s.",
              collection="Engineering")
        b.add("Payments", "The payments subsystem 中文.", collection="Engineering")
        b.add("Quarterly goals", "OKRs for Q3.", collection="Planning")
        b.add("Root note", "Lives at the bundle root.")
        b.close()
        b = SecondBrain(tmp / "a.db")
        bdir = tmp / "okf"
        bundle.export(b, bdir)
        concept_count = len(b.list(limit=10**9))
        b.close()

        # --- root index.md ---
        root_idx = bdir / "index.md"
        check(root_idx.exists(), "root index.md missing")
        if root_idx.exists():
            txt = root_idx.read_text(encoding="utf-8")
            check(re.search(r'okf_version:\s*"?0\.1"?', txt),
                  "root index.md does not declare okf_version 0.1")
            # collections + root concept appear as links
            check("Engineering" in txt and "Planning" in txt,
                  "root index.md missing a collection entry")
            check("Root note" in txt, "root index.md missing the root concept")
            # every link target resolves to a real file/dir under the bundle
            for _, tgt in LINK.findall(txt):
                t = tgt.split("#")[0].strip("/")
                if not t:
                    continue
                check((bdir / t).exists(), f"root index.md broken link: {tgt}")

        # --- per-subdirectory index.md ---
        eng_idx = bdir / "Engineering" / "index.md"
        check(eng_idx.exists(), "Engineering/index.md missing")
        if eng_idx.exists():
            txt = eng_idx.read_text(encoding="utf-8")
            check("# " in txt, "subdir index.md has no section heading")
            names = [m[0] for m in LINK.findall(txt)]
            check("Checkout timeout fix" in names and "Payments" in names,
                  "Engineering/index.md missing a concept entry")
            for _, tgt in LINK.findall(txt):
                t = tgt.split("#")[0]
                check((eng_idx.parent / t).exists(),
                      f"Engineering/index.md broken link: {tgt}")
            # index.md itself MUST NOT carry frontmatter (OKF §6)
            check(not txt.startswith("---"),
                  "subdir index.md must not have frontmatter")

        # --- log.md ---
        log = bdir / "log.md"
        check(log.exists(), "log.md missing")
        if log.exists():
            txt = log.read_text(encoding="utf-8")
            dates = re.findall(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", txt, re.M)
            check(len(dates) >= 1, "log.md has no ISO date-grouped (## YYYY-MM-DD) entries")
            check(dates == sorted(dates, reverse=True),
                  f"log.md dates not newest-first: {dates}")
            check(LINK.search(txt) is not None, "log.md entries reference no concepts")

        # --- Bundle still rebuilds, reserved files ignored ---
        b2 = bundle.rebuild(bdir, tmp / "b.db")
        check(len(b2.list(limit=10**9)) == concept_count,
              "rebuild count changed — reserved files not ignored")
        check(b2.get_by_title("index") == [] or all(
            d["title"] != "Index" for d in b2.list(limit=10**9)),
            "an index.md leaked in as a drawer")
        b2.close()

        # --- CLI entrypoint runs as a fresh process (stranger smoke test) ---
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "bundle.py")],
                           capture_output=True, text=True)
        check(r.returncode == 0 and "usage" in r.stdout.lower(),
              "bundle.py CLI entrypoint did not print usage cleanly")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("INDEX/LOG FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("INDEX/LOG PASS: root+subdir index.md, log.md, okf_version pin all conform; "
          "Bundle still rebuilds")


if __name__ == "__main__":
    main()
