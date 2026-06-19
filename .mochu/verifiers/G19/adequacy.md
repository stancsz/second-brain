# G19 — Verifier Adequacy Audit

Claim: the proactive recall hook emits its recall block (with the matching note, unicode intact)
even under a non-UTF-8 (cp1252) stdout, while filler prompts stay silent.

## The three lazy artifacts (summary list)

1. Still-silent — the emoji print still crashes under cp1252 and the never-block handler swallows
   it, so recall emits nothing (the original bug, unfixed).
2. Lossy strip — "fix" by deleting the emoji / all non-ASCII, which would mangle unicode note
   titles and content.
3. Over-eager — make it always print something, losing the "stay silent on filler" guarantee.

## How the suite blocks each

- **Artifact 1** — runs the real hook as a subprocess with `PYTHONIOENCODING=cp1252` and asserts
  the output contains the `second-brain` label and the matching note title. A swallowed crash =
  empty output = fail.
- **Artifact 2** — includes a CJK-titled note and asserts the exact CJK title (a 5-char Chinese
  string, see verify_recall.py) appears in the cp1252-run output, so a strip-non-ASCII fix fails.
- **Artifact 3** — sends `ok thanks` and asserts empty output, preserving filler-silence.

## Strongest-pattern check
Executes the actual hook binary as a separate process under the exact hostile encoding, decoding
its stdout as UTF-8 — reproducing the real Windows failure mode rather than calling internals.

## Out of scope (own gaps)
FTS morphological matching / stemming (a separate possible enhancement) — the recall *match* already
works; this gap is strictly the output-encoding crash.
