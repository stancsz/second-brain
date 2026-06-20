---
name: brain
description: Quick access to SecondBrain — add, search, show, list, or summary without remembering the CLI shape.
---

# /brain — SecondBrain shortcut

Wraps the most common `brain_cli.py` actions so the user can do them in
natural language without remembering subcommand names or flags. The CLI
itself stays the source of truth — this just translates intent.

## Forms

Match the user's phrasing to the right subcommand. If they say:

- `/brain add "Title" "Content" [tags]` → save a concept.
  - Infer 2–5 tags, pick a collection if obvious (use the four-collection
    taxonomy `Decisions` / `Preferences` / `Facts` / `Knowledge` only if
    the content is clearly distilled conversational know-how; otherwise
    use a topic collection or no collection).
  - Command: `brain add "<title>" "<content>" [--collection C] [--tags a,b]`.
- `/brain search "query"` → find notes.
  - Command: `brain search "<query>" [--collection C] [--tag T] [--limit N]`.
  - Synthesize a short answer citing 8-char concept ids. Don't dump raw results.
- `/brain show <id-or-title>` → open one concept.
  - Command: `brain show <id-or-title>`. If title is ambiguous, list matches
    and ask which.
- `/brain list [--collection X]` → browse.
  - Command: `brain list [--collection C] [--tag T] [--limit N] [--sort updated|created|title]`.
- `/brain summary` → brain health.
  - Command: `brain summary`. Propose action if it recommends, never act
    unprompted on `archive` or `distill --activate`.
- `/brain recall <person>` → "what do I know about <person>?" (psych subjects).
  - Command: `brain recall-subject <person-or-path>`. Accepts a path
    (`/people/rox.md`) or a name (`rox`, `Rox`). Returns the live
    subject sub-graph: every Concept tagged `sb_subject: /people/<name>.md`
    (or the implicit `/people/self.md` for unset memories). Pair with
    `/brain show <id>` to read the most relevant 1–2 entries.
- `/brain recall <emotion / mood>` → "find the memories that felt like X" (psych affect).
  - Command: `brain recall-affect [--emotion E] [--min-intensity N]
    [--min-valence N] [--max-valence N] [--min-arousal N] [--max-arousal N]`.
    Filters by structured affect: `--emotion grief` (exact, case-insensitive),
    or numeric ranges on valence (pleasant +1 .. unpleasant −1), arousal, and
    intensity (0..1). Combine them — `--emotion grief --min-intensity 0.7`
    returns only the most intense grief memories. Results are full Concepts
    ordered by intensity.
  - To capture affect on a memory, pass `--affect` to `add`/`update`:
    `brain add "<title>" "<content>" --affect '{"emotion":"grief","valence":-0.8,"intensity":0.9}'`
    (any subset of the four dimensions). `brain show <id>` prints the affect line.
- Temporal facts that change over time → give them a validity window.
  - Capture: `brain add "<title>" "<content>" --valid-from 2020-01-01 [--valid-to 2023-06-01]`.
    A fact with no window is treated as valid since creation, still valid.
  - When a fact is corrected/replaced, don't overwrite — **supersede** it:
    `SecondBrain.supersede(old_id, "<new title>", "<new content>", as_of="2023-06-01")`
    closes the old fact's window at `as_of` and adds the new fact linked to it,
    keeping the old one as history. `brain show <id>` prints the `⏳ Valid:`
    window. (Point-in-time `recall --as-of <date>` lands in the next iteration.)

## Output rules

- For each action, run the matching `brain_cli.py` subcommand. Add `--json`
  only if you need to parse the output; omit it for human-readable text.
- Be quiet: one short line per save, no echo of the full CLI invocation.
- No-op: silent unless the user explicitly asked for confirmation.

## Vague phrasing

If the user is loose ("catch me up on Braid", "what do I know about RAG?"),
interpret as the most-likely action: `list --collection Braid --sort updated`
for prep, `search RAG` for recall. Read the top 5, give a 3-paragraph brief,
surface the most-linked concept (`related` / `traverse`).

## Examples

- `/brain add "Attention Is All You Need" "<abstract>" --collection Research --tags ml,transformers,paper`
- `/brain search second-brain`
- `/brain list --collection Braid --sort updated`
- `/brain summary`

## Other slash commands

- `/history` (in `commands/history.md`) — browse raw conversation logs at `~/.secondbrain/logs/`.
- `/brain` (this file) — operate on the brain itself.
