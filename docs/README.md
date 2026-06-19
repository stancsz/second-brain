# SecondBrain — Design Docs

Design documentation for the OKF-native, git-synced, psychology-aware evolution of SecondBrain.
These are the *target* design; the currently-shipped system is described in
[../references/architecture.md](../references/architecture.md) and will be migrated toward this.

Read in order:

1. [01-overview-and-decisions.md](./01-overview-and-decisions.md) — what we're building and why; locked decisions.
2. [02-okf-and-terminology.md](./02-okf-and-terminology.md) — OKF v0.1 summary and the SecondBrain→OKF rename (drawer→Concept, …).
3. [03-sync-architecture.md](./03-sync-architecture.md) — files-as-truth, git sync spine, scheduling, conflicts, deletes.
4. [04-psychological-memory.md](./04-psychological-memory.md) — temporal validity, subjects, affect, memory kinds (the differentiator).
5. [05-backends-and-encryption.md](./05-backends-and-encryption.md) — backup adapters and selective encryption.
6. [06-build-plan.md](./06-build-plan.md) — phased, testable build sequence + risks.
7. [07-pmf-and-gap-analysis.md](./07-pmf-and-gap-analysis.md) — competitive landscape, PMF, and detailed gap analysis.

**North star:** *follow OKF as closely as possible.* Where our model and OKF disagree on a name,
OKF wins. Our extensions live in namespaced `sb_*` frontmatter keys, which OKF explicitly blesses.
