# 02 — OKF v0.1 & the SecondBrain → OKF Rename

## OKF v0.1 in one screen
Source: `GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md` (v0.1, 2026-06-12).

- A **Knowledge Bundle** = a directory tree of markdown files. The unit of distribution.
- A **Concept** = one markdown file = `YAML frontmatter` + `markdown body`.
- **Concept ID** = file path within the bundle, minus `.md`. e.g. `people/rox.md` → `people/rox`.
- **Frontmatter:** one **REQUIRED** field `type` (free string). Recommended: `title`,
  `description`, `resource`, `tags` (list), `timestamp` (ISO 8601). Producers MAY add any keys;
  consumers MUST preserve unknown keys and MUST NOT reject unknown ones.
- **Links** = standard markdown links, **untyped**; relationship meaning lives in prose.
  Bundle-relative form `/dir/file.md` is recommended (stable across moves). Broken links are legal.
- **Reserved files:** `index.md` (directory listing; the only place `okf_version` may be declared)
  and `log.md` (date-grouped change history, newest first).
- **Conformance:** every non-reserved `.md` has parseable frontmatter with a non-empty `type`.
  Everything else is soft guidance.

## The rename — OKF terminology becomes canonical
We adopt OKF names throughout code, schema, CLI, and docs. Where SecondBrain and OKF disagree, OKF wins. The v2.1 model term was renamed to `Concept` everywhere — schema, CLI, hooks, docs (see the
comparison in `.mochu/ledger.md` iter-12 and the v2.1→v3.0 migration in
`scripts/brain.py:_migrate_v21_to_concepts`). What follows describes the
**current** canonical state.

| Canonical term | Where it lives | Notes |
|---|---|---|
| **Concept** | one markdown file | Table `concepts`; CLI `/brain-add` writes a Concept. |
| **`sb_id`** (UUID) | frontmatter | Durable identity; the OKF Concept ID (path) is the human address. |
| **body** | markdown body | The actual content of the Concept file. |
| **collection** (kept) | subdirectory under the bundle root | OKF leaves directory grouping to producers; `collection` = the Concept's subdirectory within the Bundle. Fully OKF-legal. |
| **Bundle** | the vault directory `~/.secondbrain/okf/` | The whole store. |
| **tags** | frontmatter list | Already matches OKF. |
| **Link** | markdown link + `sb_relations` mirror | Emitted as OKF bundle-relative markdown links; typed edges mirrored in `sb_relations`. |
| **`resource`** + **`# Citations`** | frontmatter + body | `resource` = first canonical URI; rest go under a `# Citations` section. |
| **`timestamp`** | frontmatter | ISO 8601. |
| **`sb_deleted`** | frontmatter | Tombstone timestamp; file moved to `.trash/`. |

> Migration keeps the UUIDs: each existing v2.1 record's UUID becomes that Concept's `sb_id`.

## Model mapping

| SecondBrain | OKF representation |
|---|---|
| Bundle root (`~/.secondbrain/okf/`) | Knowledge Bundle root (git work tree) |
| `collection` | Subdirectory under the bundle root |
| Concept | Concept file `<collection>/<slug>.md` |
| `sb_id` (UUID) | frontmatter key — rename-safe identity |
| title | `title` |
| body | markdown body |
| tags | `tags` |
| sources | `resource` + `# Citations` |
| timestamp | `timestamp` |
| Link (typed) | plain OKF markdown link **+** `sb_relations` frontmatter mirror |
| FTS / pending links / `_meta` | **not serialized** — derived, rebuilt from files |

## Example Concept (psychological, with `sb_*` extensions)
```markdown
---
type: Episode
sb_id: 7f3a2c91-...-9b21
title: First real fight with Rox
description: Argument about silence; she went distant for three days.
sb_subject: /people/rox.md
tags: [relationship, conflict, private]
timestamp: 2026-06-18T20:14:00Z
sb_valid_from: 2024-11-02T00:00:00Z
sb_affect:
  valence: -0.7
  arousal: 0.6
  emotion: "hurt"
  intensity: 0.8
sb_relations:
  - { to: /traits/rox-conflict-avoidant.md, type: expands, strength: 0.8 }
---

The argument started over [a missed call](/episodes/missed-call.md) …

# Citations
[1] [original chat export](/references/wechat-2024-11.md)
```

## `sb_id` ↔ path
OKF's Concept ID is the path, but edges and cross-device merges need a stable identity that
survives renames. Resolution: **`sb_id` is the durable identity; the path is a human-friendly
address.** The DB keys on `sb_id`; links are emitted by path and re-resolved to `sb_id` on import.
External OKF consumers still get working path-links; we get rename-safe internal edges.
