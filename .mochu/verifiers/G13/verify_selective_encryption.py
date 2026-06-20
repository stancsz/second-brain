"""Verifier: selective-encryption (G13 / R13 — trust)

Private Concepts (tag `private`/`psych`, or type `Episode`/`RelationshipModel`)
must be CIPHERTEXT in the exported OKF Bundle that git pushes; public Concepts
must stay PLAINTEXT and diffable. The round-trip (export→rebuild) must recover
the private Concept verbatim when the key is present. If a private Concept must
be exported but NO key is available, export REFUSES (raises) and never writes the
plaintext secret into the bundle — the moat-protecting "refuse to leak" leg.

Phases:
  1. crypto adapter: round-trip encrypt/decrypt identity; availability gating
  2. is_private classification (tags private/psych, types Episode/RelationshipModel)
  3. encrypt-on-export: private file body has NO plaintext secret; carries an
     sb_encrypted marker; public file stays plaintext
  4. private title does NOT leak into index.md / log.md
  5. round-trip: rebuild WITH key recovers the private body verbatim; public intact
  6. REFUSE-TO-LEAK: export with a private Concept and no key raises, and no
     plaintext secret is written anywhere in the bundle
  7. EXEC: a subprocess performs encrypt→write→read-raw and asserts ciphertext
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

# Feature-detect: clean red if the crypto adapter isn't implemented yet.
try:
    import crypto as _crypto
except Exception as e:
    print(f"Phase 1: crypto adapter present")
    print(f"  {FAIL}  scripts/crypto.py importable: {type(e).__name__}: {e}")
    print()
    print("RESULT: FAIL (selective encryption not implemented; remaining phases skipped)")
    sys.exit(1)

if not _crypto.backend_available():
    print("RESULT: FAIL (no crypto backend available in this environment — cannot verify)")
    sys.exit(1)

import brain as _brain_mod
import bundle as _bundle

SECRET = "DIARY: I felt deep grief about Alex on the seaside 中文密文"
PUBLIC = "public knowledge: the sky is blue"

def with_key(tmp):
    """Create a fresh key file and point the adapter at it via env."""
    kp = pathlib.Path(tmp) / "secret.key"
    _crypto.generate_key(str(kp))
    os.environ["SECONDBRAIN_KEY_FILE"] = str(kp)
    return kp

def no_key(tmp):
    os.environ["SECONDBRAIN_KEY_FILE"] = str(pathlib.Path(tmp) / "does-not-exist.key")

# ── Phase 1: round-trip ──────────────────────────────────────────────────────
print("Phase 1: crypto adapter round-trip + availability")
with tempfile.TemporaryDirectory() as tmp:
    with_key(tmp)
    chk("available() True with backend + key", _crypto.available())
    token = _crypto.encrypt(SECRET)
    chk("ciphertext != plaintext", SECRET not in token)
    chk("decrypt(encrypt(x)) == x", _crypto.decrypt(token) == SECRET)
    no_key(tmp)
    chk("available() False without key", not _crypto.available())

# ── Phase 2: is_private classification ───────────────────────────────────────
print("Phase 2: is_private classification")
chk("tag 'private' => private", _crypto.is_private({"tags": ["private"], "type": "Note"}))
chk("tag 'psych' => private", _crypto.is_private({"tags": ["psych"], "type": "Note"}))
chk("type 'Episode' => private", _crypto.is_private({"tags": [], "type": "Episode"}))
chk("type 'RelationshipModel' => private",
    _crypto.is_private({"tags": [], "type": "RelationshipModel"}))
chk("plain note => not private", not _crypto.is_private({"tags": ["misc"], "type": "Note"}))

# ── Phase 3 & 4 & 5: export / index / round-trip ─────────────────────────────
print("Phase 3+4+5: encrypt-on-export, index non-leak, round-trip")
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    with_key(tmp)
    b = _brain_mod.SecondBrain(str(tmp / "b.db"))
    priv = b.add("My private diary", SECRET, tags=["private"])
    pub = b.add("Public fact", PUBLIC, tags=["misc"])
    bundle_dir = tmp / "okf"
    _bundle.export(b, str(bundle_dir))
    b.con.close()

    # locate the two files by sb_id
    priv_file = pub_file = None
    for f in bundle_dir.rglob("*.md"):
        if f.name in ("index.md", "log.md"):
            continue
        txt = f.read_text(encoding="utf-8")
        if priv["id"] in txt:
            priv_file = (f, txt)
        if pub["id"] in txt:
            pub_file = (f, txt)

    chk("private concept file exists", priv_file is not None)
    chk("public concept file exists", pub_file is not None)
    if priv_file:
        _, ptxt = priv_file
        chk("private body is ciphertext (secret absent from disk)", SECRET not in ptxt,
            ptxt[:200])
        chk("private file carries sb_encrypted marker", "sb_encrypted" in ptxt)
    if pub_file:
        _, ptxt2 = pub_file
        chk("public body stays plaintext/diffable", PUBLIC in ptxt2)

    # Phase 4: index/log must not leak the private title
    idx = (bundle_dir / "index.md")
    log = (bundle_dir / "log.md")
    idx_txt = idx.read_text(encoding="utf-8") if idx.exists() else ""
    log_txt = log.read_text(encoding="utf-8") if log.exists() else ""
    chk("private title NOT in index.md", "My private diary" not in idx_txt, idx_txt[:200])
    chk("private title NOT in log.md", "My private diary" not in log_txt, log_txt[:200])
    chk("public title IS in index.md", "Public fact" in idx_txt)

    # Phase 5: rebuild WITH key recovers the private body verbatim
    b2 = _bundle.rebuild(str(bundle_dir), str(tmp / "b2.db"))
    got = b2.get(priv["id"])
    chk("rebuild recovers private body verbatim", got is not None and got["content"] == SECRET,
        (got or {}).get("content", "<missing>")[:80])
    gotpub = b2.get(pub["id"])
    chk("rebuild keeps public body", gotpub is not None and gotpub["content"] == PUBLIC)
    b2.con.close()

# ── Phase 6: refuse-to-leak ──────────────────────────────────────────────────
print("Phase 6: refuse-to-leak when no key is available")
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    no_key(tmp)
    b = _brain_mod.SecondBrain(str(tmp / "b.db"))
    b.add("Secret episode", SECRET, tags=["private"])
    bundle_dir = tmp / "okf"
    refused = False
    try:
        _bundle.export(b, str(bundle_dir))
    except Exception:
        refused = True
    b.con.close()
    chk("export REFUSES (raises) on private concept without key", refused)
    # and crucially: no plaintext secret anywhere in the bundle dir
    leaked = False
    if bundle_dir.exists():
        for f in bundle_dir.rglob("*.md"):
            if SECRET in f.read_text(encoding="utf-8"):
                leaked = True
    chk("no plaintext secret leaked to the bundle", not leaked)

# ── Phase 7: EXEC subprocess ─────────────────────────────────────────────────
print("Phase 7: subprocess encrypt->write->read-raw asserts ciphertext")
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    kp = with_key(tmp)
    script = (
        "import sys; sys.path.insert(0, r'%s')\n" % str(ROOT / 'scripts') +
        "import crypto\n"
        "tok = crypto.encrypt('TOPSECRETxyz')\n"
        "open(r'%s','w',encoding='utf-8').write(tok)\n" % str(tmp / 'out.txt') +
        "raw = open(r'%s',encoding='utf-8').read()\n" % str(tmp / 'out.txt') +
        "assert 'TOPSECRETxyz' not in raw, 'LEAK'\n"
        "assert crypto.decrypt(raw) == 'TOPSECRETxyz', 'ROUNDTRIP'\n"
        "print('OK')\n"
    )
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "SECONDBRAIN_KEY_FILE": str(kp)})
    chk("subprocess encrypt/roundtrip OK", r.returncode == 0 and "OK" in (r.stdout or ""),
        (r.stdout or "") + (r.stderr or ""))

print()
if errors:
    print(f"RESULT: FAIL ({len(errors)} failures: {errors})")
    sys.exit(1)
print("RESULT: PASS")
