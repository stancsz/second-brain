# 06 — Build Plan

Phased and testable. Each phase ends green on `tests/` before the next begins. mochu iterates here.

## Phase A — OKF serializer + rebuildable DB (the keystone)
- `okf.py`: Concept ⇄ markdown file (frontmatter parse/emit, `sb_*` keys, links by path↔`sb_id`).
- `rebuild()`: walk Bundle → fresh `brain.db` (concepts, tags, links, FTS).
- Generate `index.md` / `log.md`; pin `okf_version: "0.1"` in root `index.md`.
- Rename `drawer`→`Concept` across schema/CLI/code (see [02](./02-okf-and-terminology.md)).
- **Test:** round-trip identity — `DB → files → DB` reproduces the store; OKF conformance lint passes.
- **Ships:** portability + Obsidian compatibility, *no sync yet*.

## Phase B — Git sync spine
- `brain sync`: serialize → commit → `pull --rebase` → push → rebuild.
- Conflict parking (`*.conflict.md`) + `/brain-conflicts` + `/brain-resolve`.
- Tombstone deletes (`sb_deleted` + `.trash/`).
- Hook (`Stop`) + OS scheduler install in `install.sh`.
- **Test:** simulated two-clone divergence merges cleanly; conflicting edits park, not clobber.

## Phase C — Psychological schema
- `sb_*` keys; `subjects` / `affect` / validity tables; `type` vocabulary; supersede flow.
- `/brain-recall <subject> [--as-of]`; `/brain-add` gains `--type/--subject/--affect/--valid-from`.
- Wire `bbju` / `create-ex` personas to read their subject sub-graph.
- **Test:** as-of queries return the correct historical state; persona sub-graph is complete.

## Phase D — Backup adapters + encryption
- `Backend` interface; `S3`/`GCS`/`GDrive`/`OneDrive` adapters (MCP-first where available).
- `sync.toml`; age selective encryption; fan-out in `sync --full`; `brain restore`.
- **Test:** push→wipe→restore→rebuild reproduces the Bundle; private Concepts are ciphertext on remote.

## Phase E — Hardening
- Incremental rebuild (mtime-based) for large Bundles; `brain okf-lint` conformance validator.
- Migration from current v2.1 `brain.db` → OKF Bundle; perf targets from architecture.md.
- Docs refresh; `SKILL.md` updated to OKF terminology.

## Open risks
- **Rebuild cost at scale** — full walk fine to tens of thousands; Phase E adds incremental reindex.
- **Git is a hard dependency** — `install.sh` must `git init` the Bundle and offer to set a remote.
- **Encrypted-body search gap** — by design; titles/tags stay searchable. Optional later: local-only encrypted FTS shadow.
- **OKF is v0.1 draft** — pin `okf_version`; keep richness in `sb_*` so a spec bump can't break us.

## Decisions resolved (2026-06-18)
1. **Bundle location** — its **own private git repo at `~/.secondbrain/okf/`**, separate from this skill
   repo. Personal/psychological data never mixes with publishable skill code. `install.sh` `git init`s it
   and offers to set a remote. (A future `sync.toml` `bundle_path` may relax this, but the default is fixed.)
2. **Migration** — **migrate the existing v2.1 `brain.db` → OKF Bundle as Phase A's first real test.**
   The migration is the round-trip proof on real data; nothing is orphaned.
3. **Git workflow** — **feature branch `mochu/<gap-id>` + PR per mochu iteration**, human-gated merge to
   `main`. `product.md` records the human gates merges.
