# RELEASE — Definition of Done (the loop's finish line)

SecondBrain is "production-ready, portable, OKF-native, psychology-capable" when all criteria pass
their named verifiers. Each line names the gap(s)/verifier(s) that satisfy it.

## Portability & OKF
- [x] R1 Every Concept persists as an OKF v0.1-conformant markdown file (frontmatter with non-empty `type`); `brain okf-lint` passes — verifier: okf-conformance (G01,G03) — DONE iter-10 (G01+G03 already passed; G20 verifier added in iter-10 to lock in spec-shape rules: okf_version in index.md frontmatter, subdir indexes have no frontmatter, every concept has type, no concept has okf_version; the `brain okf-lint` CLI subcommand is not built — R1's binding verifier is G01+G03, not the CLI)
- [x] R2 Round-trip identity: `DB → files → DB` reproduces the store byte-for-meaning — verifier: okf-roundtrip + bundle-rebuild (G01,G02) — DONE iter-2
- [x] R3 SQLite is fully rebuildable from files; deleting brain.db and running `rebuild` loses nothing — verifier: bundle-rebuild (G02) — DONE iter-2
- [x] R4 Model/terminology is OKF-canonical (`Concept`, not `drawer`) across code + CLI + schema + tests; docs surface (commands/, docs/, references/, README.zh.md, CHANGELOG historical entries) tracked as G23 — verifier: schema-rename (G04) — DONE iter-12 (M1+M2)

## Sync & survivability
- [x] R5 `brain sync` round-trips through a git remote; a second clone sees the same Bundle — verifier: git-sync (G05) — DONE iter-4
- [x] R6 Divergent edits on two clones park as `*.conflict.md` instead of clobbering — verifier: conflict (G06) — DONE iter-6
- [x] R7 A delete on clone A propagates to clone B (tombstone) and `restore` reverses it — verifier: tombstone (G07) — DONE iter-5
- [ ] R8 Push → wipe → restore → rebuild reproduces the Bundle from at least one cloud backend — verifier: backup-restore (G11)
- [ ] R9 Scheduled sync runs unattended (hook + OS scheduler installed by install.sh) — verifier: scheduler-install (G15)

## Psychological memory (mimic-agent foundation)
- [ ] R10 Memories carry a subject; a persona sub-graph query returns exactly that subject's Concepts — verifier: subject-subgraph (G08)
- [ ] R11 `--as-of <date>` recall returns the historically-valid state; superseded facts are excluded — verifier: temporal-asof (G09)
- [ ] R12 Structured affect persists and is queryable per Concept — verifier: affect-persist (G10)

## Trust
- [ ] R13 `private`/`psych`/`Episode`/`RelationshipModel` Concepts are ciphertext on the remote; plaintext notes stay diffable — verifier: selective-encryption (G13)
- [x] R14 No secrets ever committed; sync.toml secrets via env/keyring — verifier: secret-scan (ship_gate) — DONE iter-11 (ship_gate's diff scan + G22's git-history + config-shape scan together cover both halves)

## Docs
- [x] R15 SKILL.md + README describe the OKF model and every shipped capability; a stranger can install and sync — verifier: docs-executable (G14) — DONE iter-9
