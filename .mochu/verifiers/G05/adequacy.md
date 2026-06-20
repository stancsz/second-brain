# G05 — Verifier Adequacy Audit

Claim: a git-backed `sync()` makes memory portable across devices — serialize → commit →
pull --rebase → push → rebuild — so two devices sharing a remote converge.

## The three lazy artifacts (summary list)

1. Push-only — commits and pushes local state but never pulls, so device B never sees A (and A
   never sees B's later edits). Looks like "sync" on one machine, silently one-way.
2. No rebuild — pulls files but never rebuilds brain.db, so the pulled OKF concepts never become
   queryable drawers (db stays stale).
3. Non-deterministic export — re-serializes unchanged drawers with churn (reordered keys, shifting
   timestamps), producing spurious commits/merge conflicts on every sync.

## How the suite blocks each

- **Artifact 1** — the test drives a true bidirectional scenario: A creates content and pushes;
  B (fresh clone) syncs and MUST see A's drawers; then B creates content and pushes; A syncs and
  MUST see B's. A push-only implementation fails both the B-receives-A and A-receives-B assertions,
  and the final convergence assertion (`titles(A) == titles(B)`).
- **Artifact 2** — after B's sync, the test opens B's brain.db and asserts the drawers and a
  wikilink relation are actually present and queryable — which only holds if sync rebuilt the db
  from the pulled bundle.
- **Artifact 3** — a final no-change `sync()` asserts `committed` is False; any non-deterministic
  re-serialization would dirty the tree and fail.

## Strongest-pattern check
Real git: a bare repo as remote and two working clones as devices A/B, driving the actual
`scripts/sync.py`. Convergence and queryability are asserted on observable state, not logs.

## Out of scope (own gaps)
Conflicting concurrent edits to the *same* concept (G06 conflict parking), tombstone deletes over
git (G07), and cloud backup mirrors (G11+). This verifier covers non-conflicting multi-device sync.
