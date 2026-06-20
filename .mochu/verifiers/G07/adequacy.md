# G07 — Verifier Adequacy Audit

Claim: deletes survive sync — soft-delete → `.trash/` tombstone that propagates, `restore`
reverses across devices, hard-delete removes the file with no resurrection.

## The three lazy artifacts (summary list)

1. Additive export — never removes files, so a hard-deleted concept's file lingers and the drawer
   resurrects on the next rebuild/sync.
2. Tombstone-in-place — marks sb_deleted but leaves the file in its live collection dir (clutters
   the bundle and index), never using `.trash/`.
3. One-way restore — restore clears sb_deleted locally but doesn't move the file back / doesn't
   propagate, so the other device keeps it dead.

## How the suite blocks each

- **Artifact 1** — hard-deletes "Purged", syncs, asserts no live OR trash file for it on A, that it
  is gone on B, and — crucially — re-syncs B twice asserting it does NOT resurrect.
- **Artifact 2** — after soft-deleting "Doomed", asserts the file is under `.trash/` AND absent from
  any live collection dir, on both A and B.
- **Artifact 3** — restores "Doomed" on A, asserts the file moved back to a live dir and left
  `.trash`, then syncs B and asserts "Doomed" is alive again on B.

## Strongest-pattern check
Real git two-clone topology driving `scripts/sync.py`; assertions inspect both the queryable brain
state (alive titles) and the actual on-disk bundle layout (`.trash/` vs live dirs) — observable
state, not logs. Convergence asserted at the end.

## Out of scope (own gaps)
Conflicting concurrent edits to the same concept (G06). This verifier covers delete/restore/hard-delete
propagation only.
