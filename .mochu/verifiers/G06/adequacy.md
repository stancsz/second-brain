# G06 — Verifier Adequacy Audit

Claim: concurrent edits to the *same* concept on two devices park as `<slug>.conflict.md`
instead of crashing sync or silently clobbering one side.

## The three lazy artifacts (summary list)

1. Crash-or-abort — sync raises on the rebase conflict (or leaves a half-finished rebase), so the
   user is stuck with a broken working tree.
2. Silent clobber — sync "resolves" by taking one side (e.g. always theirs) and discarding the
   other edit entirely, with no conflict copy.
3. Poison import — the conflict copy is imported as a second drawer (duplicate concept) or the
   leftover rebase markers corrupt the rebuilt brain.

## How the suite blocks each

- **Artifact 1** — wraps `sync()` in try/except and fails if it raises; asserts no
  `.git/rebase-merge` / `rebase-apply` remains and `git status --porcelain` is empty.
- **Artifact 2** — asserts BOTH "A's version of the body" and "B's totally different body" survive
  somewhere in the bundle (canonical + conflict copy). Losing either fails.
- **Artifact 3** — asserts exactly ONE `Shared` drawer in the rebuilt brain (conflict copies must
  not be imported) and that a follow-up sync does not crash or re-conflict perpetually.

## Strongest-pattern check
Real two-clone git topology forcing an actual rebase conflict on the same file, driving the real
`scripts/sync.py`; assertions inspect on-disk bundle, git state, and the rebuilt brain.

## Out of scope (own gaps)
A `/brain-conflicts` and `/brain-resolve` slash-command UX (thin wrappers over `conflicts()`),
and automatic three-way *content* merging — parking + listing is the safety guarantee here.
