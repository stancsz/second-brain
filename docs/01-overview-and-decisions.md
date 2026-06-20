# 01 — Overview & Locked Decisions

## Goal
Make SecondBrain **production-ready, portable, and format-agnostic**, backed up on a schedule to
multiple destinations, natively speaking Google's **Open Knowledge Format (OKF)**, and extended to
serve as a **foundation for emotional / psychological mimic agents**.

Three intertwined upgrades:
1. **Portability & backup** — git as the bidirectional sync spine; S3/GCS/Google Drive/OneDrive as one-way backup mirrors.
2. **OKF-native storage** — Concepts are OKF markdown files; SQLite is a rebuildable index.
3. **Psychological memory** — temporal validity, subjects, structured affect, first-class memory kinds.

## Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Source of truth | **OKF files on disk** | Deletes the DB-vs-file conflict problem; SQLite becomes a <5s rebuildable cache. |
| Sync model | **Git spine + one-way backups** | Git already is a hardened multi-master, offline, conflict-resolving sync engine. Don't rebuild it over Drive's API. |
| On-disk format | **Markdown + OKF YAML frontmatter** | This *is* native OKF v0.1. Human-readable, diffable, Obsidian-compatible. |
| OKF fidelity | **Follow OKF as closely as possible; rename our model to match** | `concept`→`Concept`, etc. Our richness rides in `sb_*` keys, which OKF blesses. |
| Psych schema | Temporal validity + subjects + structured affect + trait/value/pattern kinds | The actual differentiator; sync is plumbing. |
| Encryption | **Selective by tag** | Plaintext+diffable for normal notes; `private`/`psych` Concepts encrypted before push. |
| Deps | **Minimal, justified, lazy-imported** | Core dep-free; adapters import their SDK only when used. |
| Scheduling | **Hook + cron** | Hook commits/pushes opportunistically; OS scheduler is the guaranteed backstop. |

## The core architectural challenge that shaped this
The original ask implied bidirectional sync to five backends at once. That's building a distributed
database over consumer cloud APIs. We rejected it in favor of: **files are the single source of
truth, git is the single bidirectional channel, every cloud target is a dumb one-way mirror.** This
single inversion removes the majority of the distributed-systems risk for zero capability loss, and
frees the complexity budget for the psychological layer — the part git can't give us for free.
