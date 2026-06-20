"""Verifier: restore-psych-dims (G27 / reliability — hardens R10/R11/R12)

A Concept that was soft-deleted, then carried through a `bundle.rebuild` (which
skips indexing deleted Concepts), then restored, must recover ALL of its
psychological dimensions — affect (R12), subject (R10), and validity (R11) —
from `concepts.metadata`, WITHOUT requiring a second rebuild. Before this fix
`restore()` re-synced only wikilinks + pending links, so the psych derived rows
stayed empty until the next full rebuild.

Phases:
  1. Real-world path: add(affect+subject+validity) -> soft-delete -> EXPORT ->
     REBUILD into a fresh db. Confirm the rebuild DROPPED the psych rows (this is
     the bug precondition the fix must repair).
  2. restore() on the rebuilt db recovers affect EXACTLY (values, not just a row).
  3. restore() recovers the subject sub-graph membership.
  4. restore() recovers the validity window EXACTLY.
  5. CLI: `brain restore` then `brain show` displays the affect + validity again.
"""
import subprocess, sys, json, tempfile, pathlib, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parent
while ROOT != ROOT.parent and not (ROOT / "scripts" / "brain.py").exists():
    ROOT = ROOT.parent
if not (ROOT / "scripts" / "brain.py").exists():
    sys.exit("FAIL: could not locate project root")
sys.path.insert(0, str(ROOT / "scripts"))

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
errors = []

def chk(label, cond, detail=""):
    if cond:
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}" + (f": {detail}" if detail else ""))
        errors.append(label)

import brain as _brain_mod
import bundle as _bundle

AFFECT = {"emotion": "grief", "valence": -0.8, "arousal": 0.6, "intensity": 0.9}
SUBJECT = "/people/alex.md"
VALID_FROM = "2020-01-01"
VALID_TO = "2023-01-01"

# ── Phases 1–4: real rebuild path ────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    b1 = _brain_mod.SecondBrain(str(tmp / "b1.db"))
    dr = b1.add("Grief about Alex", "a hard memory", collection="Episodes",
                sb_subject=SUBJECT, sb_affect=AFFECT,
                sb_valid_from=VALID_FROM, sb_valid_to=VALID_TO)
    cid = dr["id"]
    # sanity: all three dims present while live
    assert b1.affect(cid) is not None and b1.validity(cid) is not None

    b1.delete(cid)            # soft-delete
    bundle_dir = tmp / "okf"
    _bundle.export(b1, str(bundle_dir))
    b1.con.close()

    # Fresh rebuild — deleted concept is present but NOT psych-indexed.
    b2 = _bundle.rebuild(str(bundle_dir), str(tmp / "b2.db"))

    print("Phase 1: rebuild dropped the psych rows (bug precondition)")
    chk("affect row absent after rebuild of a deleted concept", b2.affect(cid) is None,
        f"got {b2.affect(cid)}")
    chk("validity row absent after rebuild of a deleted concept", b2.validity(cid) is None,
        f"got {b2.validity(cid)}")
    in_subgraph_before = any(c["id"] == cid for c in b2.subject_subgraph(SUBJECT))
    chk("subject membership absent after rebuild", not in_subgraph_before)

    # The metadata itself must have survived the rebuild (the fix's source of truth).
    meta_row = b2.con.execute("SELECT metadata FROM concepts WHERE id=?", (cid,)).fetchone()
    meta = json.loads(meta_row["metadata"] or "{}") if meta_row else {}
    chk("metadata.sb_affect survived rebuild", meta.get("sb_affect") == AFFECT)

    # ── The fix: restore must recover every dim from metadata ──
    b2.restore(cid)

    print("Phase 2: restore recovers affect exactly")
    aff = b2.affect(cid)
    chk("affect present after restore", aff is not None)
    if aff:
        chk("affect emotion exact", aff.get("emotion") == "grief", f"got {aff.get('emotion')}")
        chk("affect valence exact", aff.get("valence") == -0.8, f"got {aff.get('valence')}")
        chk("affect intensity exact", aff.get("intensity") == 0.9, f"got {aff.get('intensity')}")

    print("Phase 3: restore recovers subject sub-graph membership")
    in_subgraph = any(c["id"] == cid for c in b2.subject_subgraph(SUBJECT))
    chk("concept back in /people/alex.md sub-graph", in_subgraph)

    print("Phase 4: restore recovers the validity window exactly")
    val = b2.validity(cid)
    chk("validity present after restore", val is not None)
    if val:
        chk("valid_from exact", val.get("valid_from") == VALID_FROM, f"got {val.get('valid_from')}")
        chk("valid_to exact", val.get("valid_to") == VALID_TO, f"got {val.get('valid_to')}")

    b2.con.close()

# ── Phase 5: CLI end-to-end ──────────────────────────────────────────────────
print("Phase 5: CLI restore then show displays psych dims again")
cli = ROOT / "scripts" / "brain_cli.py"
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    b1 = _brain_mod.SecondBrain(str(tmp / "c1.db"))
    # Emotion deliberately NOT a substring of the title/content, so a passing
    # affect check proves the affect was actually recovered + displayed, not just
    # that the word happens to appear in the note text.
    dr = b1.add("Seaside afternoon", "by the water", sb_subject="/people/rox.md",
                sb_affect={"emotion": "melancholy", "valence": -0.3},
                sb_valid_from="2021-06-01")
    cid = dr["id"]
    b1.delete(cid)
    bundle_dir = tmp / "okf2"
    _bundle.export(b1, str(bundle_dir))
    b1.con.close()
    db2 = str(tmp / "c2.db")
    _bundle.rebuild(str(bundle_dir), db2).con.close()

    def cli_run(*args):
        return subprocess.run([sys.executable, str(cli), "--db", db2] + list(args),
                              capture_output=True, text=True, encoding="utf-8")

    r = cli_run("restore", cid)
    chk("CLI restore exits 0", r.returncode == 0, r.stderr[:200])
    show = cli_run("show", cid)
    out = (show.stdout or "") + (show.stderr or "")
    chk("show displays affect after restore", "melancholy" in out.lower(), out[:300])
    chk("show displays validity window after restore", "2021-06-01" in out, out[:300])

print()
if errors:
    print(f"RESULT: FAIL ({len(errors)} failures: {errors})")
    sys.exit(1)
print("RESULT: PASS")
