# 04 — Psychological / Emotional Memory

This is the differentiator: SecondBrain as a foundation for emotional/psychological **mimic agents**
(cf. the `bbju` and `create-ex` persona skills). Sync is plumbing; this is the product.

All additions are namespaced `sb_` so any OKF consumer round-trips them untouched.

## Memory kinds → OKF `type`
The OKF `type` field carries the kind. MVP vocabulary (extensible; never centrally registered):

`Note` · `Trait` (stable personality) · `Value` · `Pattern` (habit / behavioral) ·
`Episode` (emotional event) · `RelationshipModel` · `Person` (a subject) · `Reference`.

Consumers must tolerate unknown types — so adding a kind later never breaks an existing Bundle.

## Subjects — "who is this memory about"
A **subject** is itself a Concept of `type: Person` at `people/<slug>.md`. Any memory points at its
subject via `sb_subject: /people/<slug>.md` (default `/people/self.md` = the user).

This makes mimic agents first-class: **a person's psychology is just the sub-graph of Concepts whose
`sb_subject` is them.** Building a persona of Rox = querying `sb_subject == /people/rox.md` across
Traits, Values, Patterns, Episodes, RelationshipModels. The `bbju` / `create-ex` skills become
consumers of this sub-graph rather than maintaining their own private store.

## Temporal validity — "what was true when" (the Zep/Graphiti capability)
```yaml
sb_valid_from: 2024-01-01T00:00:00Z   # when this became true
sb_valid_to:   2025-06-01T00:00:00Z   # null/absent = still true
sb_supersedes: /traits/rox-distant.md # the fact this replaced
```
Editing a fact doesn't destroy history — it sets `sb_valid_to` on the old Concept and writes a new
one with `sb_supersedes`. Git keeps byte-level history; `sb_supersedes` keeps the semantic chain.
An agent reasoning about a past state filters Concepts by validity window.

## Structured affect (optional, nullable)
```yaml
sb_affect:
  valence: -0.6        # -1..1  (unpleasant..pleasant)
  arousal: 0.7         #  0..1  (calm..activated)
  emotion: "longing"   # free-string named emotion (optional)
  intensity: 0.8       #  0..1
```
Structured enough for agent reasoning, optional enough that a plain Note carries none.

## Other `sb_` keys
`sb_confidence` (0..1) · `sb_relations` (typed-edge mirror `[{to, type, strength}]`) ·
`sb_private: true` (encryption flag — see [05](./05-backends-and-encryption.md)).

## Derived DB tables (rebuilt from frontmatter, never authoritative)
- `subjects(sb_id, slug, display_name, kind)` — one row per `type: Person`.
- `affect(concept_id, valence, arousal, emotion, intensity)`.
- validity columns on `concepts`: `valid_from`, `valid_to`, `supersedes_id`.
- `concept_subject(concept_id, subject_id)` index for fast persona sub-graph queries.

Because the DB is disposable, these evolve freely: change the serializer, rebuild.

## New/extended CLI surface
- `/brain-recall <subject> [--as-of <date>]` — persona sub-graph, optionally at a past moment.
- `/brain-add` gains `--type`, `--subject`, `--affect`, `--valid-from`.
- Supersede flow: updating a temporal fact offers "supersede (keep history)" vs "edit in place".
