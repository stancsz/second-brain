# 03 — Sync Architecture

```
        ┌─────────────────────────────────────────────┐
        │  ~/.secondbrain/okf/   ← BUNDLE = SOURCE OF TRUTH (git work tree)
        │     people/  traits/  notes/  episodes/ …    │
        └───────┬───────────────────────────┬─────────┘
       serialize│                    rebuild │ (walk files → SQLite)
                ▼                            ▼
        ┌──────────────┐            ┌──────────────────┐
        │ brain.db     │  ← derived cache: FTS + graph + temporal index
        └──────────────┘            └──────────────────┘
                │
   git commit/push/pull  ← THE ONLY bidirectional channel (multi-device)
                │
        ┌───────┴────────────────────────────────────┐
        │            one-way backup fan-out            │
        ▼            ▼            ▼            ▼        ▼
       S3          GCS      Google Drive   OneDrive  (any future Backend)
```

## Files are truth; SQLite is disposable
The Bundle is authoritative. `brain.db` is rebuilt by walking the Bundle. Reserved `index.md` /
`log.md` per directory are **generated** on serialize, never hand-authoritative. Schema migrations
become "bump the serializer + rebuild" — no fragile in-place `ALTER`.

## The sync loop — `brain sync`
1. **Serialize** any DB-side edits since last sync into OKF files. (CLI writes go to files first
   anyway; this catches batch ops.)
2. `git add -A && git commit` (skip if clean).
3. `git pull --rebase` → git performs the multi-device merge.
   - **Conflicts:** each Concept is its own file, so conflicts are scoped to a single Concept.
     Git conflict markers land in the file; `brain sync` detects them, parks the Concept as
     `<slug>.conflict.md`, and surfaces a `/brain-conflicts` list for human/agent resolution.
     (Per-file granularity is *why* we chose one-file-per-Concept.)
4. `git push`.
5. **Rebuild** the DB from the merged Bundle so FTS/graph reflect remote changes.
6. **Backup fan-out:** mirror the Bundle tree to each configured `Backend` (one-way).

## Scheduling — hook + cron
- **Hook** (`Stop` / post-capture): runs steps 1–2 (+ 3–5 if a remote is configured) so a session's
  captures are committed promptly. Cheap, best-effort, non-blocking.
- **Cron / Windows Task Scheduler** (`brain sync --full`, e.g. every 30 min): the guaranteed
  backstop that also does pull + backup fan-out even when Claude isn't open. Installed by
  `install.sh` (Task Scheduler entry on Windows; cron line on *nix).

## Multi-device & deletes
- Identity is `sb_id`, so a Concept renamed on device A and edited on device B reconciles by id.
- Deletes propagate as **tombstones**: soft delete writes `sb_deleted: <ts>` to frontmatter and
  moves the file to `.trash/` (git tracks the move; remote sees the deletion). `restore` reverses
  it. Hard delete removes the file. Delete stays a normal git diff.

## Conflict UX contract
- `/brain-conflicts` — list parked `*.conflict.md` Concepts.
- `/brain-resolve <id> --keep ours|theirs|merged` — resolve and re-serialize.
- Unresolved conflicts never block capture; new Concepts still write normally.
