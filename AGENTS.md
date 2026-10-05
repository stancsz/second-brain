# Project-wide agent instructions

## Second Brain task checkpoints

Before ending a substantive task in this repository, save or update a concise
task checkpoint in the user's Second Brain. This applies to partial, blocked,
and completed work, including work performed by subagents. Do not create a
checkpoint for ordinary Q&A or when no meaningful project work occurred.

Use a `Work` concept with a title that identifies this project and the task.
Record:

- completion estimate from 0–100% (use 100% only when the requested outcome is
  actually complete);
- what changed or was accomplished;
- remaining work or blockers;
- verification performed and its result, or state that verification was not run.

Search for the same task before adding. Update its existing concept when there
is a clear match; otherwise add a new one. Use the Second Brain CLI or its
connected MCP tools as described in `SKILL.md`. Never save the raw transcript.
If the brain is unavailable, say so in the final response and do not claim the
checkpoint was saved.

Finish the response with exactly one checkpoint marker:

- `SECOND_BRAIN_CHECKPOINT: saved` after a successful add or update;
- `SECOND_BRAIN_CHECKPOINT: skip` when no meaningful project work occurred;
- `SECOND_BRAIN_CHECKPOINT: unavailable` when the Second Brain could not be
  reached.
