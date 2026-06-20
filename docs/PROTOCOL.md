# docs/ Protocol — architect ⇄ builder wire format

> The repo's existing `docs/README.md` is the **project** readme, so this protocol copy lives
> here at `PROTOCOL.md`. The builder learns the rules from this file.

Two instances — the **architect** (design + decisions) and the **builder** (implementation, here:
the mochu loop) — coordinate only through files in `docs/`. They never share memory and never talk
directly. The whole conversation must be reconstructable from the files alone.

## Folder layout
```
docs/
  PROTOCOL.md          # this file (architect writes on bootstrap)
  brief.md             # north star: vision, current state, principles, open arcs (architect owns)
  board.md             # status board — read first
  tasks/      T###.md   # architect → builder
  reports/    T###-R#.md# builder → architect (R# = revision)
  decisions/  D###.md   # co-authored ADRs, addressable by ID
```
The numbered files (`01-…`–`08-…`), `HANDOFF.md`, `CHANGELOG.md` are the project's own narrative docs
and are untouched by this protocol.

## IDs
- `T###` — a task (monotonic, never reused).
- `T###-R#` — a report tied to its task, numbered by revision.
- `D###` — a decision (monotonic). Front-matter carries the related IDs so the thread is explicit.

## Front-matter
**Task** `tasks/T###.md`: `id, status (open|building|blocked|done), title, depends_on[], governed_by[], oversight (proposal-first|standard|trusted)`
**Report** `reports/T###-R#.md`: `task, rev, status (proposal|complete|blocked|needs-decision), raises[]`
**Decision** `decisions/D###.md`: `id, status (open|ruled|superseded), raised_by, governs[], supersedes`

## Turn loops
**Builder:** read board → read brief + consume newly `ruled` decisions → take next `open` task whose
`depends_on` are `done` and `governed_by` are `ruled` → if `proposal-first`, write a proposal report and
stop; else build, run, test, write a report with **mandatory evidence** (command + outcome) and a
structure map. On a load-bearing fork, open a `D###`, set the report `needs-decision`, stop the task.

**Architect:** read board first → rule every `needs-decision`/`blocked` (Ruling + Consequence, flip to
`ruled`) → verify every `complete` against acceptance criteria → check arc drift, update brief → issue or
adjust tasks. **Never reads source** — if a report is insufficient, that's a report-quality fix, not a
reason to break the barrier.

## Hard rules
- Evidence is mandatory at every oversight level. No "it works" without a command and an outcome.
- The builder never assumes a load-bearing choice — it opens a decision and stops.
- Status flips are the clock: a report isn't addressed until its decision is `ruled` and its task moves.

## How this maps onto mochu (this repo)
The **mochu loop is the builder**. A mochu gap (`G##`) is implemented under an architect task (`T###`).
The mochu ratchet corpus (`.mochu/verifiers/`) + `scripts/ship_gate.py` are the builder's evidence engine;
their green/exit-0 output is the "command + outcome" this protocol requires.
