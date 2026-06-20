"""Verifier: window-coherence (G32 / reliability — hardens R11)

G26 validated each date's FORMAT. G32 enforces the RELATIONSHIP between the two
dates: `valid_from <= valid_to`. A backwards window (valid_from AFTER valid_to)
can never contain any `as_of` under recall_as_of's predicate, so it is
unambiguously a mistake, not a representable state. Two contracts, mirroring G26:

  WRITE PATH (add / update / supersede): a backwards window raises ValueError
  before any write. supersede(as_of) where as_of precedes the old fact's
  valid_from also raises (cannot close a window before it opened).

  REBUILD PATH (rebuild_validity_index): a backwards window already in metadata
  is QUARANTINED — the whole window is dropped (we cannot tell which bound is
  wrong), the concept survives, the rest of the index builds, no crash.

  Equal bounds (valid_from == valid_to) are allowed: a zero-width window is
  degenerate but representable; only strictly-backwards is rejected.

Phases:
  1. add() with valid_from > valid_to raises ValueError
  2. update() into a backwards window raises ValueError
  3. supersede() with as_of before the old fact's valid_from raises ValueError
  4. coherent windows accepted: from < to, and the equal-bounds edge
  5. rebuild quarantines a backwards window in metadata; good rows survive
  6. CLI: backwards `--valid-from/--valid-to` is a clean message, no traceback
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
        fn(); return False
    except ValueError:
        return True
    except Exception:
        return False

import brain as _brain_mod

def mk(tmp):
    return _brain_mod.SecondBrain(str(pathlib.Path(tmp) / "brain.db"))

# ── Phase 1: add backwards window ────────────────────────────────────────────
print("Phase 1: add() with valid_from > valid_to raises ValueError")
with tempfile.TemporaryDirectory() as tmp:
    b = mk(tmp)
    chk("add(from=2025-01-01, to=2020-01-01) raises",
        raises_valueerror(lambda: b.add("X", "y",
            sb_valid_from="2025-01-01", sb_valid_to="2020-01-01")))
    chk("add(from=2023-06-02, to=2023-06-01) raises (one day backwards)",
        raises_valueerror(lambda: b.add("X2", "y",
            sb_valid_from="2023-06-02", sb_valid_to="2023-06-01")))
    # mixed date / datetime, still backwards
    chk("add backwards across date/datetime forms raises",
        raises_valueerror(lambda: b.add("X3", "y",
            sb_valid_from="2023-06-01T12:00:00", sb_valid_to="2023-06-01")))
    b.con.close()

# ── Phase 2: update into a backwards window ──────────────────────────────────
print("Phase 2: update() into a backwards window raises ValueError")
with tempfile.TemporaryDirectory() as tmp:
    b = mk(tmp)
    dr = b.add("Fact", "body", sb_valid_from="2020-01-01")
    chk("update(valid_to=2019-01-01) before existing valid_from raises",
        raises_valueerror(lambda: b.update(dr["id"], sb_valid_to="2019-01-01")))
    # setting both at once, backwards
    dr2 = b.add("Fact2", "body")
    chk("update(from=2025, to=2024) raises",
        raises_valueerror(lambda: b.update(dr2["id"],
            sb_valid_from="2025-01-01", sb_valid_to="2024-01-01")))
    b.con.close()

# ── Phase 3: supersede as_of before old valid_from ───────────────────────────
print("Phase 3: supersede() with as_of before old valid_from raises ValueError")
with tempfile.TemporaryDirectory() as tmp:
    b = mk(tmp)
    old = b.add("Lived NYC", "v1", sb_valid_from="2020-01-01")
    chk("supersede(as_of=2015-01-01) before old.valid_from raises",
        raises_valueerror(lambda: b.supersede(old["id"], "Lived SF", "v2",
            as_of="2015-01-01")))
    # sanity: a forward supersede still works
    ok = True
    try:
        b.supersede(old["id"], "Lived SF", "v2", as_of="2023-01-01")
    except Exception as e:
        ok = False; detail = f"{type(e).__name__}: {e}"
    chk("forward supersede(as_of=2023-01-01) still works", ok,
        "" if ok else detail)
    b.con.close()

# ── Phase 4: coherent windows accepted ───────────────────────────────────────
print("Phase 4: coherent windows accepted (from < to, and equal-bounds edge)")
with tempfile.TemporaryDirectory() as tmp:
    b = mk(tmp)
    try:
        d1 = b.add("OK window", "y", sb_valid_from="2020-01-01", sb_valid_to="2023-01-01")
        v = b.validity(d1["id"])
        chk("forward window stored", v and v["valid_from"] == "2020-01-01" and v["valid_to"] == "2023-01-01")
    except Exception as e:
        chk("forward window stored", False, f"{type(e).__name__}: {e}")
    try:
        d2 = b.add("Equal bounds", "y", sb_valid_from="2022-05-05", sb_valid_to="2022-05-05")
        chk("equal-bounds window accepted (degenerate but representable)",
            b.validity(d2["id"]) is not None)
    except Exception as e:
        chk("equal-bounds window accepted (degenerate but representable)", False,
            f"{type(e).__name__}: {e}")
    b.con.close()

# ── Phase 5: rebuild quarantines a backwards window ──────────────────────────
print("Phase 5: rebuild_validity_index quarantines a backwards window, keeps good rows")
with tempfile.TemporaryDirectory() as tmp:
    b = mk(tmp)
    good = b.add("Good", "g", sb_valid_from="2021-01-01", sb_valid_to="2022-01-01")
    bad = b.add("Bad", "b")
    b.con.execute("UPDATE concepts SET metadata=? WHERE id=?",
                  (json.dumps({"sb_valid_from": "2025-01-01", "sb_valid_to": "2020-01-01"}),
                   bad["id"]))
    b.con.commit()
    crashed = False
    try:
        b.rebuild_validity_index()
    except Exception as e:
        crashed = True
        chk("rebuild does NOT crash on a backwards window", False, f"{type(e).__name__}: {e}")
    if not crashed:
        chk("rebuild does NOT crash on a backwards window", True)
        chk("good window survives rebuild", b.validity(good["id"]) is not None)
        chk("backwards window quarantined (no row)", b.validity(bad["id"]) is None,
            f"got {b.validity(bad['id'])}")
    b.con.close()

# ── Phase 6: CLI clean error ─────────────────────────────────────────────────
print("Phase 6: CLI backwards window is a clean message, no traceback")
cli = ROOT / "scripts" / "brain_cli.py"
with tempfile.TemporaryDirectory() as tmp:
    db = str(pathlib.Path(tmp) / "brain.db")
    r = subprocess.run(
        [sys.executable, str(cli), "--db", db, "add", "T", "c",
         "--valid-from", "2025-01-01", "--valid-to", "2020-01-01"],
        capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout or "") + (r.stderr or "")
    chk("CLI exits nonzero on backwards window", r.returncode != 0, f"rc={r.returncode}")
    chk("CLI emits NO traceback", "Traceback (most recent call last)" not in out, out[:300])
    chk("CLI message references the window/order problem",
        any(w in out.lower() for w in ("valid_to", "valid-to", "before", "after", "window", "order")),
        out[:300])

print()
if errors:
    print(f"RESULT: FAIL ({len(errors)} failures: {errors})")
    sys.exit(1)
print("RESULT: PASS")
