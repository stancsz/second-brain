#!/usr/bin/env python3
"""G02 verifier — Bundle round-trip & disposable SQLite.

Claim: a brain can be exported to an OKF Bundle and rebuilt from those files
into a *fresh* database that loses nothing — drawers (id/title/content/
collection/sources/tags), wikilink relations, soft-delete state, and a working
FTS index all survive. This is what makes brain.db disposable (RELEASE R2/R3).

Executes the real export + rebuild (scripts/bundle.py) over a diverse brain.
"""
import sys, tempfile, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
from brain import SecondBrain  # noqa: E402
import bundle  # noqa: E402  (must exist; absence = RED pre-build)

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        db1 = tmp / "a.db"
        b = SecondBrain(db1)
        # Diverse corpus.
        a = b.add("Checkout timeout fix", "Raised gateway timeout. See [[Payments]].",
                  collection="Engineering", tags=["ops", "urgent"],
                  sources=["https://x.com/1", "https://x.com/2"])
        p = b.add("Payments", "The payments subsystem 中文.", collection="Engineering",
                  tags=["ops"])
        n = b.add("Root note", "No collection here.")
        d = b.add("Doomed", "Will be soft-deleted.", collection="Trash")
        b.delete(d["id"])  # soft delete
        b.close()

        # Reopen, capture expected state.
        b = SecondBrain(db1)
        exp = {dr["id"]: dr for dr in b.list(limit=10**9)}
        exp_rels = len(b.related(a["id"], limit=99))  # A->Payments wikilink
        bundle_dir = tmp / "okf"
        bundle.export(b, bundle_dir)
        b.close()

        # Bundle files conform to OKF (non-reserved .md have a `type`).
        mds = [f for f in bundle_dir.rglob("*.md") if f.name not in ("index.md", "log.md")]
        check(len(mds) >= 4, f"expected >=4 concept files, got {len(mds)}")
        for f in mds:
            txt = f.read_text(encoding="utf-8")
            check(txt.startswith("---\n"), f"{f.name}: no frontmatter")
            check(any(l.startswith("type:") and l.strip() != "type:"
                      for l in txt.splitlines()), f"{f.name}: missing/empty type")

        # Rebuild into a FRESH db.
        db2 = tmp / "b.db"
        b2 = bundle.rebuild(bundle_dir, db2)

        got = {dr["id"]: dr for dr in b2.list(limit=10**9)}
        check(set(got) == set(exp),
              f"drawer id set differs: missing={set(exp)-set(got)} extra={set(got)-set(exp)}")
        for did, e in exp.items():
            g = got.get(did)
            if not g:
                continue
            for k in ("title", "content", "collection"):
                check(e[k] == g[k], f"[{did}] {k}: {e[k]!r} != {g[k]!r}")
            check(sorted(e["tags"]) == sorted(g["tags"]),
                  f"[{did}] tags {e['tags']} != {g['tags']}")
            check(sorted(e["sources"]) == sorted(g["sources"]),
                  f"[{did}] sources differ")

        # Soft-deleted drawer must NOT reappear as alive.
        check(b2.get(d["id"]) is None, "soft-deleted drawer came back alive after rebuild")

        # Wikilink relations re-derived.
        got_rels = len(b2.related(a["id"], limit=99))
        check(got_rels == exp_rels and got_rels >= 1,
              f"wikilink relations not rebuilt: exp {exp_rels} got {got_rels}")

        # FTS works on the rebuilt db.
        hits = [h["id"] for h in b2.search("timeout")]
        check(a["id"] in hits, "FTS search 'timeout' missed the expected drawer after rebuild")
        b2.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("REBUILD FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("REBUILD PASS: export->rebuild reproduced drawers, tags, sources, "
          "relations, soft-delete, and FTS")


if __name__ == "__main__":
    main()
