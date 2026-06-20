# RELEASE — Definition of Done (the loop's finish line)

SecondBrain is "production-ready, portable, OKF-native, psychology-capable" when all criteria pass
their named verifiers. Each line names the gap(s)/verifier(s) that satisfy it.

## Portability & OKF
- [x] R1 Every Concept persists as an OKF v0.1-conformant markdown file (frontmatter with non-empty `type`); `brain okf-lint` passes — verifier: okf-conformance (G01,G03) — DONE iter-10 (G01+G03 already passed; G20 verifier added in iter-10 to lock in spec-shape rules: okf_version in index.md frontmatter, subdir indexes have no frontmatter, every concept has type, no concept has okf_version; the `brain okf-lint` CLI subcommand is not built — R1's binding verifier is G01+G03, not the CLI)
- [x] R2 Round-trip identity: `DB → files → DB` reproduces the store byte-for-meaning — verifier: okf-roundtrip + bundle-rebuild (G01,G02) — DONE iter-2
- [x] R3 SQLite is fully rebuildable from files; deleting brain.db and running `rebuild` loses nothing — verifier: bundle-rebuild (G02) — DONE iter-2
- [x] R4 Model/terminology is OKF-canonical (`Concept`, not `drawer`) across code + CLI + schema + tests + docs surface (commands/, docs/, references/, README.zh.md); CHANGELOG historical entries intentionally out of scope (revisionism) — verifier: schema-rename (G04) + docs-surface-rename (G23) — DONE iter-13

## Sync & survivability
- [x] R5 `brain sync` round-trips through a git remote; a second clone sees the same Bundle — verifier: git-sync (G05) — DONE iter-4
- [x] R6 Divergent edits on two clones park as `*.conflict.md` instead of clobbering — verifier: conflict (G06) — DONE iter-6
- [x] R7 A delete on clone A propagates to clone B (tombstone) and `restore` reverses it — verifier: tombstone (G07) — DONE iter-5
- [ ] R8 Push → wipe → restore → rebuild reproduces the Bundle from at least one cloud backend — verifier: backup-restore (G11)
- [ ] R9 Scheduled sync runs unattended (hook + OS scheduler installed by install.sh) — verifier: scheduler-install (G15)

## Psychological memory (mimic-agent foundation)
- [x] R10 Memories carry a subject; a persona sub-graph query returns exactly that subject's Concepts — verifier: subject-subgraph (G08)
- [x] R11 `--as-of <date>` recall returns the historically-valid state; superseded facts are excluded — verifier: temporal-asof (G09) — DONE iter-18 (M2: `recall_as_of()` + `brain recall --as-of` CLI; timeless notes returned for all as_of; exclusive valid_to boundary; NYC→SF supersession point-in-time correctness; 7 new unit tests 130→137; corpus 17/17)
- [x] R12 Structured affect persists and is queryable per Concept — verifier: affect-persist (G10) — DONE iter-15 (typed `affect` table populated via bundle.rebuild + live add/update; `affect(id)` typed getter; `recall_by_affect()` categorical + numeric-range + combined queries; FK ON DELETE CASCADE; `brain recall-affect` CLI; round-trip stable)

## Trust
- [x] R13 `private`/`psych`/`Episode`/`RelationshipModel` Concepts are ciphertext on the remote; plaintext notes stay diffable — verifier: selective-encryption (G13) — DONE iter-22 (opt-in Fernet via lazy `cryptography`; private Concepts encrypted into a minimal OKF envelope on export, excluded from index.md/log.md, decrypted on rebuild; idempotent — no git churn on unchanged; strict `SECONDBRAIN_REQUIRE_ENCRYPTION` refuses to write private plaintext, default no-key path warns and never silently leaks)
- [x] R14 No secrets ever committed; sync.toml secrets via env/keyring — verifier: secret-scan (ship_gate) — DONE iter-11 (ship_gate's diff scan + G22's git-history + config-shape scan together cover both halves)

## Docs
- [x] R15 SKILL.md + README describe the OKF model and every shipped capability; a stranger can install and sync — verifier: docs-executable (G14) — DONE iter-9

## Retrieval & ecosystem (ratified 2026-06-20 from iter-18 competitive intel)
- [ ] R16 `search --semantic` recalls a synonym match FTS5 would miss when `sqlite-vec` is present, AND falls back to FTS5 with no crash when the extension is absent (the moat-protecting fallback leg is a first-class acceptance phase) — verifier: semantic-search (G29)
- [ ] R17 Every core brain operation (search/add/recall-as-of/recall-affect/recall-subject/show/related) is reachable over MCP; a third-party client can drive the brain with zero bespoke glue — verifier: mcp-server (G30)
