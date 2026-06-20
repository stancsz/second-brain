"""Verifier: temporal-asof (G09 M2 / R11)

Proves that recall_as_of(as_of, query, collection, limit) and the
`brain recall --as-of <date>` CLI correctly return only the Concepts
whose validity window contains `as_of`:
  COALESCE(valid_from, created_at) <= as_of AND (valid_to IS NULL OR valid_to > as_of)

Phases:
  1. recall_as_of exists and is callable
  2. Timeless notes returned for any as_of >= creation
  3. NYC→SF supersession: as-of in NYC window returns NYC, not SF
  4. as-of in SF window returns SF, not NYC
  5. Exclusive valid_to boundary: fact with valid_to=X excluded at as_of=X
  6. Expired fact (valid_to in the past) excluded
  7. Optional FTS query filter with as-of
  8. CLI subprocess: `brain recall --as-of <date>` end-to-end
"""
import subprocess, sys, json, tempfile, pathlib, os, textwrap, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── locate project root ──────────────────────────────────────────────────────
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

# ── Phase 1: method exists ───────────────────────────────────────────────────
print("Phase 1: recall_as_of method exists")
import brain as _brain_mod
_has_method = callable(getattr(_brain_mod.SecondBrain, "recall_as_of", None))
chk("recall_as_of is callable", _has_method)
if not _has_method:
    print()
    print(f"RESULT: FAIL (recall_as_of not implemented; remaining phases skipped)")
    sys.exit(1)

# ── shared helpers ───────────────────────────────────────────────────────────

def make_brain(tmp):
    db = pathlib.Path(tmp) / "brain.db"
    return _brain_mod.SecondBrain(str(db))

# ── Phase 2: timeless notes returned ────────────────────────────────────────
print("Phase 2: timeless notes returned for any as_of >= creation")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)
    note = b.add("Timeless fact", "always true", collection="Facts")
    nid = note["id"]

    hits = b.recall_as_of("2020-01-01")
    chk("timeless note in far-past as_of", any(h["id"] == nid for h in hits),
        f"got ids {[h['id'] for h in hits]}")

    hits2 = b.recall_as_of("2099-12-31")
    chk("timeless note in far-future as_of", any(h["id"] == nid for h in hits2))

    b.con.close()

# ── Phase 3 & 4: NYC→SF supersession ────────────────────────────────────────
print("Phase 3 + 4: NYC→SF supersession — point-in-time correctness")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)

    # NYC fact valid 2015-06-01 .. 2023-09-01 (move-out date)
    nyc = b.add("Home city", "New York City", collection="Facts",
                 sb_valid_from="2015-06-01")
    nyc_id = nyc["id"]

    # Supersede: NYC window closes at 2023-09-01; SF opens
    sf = b.supersede(nyc_id, "Home city", "San Francisco", as_of="2023-09-01")
    sf_id = sf["id"]

    # as-of in NYC window: 2020-01-01 should return NYC, not SF
    in_nyc = b.recall_as_of("2020-01-01")
    in_nyc_ids = [h["id"] for h in in_nyc]
    chk("as-of 2020: NYC returned", nyc_id in in_nyc_ids, f"ids={in_nyc_ids}")
    chk("as-of 2020: SF excluded", sf_id not in in_nyc_ids, f"ids={in_nyc_ids}")

    # as-of in SF window: 2024-01-01 should return SF, not NYC
    in_sf = b.recall_as_of("2024-01-01")
    in_sf_ids = [h["id"] for h in in_sf]
    chk("as-of 2024: SF returned", sf_id in in_sf_ids, f"ids={in_sf_ids}")
    chk("as-of 2024: NYC excluded (window closed)", nyc_id not in in_sf_ids, f"ids={in_sf_ids}")

    b.con.close()

# ── Phase 5: exclusive valid_to boundary ─────────────────────────────────────
print("Phase 5: exclusive valid_to boundary")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)

    # Fact valid 2020-01-01 .. 2023-01-01 (exclusive)
    f = b.add("Bounded fact", "was true", sb_valid_from="2020-01-01", sb_valid_to="2023-01-01")
    fid = f["id"]

    # as_of = 2022-12-31: inside window → should be returned
    inside = b.recall_as_of("2022-12-31")
    chk("boundary: as_of before valid_to included", fid in [h["id"] for h in inside])

    # as_of = 2023-01-01: ON valid_to → EXCLUDED (exclusive upper bound)
    on_boundary = b.recall_as_of("2023-01-01")
    chk("boundary: as_of == valid_to excluded", fid not in [h["id"] for h in on_boundary],
        f"ids={[h['id'] for h in on_boundary]}")

    # as_of = 2023-01-02: after valid_to → EXCLUDED
    after = b.recall_as_of("2023-01-02")
    chk("boundary: as_of after valid_to excluded", fid not in [h["id"] for h in after])

    b.con.close()

# ── Phase 6: expired fact excluded ──────────────────────────────────────────
print("Phase 6: expired facts excluded")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)

    expired = b.add("Old belief", "no longer valid",
                    sb_valid_from="2000-01-01", sb_valid_to="2010-01-01")
    eid = expired["id"]

    current = b.add("Current belief", "still valid")
    cid = current["id"]

    hits = b.recall_as_of("2025-06-01")
    hit_ids = [h["id"] for h in hits]
    chk("expired fact excluded from present query", eid not in hit_ids, f"ids={hit_ids}")
    chk("current fact included in present query", cid in hit_ids)

    b.con.close()

# ── Phase 7: FTS query filter with as-of ────────────────────────────────────
print("Phase 7: FTS query filter combined with as-of")
with tempfile.TemporaryDirectory() as tmp:
    b = make_brain(tmp)

    b.add("WX-past", "sunny in NYC back then", sb_valid_from="2020-01-01", sb_valid_to="2022-01-01")
    b.add("WX-current", "still sunny in NYC today", sb_valid_from="2022-01-01")
    b.add("Unrelated note", "something else entirely")

    # as-of 2020-06-01, query "NYC" → only WX-past (WX-current's valid_from=2022 not yet reached)
    hits = b.recall_as_of("2020-06-01", query="NYC")
    titles = [h["title"] for h in hits]
    chk("FTS+as-of returns matching live note", "WX-past" in titles,
        f"titles={titles}")
    chk("FTS+as-of excludes not-yet-valid note", "WX-current" not in titles,
        f"titles={titles}")

    b.con.close()

# ── Phase 8: CLI subprocess end-to-end ───────────────────────────────────────
print("Phase 8: CLI `brain recall --as-of` end-to-end")
cli = ROOT / "scripts" / "brain_cli.py"

with tempfile.TemporaryDirectory() as tmp:
    db = str(pathlib.Path(tmp) / "brain.db")

    def cli_run(*args):
        # Always inject --db before the subcommand to target the temp DB
        argv = list(args)
        # Insert --db <path> at position 0 (before any global flags or subcommand)
        return subprocess.run(
            [sys.executable, str(cli), "--db", db] + argv,
            capture_output=True, text=True, encoding="utf-8"
        )

    # seed: add a NYC fact with a window, then supersede with SF
    r = cli_run("--json", "add", "Residence", "New York City",
                "--valid-from", "2015-01-01", "--collection", "Facts")
    if r.returncode != 0:
        chk("CLI add NYC", False, r.stderr[:200])
    else:
        try:
            nyc_id = json.loads(r.stdout.strip())["id"]
        except Exception:
            # fallback: search returns a list directly
            sr = cli_run("--json", "search", "New York City")
            rows = json.loads(sr.stdout) if sr.returncode == 0 else []
            nyc_id = rows[0]["id"] if rows else None

        if nyc_id:
            # supersede via update (close old, add new)
            cli_run("update", nyc_id, "--valid-to", "2023-09-01")
            r2 = cli_run("add", "Residence", "San Francisco",
                         "--valid-from", "2023-09-01", "--supersedes", nyc_id,
                         "--collection", "Facts")
            if r2.returncode == 0:
                # recall --as-of 2020 should mention NYC
                r3 = cli_run("recall", "--as-of", "2020-06-01")
                chk("CLI recall --as-of 2020 exits 0", r3.returncode == 0, r3.stderr[:200])
                chk("CLI recall --as-of 2020 contains NYC",
                    "New York" in r3.stdout or "nyc" in r3.stdout.lower(),
                    f"stdout={r3.stdout[:300]}")

                # recall --as-of 2024 should mention SF, not NYC
                r4 = cli_run("recall", "--as-of", "2024-01-01")
                chk("CLI recall --as-of 2024 exits 0", r4.returncode == 0, r4.stderr[:200])
                chk("CLI recall --as-of 2024 contains SF",
                    "San Francisco" in r4.stdout or "sf" in r4.stdout.lower(),
                    f"stdout={r4.stdout[:300]}")
                chk("CLI recall --as-of 2024 excludes NYC residence",
                    "New York" not in r4.stdout,
                    f"stdout={r4.stdout[:300]}")
            else:
                chk("CLI add SF", False, r2.stderr[:200])
        else:
            chk("CLI parse NYC id", False, "could not extract id from output")

# ── Final ─────────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"RESULT: FAIL ({len(errors)} failures: {errors})")
    sys.exit(1)
print("RESULT: PASS")
