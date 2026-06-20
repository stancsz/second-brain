#!/usr/bin/env python3
"""G19 verifier — proactive recall hook emits under a non-UTF-8 console.

Real bug: the hook prints a '🧠' header; on a Windows cp1252 stdout the print
raises UnicodeEncodeError, the hook's never-block handler swallows it, and recall
silently emits NOTHING — so on every cp1252 machine the user gets no proactive
recall even when a relevant note exists. (Originally mis-filed as "FTS has no
stemming"; the FTS match is fine — the output encoding is the bug.)

Claim: under a cp1252 stdout the hook still emits its recall block with the
matching note (and unicode titles survive intact), while filler prompts stay
silent. Executes the real hooks/recall_memories.py as a subprocess with
PYTHONIOENCODING=cp1252.
"""
import sys, os, subprocess, tempfile, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
from brain import SecondBrain  # noqa: E402

HOOK = REPO / "hooks" / "recall_memories.py"
fails = []


def check(c, m):
    if not c:
        fails.append(m)


def run_hook(prompt, db):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"   # simulate a Windows non-UTF-8 console
    env["PYTHONUTF8"] = "0"
    env["SECONDBRAIN_DB"] = str(db)
    env.pop("SECONDBRAIN_SKIP_RECALL", None)
    r = subprocess.run([sys.executable, str(HOOK)],
                       input=('{"prompt":%s}' % _json(prompt)).encode("utf-8"),
                       capture_output=True, env=env)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def _json(s):
    import json
    return json.dumps(s)


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        db = tmp / "b.db"
        b = SecondBrain(db)
        b.add("Checkout timeout fix", "raised gateway timeout to 30s",
              collection="Engineering")
        # CJK note recalled by an EXACT CJK token (FTS5 unicode61 treats a CJK
        # run as one token, so we match a whole token, not a substring).
        b.add("迁移笔记", "数据库 部署 notes", collection="工程")
        b.close()

        # 1. Relevant prompt under cp1252 -> must emit the recall block + note.
        rc, out = run_hook("why does checkout keep timing out?", db)
        check(rc == 0, f"hook exited nonzero: {rc}")
        check("second-brain" in out,
              "recall produced NO output under cp1252 (emoji-print crash swallowed)")
        check("Checkout timeout fix" in out,
              f"recall did not surface the matching note; out={out!r}")

        # 2. Unicode note recalled intact (blocks a lazy 'strip all non-ASCII' fix).
        rc2, out2 = run_hook("数据库", db)
        check(rc2 == 0 and "迁移笔记" in out2,
              f"unicode note not surfaced intact under cp1252; out={out2!r}")

        # 3. Filler prompt stays silent (no spurious recall).
        rc3, out3 = run_hook("ok thanks", db)
        check(rc3 == 0 and out3.strip() == "",
              f"filler prompt should produce no recall, got: {out3!r}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("RECALL FAIL:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("RECALL PASS: hook emits recall (incl. unicode) under cp1252; filler stays silent")


if __name__ == "__main__":
    main()
