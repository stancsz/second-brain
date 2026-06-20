"""Verifier: iso-validation (G26 / reliability — hardens R11)

Validity windows must not accept garbage. Two distinct contracts:

  WRITE PATH (add / update / supersede): a malformed sb_valid_from / sb_valid_to
  raises ValueError with an actionable message — fail fast, never store a date
  string that sorts wrong.

  REBUILD PATH (rebuild_validity_index from concepts.metadata): a malformed date
  ALREADY present in metadata is QUARANTINED — that concept gets no validity row,
  the rest of the index is built intact, and the rebuild does NOT crash. Existing
  OKF files may carry bad strings; a rebuild must be robust to them.

Phases:
  1. Write path: malformed dates raise ValueError (add, update, supersede)
  2. Write path: well-formed ISO dates AND datetimes AND leap dates are accepted
  3. Rebuild path: a bad date in metadata is quarantined, good rows survive, no crash
  4. Post-quarantine recall_as_of still works on the surviving good rows
  5. CLI: `brain add --valid-from "June 2023"` exits nonzero with a clean
     message and ZERO traceback
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

def raises_valueerror(fn):
    try:
        fn()
        return False
    except ValueError:
        return True
    except Exception:
        return False  # wrong exception type — not an actionable ValueError

import brain as _brain_mod

def make_brain(tmp):
    return _brain_mod.SecondBrain(str(pathlib.Path(tmp) / "brain.db"))

BAD_DATES = ["June 2023", "2023/06/01", "2023-13-01", "2023-02-30", "tomorrow", "01-01-2023"]
GOOD_DATES = ["2023-01-01", "2024-02-29", "2023-06-15T12:30:00", "2020-12-31"]

# ── Phase 1: write path rejects malformed dates ──────────────────────────────
print("Phase 1: write path (add/update/supersede) rejects malformed dates")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)
    for bad in BAD_DATES:
        chk(f"add(sb_valid_from={bad!r}) raises ValueError",
            raises_valueerror(lambda bad=bad: b.add("X", "y", sb_valid_from=bad)))
    chk("add(sb_valid_to='bad-date') raises ValueError",
        raises_valueerror(lambda: b.add("X2", "y", sb_valid_to="bad-date")))

    # a real concept to mutate
    dr = b.add("Mutable", "body")
    chk("update(sb_valid_from='June 2023') raises ValueError",
        raises_valueerror(lambda: b.update(dr["id"], sb_valid_from="June 2023")))
    chk("update(sb_valid_to='2023/13/01') raises ValueError",
        raises_valueerror(lambda: b.update(dr["id"], sb_valid_to="2023/13/01")))

    old = b.add("Old fact", "v1", sb_valid_from="2020-01-01")
    chk("supersede(as_of='not-a-date') raises ValueError",
        raises_valueerror(lambda: b.supersede(old["id"], "New", "v2", as_of="not-a-date")))
    b.con.close()

# ── Phase 2: write path accepts well-formed ISO dates/datetimes ──────────────
print("Phase 2: write path accepts well-formed ISO dates, datetimes, leap dates")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)
    for good in GOOD_DATES:
        try:
            dr = b.add(f"Good {good}", "y", sb_valid_from=good)
            v = b.validity(dr["id"])
            chk(f"add(sb_valid_from={good!r}) stored", v is not None and v["valid_from"] == good)
        except Exception as e:
            chk(f"add(sb_valid_from={good!r}) stored", False, f"raised {type(e).__name__}: {e}")
    b.con.close()

# ── Phase 3: rebuild quarantines bad metadata dates, keeps good rows ─────────
print("Phase 3: rebuild_validity_index quarantines bad dates, survives, keeps good rows")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)
    # A good concept (well-formed window).
    good = b.add("Good window", "g", sb_valid_from="2021-01-01")
    # A concept whose metadata carries a GARBAGE date — injected directly into
    # metadata to BYPASS the write-path guard, simulating an OKF file authored
    # by hand or an older version.
    bad = b.add("Bad window", "b")
    meta = json.dumps({"sb_valid_from": "garbage-not-a-date"})
    b.con.execute("UPDATE concepts SET metadata=? WHERE id=?", (meta, bad["id"]))
    b.con.commit()

    crashed = False
    try:
        n = b.rebuild_validity_index()
    except Exception as e:
        crashed = True
        chk("rebuild_validity_index does NOT crash on bad metadata", False,
            f"raised {type(e).__name__}: {e}")
    if not crashed:
        chk("rebuild_validity_index does NOT crash on bad metadata", True)
        chk("good concept keeps its validity row", b.validity(good["id"]) is not None)
        chk("bad-date concept is quarantined (no validity row)",
            b.validity(bad["id"]) is None, f"got {b.validity(bad['id'])}")
    b.con.close()

# ── Phase 4: recall_as_of still works after the quarantine rebuild ───────────
print("Phase 4: recall_as_of works on surviving good rows after quarantine")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)
    good = b.add("Lives 2021+", "g", sb_valid_from="2021-01-01")
    bad = b.add("Corrupt", "b")
    b.con.execute("UPDATE concepts SET metadata=? WHERE id=?",
                  (json.dumps({"sb_valid_from": "nope"}), bad["id"]))
    b.con.commit()
    b.rebuild_validity_index()
    hits = [h["id"] for h in b.recall_as_of("2022-06-01")]
    chk("good concept recalled as-of 2022", good["id"] in hits)
    # the corrupt concept has no validity row → treated as timeless → still returned
    # (the point is recall does not crash and the good row is correct)
    chk("recall_as_of did not crash post-quarantine", isinstance(hits, list))
    b.con.close()

# ── Phase 5: CLI boundary — bad --valid-from is clean, no traceback ──────────
print("Phase 5: CLI `brain add --valid-from 'June 2023'` is clean, no traceback")
cli = ROOT / "scripts" / "brain_cli.py"
with tempfile.TemporaryDirectory() as tmp:
    db = str(pathlib.Path(tmp) / "brain.db")
    r = subprocess.run(
        [sys.executable, str(cli), "--db", db, "add", "T", "c", "--valid-from", "June 2023"],
        capture_output=True, text=True, encoding="utf-8",
    )
    chk("CLI exits nonzero on bad --valid-from", r.returncode != 0, f"rc={r.returncode}")
    combined = (r.stdout or "") + (r.stderr or "")
    chk("CLI emits NO Python traceback", "Traceback (most recent call last)" not in combined,
        combined[:300])
    chk("CLI message mentions the date/ISO problem",
        any(w in combined.lower() for w in ("date", "iso", "valid-from", "valid_from")),
        combined[:300])

print()
if errors:
    print(f"RESULT: FAIL ({len(errors)} failures: {errors})")
    sys.exit(1)
print("RESULT: PASS")
