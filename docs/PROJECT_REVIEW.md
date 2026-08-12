# Project review: the bar for world-class

**Reviewed:** 2026-08-12
**Verdict:** strong beta foundation; not yet a world-class product.

The architecture is now credible and unusually coherent: user-owned Markdown is
canonical, SQLite is disposable, the Python core stays dependency-light, and
Agent Skills, MCP, git, Obsidian-format notes, and immutable backups compose
around the same data model.

The product is **not** world-class yet. A world-class claim requires an unfamiliar
external user to install it, switch agents, recover after a wipe, and recommend
it without repository archaeology. The integrated tree proves much more than the
previous release, but it does not yet prove that full external journey.

## What this hardening tranche changed

- Added public CI for Ubuntu, Windows, and macOS on Python 3.10 and 3.14,
  plus a hosted public-release gate that runs the corpus and secret scan.
- Replaced the missing private `.mochu` dependency with a clean-clone public
  compile/test/secret-scan release gate.
- Validated the root package against both the local and official Agent Skills
  validators.
- Added a real MCP subprocess test for initialize, tool listing, add, and search.
- Added a read-only, content-free `brain_doctor.py` report for install, MCP,
  storage, journal, and paired-store checks.
- Added a content-free `host_matrix.py` report that distinguishes five-host
  package/MCP readiness from native host activation.
- Exercised the installer command with Claude Code, Codex, Gemini CLI, OpenCode,
  and Cline as named targets; additionally verified isolated MCP registration
  parsing for Gemini CLI 0.26.0, Codex 0.87.0, OpenCode 1.15.10, and Cline 3.0.51.
- Added deterministic, content-addressed local snapshots; a generic rclone
  provider surface; and lazy PostgreSQL/Supabase storage.
- Added verified restore staging, hash checks, unsafe-archive rejection, and
  recoverable replacement of an occupied destination.
- Improved Obsidian-format behaviour: recursive Markdown import, CRLF handling,
  aliases/fragments, and manual-relation OKF round-trip.
- Added sync preflight/ignore controls, a security policy, and a threat model.
- Added paired-store receipts, stale-writer refusal, direction-aware sync
  recovery, atomic staged rebuilds, and round-trip verification before a
  canonical generation is blessed.
- Replaced the broad README and landing page with evidence-bounded onboarding.
- Added a tag-driven release workflow that reruns validation, creates a source
  archive, and publishes SHA-256 checksums; no tagged run has been observed yet.

These are working-tree results. Remote GitHub Actions, Pages deployment, release
assets, and provider accounts remain separate evidence gates until the changes
are committed and exercised there.

As of this review, the public repository still serves the older published tree;
the hardening and Pages source in this worktree are not public until an
intentional commit/push and Pages deployment are performed.

## Evidence snapshot

| Surface | Integrated evidence | Honest status |
|---|---|---|
| Local engine | 262-test public suite on Python 3.14; 262 on Python 3.11 with optional skips | Implemented |
| OKF Bundle | Export/rebuild, relation, CRLF, encryption, and Obsidian-property tests | Implemented; arbitrary YAML semantics are not interpreted |
| Git sync | Local bare-remote drill, interruption journal, staged rebuild, stale-edit refusal | Implemented locally; hosted remote CI and operator access policy remain separate |
| MCP | Isolated subprocess initialize/list/add/search | Protocol-tested; host registration still manual |
| Agent Skill | Local and official validators pass; five host names recognized by installer; isolated MCP registration smokes pass for Gemini CLI 0.26.0, Codex 0.87.0, OpenCode 1.15.10, and Cline 3.0.51; content-free doctor and host matrix reports available | Package/MCP-ready; fresh-session host handshakes pending |
| Claude hooks | Installer and hook tests | Claude-specific automation |
| Obsidian | Recursive import, paths, unknown top-level properties, common wikilinks, and opt-in attachment mirror tested | Level 2-format progress; no native plugin/live sync |
| Object storage | Deterministic local contract plus rclone adapter | Repo-tested; no live provider certification |
| Postgres/Supabase | Lazy adapter/configuration/error tests | Repo-tested; no live database integration |
| Managed SaaS | Buyer, boundary, and 90-day gates documented | Strategy only |

## Scorecard

The score is deliberately conservative. It measures product proof, not code
volume or provider-logo coverage.

| Dimension | Current | World-class gate |
|---|---:|---|
| Core architecture | 8/10 | Stable migrations, scale/property tests, recovery compatibility policy |
| Data ownership | 8/10 | Key recovery/rotation and encrypted live restore drill |
| Reliability evidence | 7/10 | Remote CI green, signed releases, checksums/SBOM |
| Cross-agent portability | 5/10 | Fresh-install add/search handshake on five named hosts |
| Obsidian interoperability | 5/10 | Golden-vault property/attachment round-trip or maintained plugin |
| Storage ecosystem | 5/10 | Emulator and live encrypted drills across provider families |
| Security posture | 6/10 | Key lifecycle, historical-plaintext erasure tooling, adversarial review |
| Onboarding | 6/10 | Observed first useful recall in under five minutes |
| Adoption | 2/10 | External weekly users, retention, and contributions |
| Commercial proof | 1/10 | Paid pilots and renewal evidence |

**Overall assessment: about 5.8/10 as a product and 8/10 as an engineering
foundation.** That is a material improvement, not a world-class finish line.

## Compatibility levels

Do not publish one binary “compatible” badge. Use levels that can be reproduced.

### Agent hosts

1. **Package:** the host discovers and loads `SKILL.md`.
2. **Handshake:** the host saves a unique Concept and recalls it in a fresh session.
3. **Automation:** host-native capture/recall hooks are installed and observed.
4. **Supported:** documented host versions run the handshake continuously.

### Obsidian

1. **Readable:** generated Markdown, frontmatter, and common links work.
2. **Vault round-trip:** nested notes, aliases, properties, Unicode, and attachments
   have an explicit preservation policy and golden fixtures.
3. **Bidirectional:** dry-run diff, conflict preview, and attachment sync exist.
4. **Native:** a maintained plugin exposes status and controls.

### Storage

1. **Contract:** the adapter passes deterministic snapshot/restore tests.
2. **Emulator:** a provider-compatible local service passes wipe/restore/rebuild.
3. **Live:** a real provider account passes an encrypted restore drill.
4. **Supported:** scheduled qualification covers documented provider versions.

## Highest-leverage remaining work

1. **Prove the wedge.** Save one unique decision in agent A, recall it in a fresh
   agent B session, and publish a content-free compatibility report.
2. **Prove remote recovery.** Generate an encrypted Bundle, upload to real
   S3-compatible and GCS accounts, wipe locally, restore, rebuild, and compare
   hashes.
3. **Reach Obsidian level 2 deliberately.** Use a consented golden vault covering
   arbitrary properties, aliases, nested paths, Unicode, and attachments.
4. **Ship supply-chain evidence.** Versioned release artifacts, checksums, signing,
   SBOM, migration notes, and a compatibility report.
5. **Earn adoption.** Ten observed external installs, week-four retention, and two
   outside contributions are more valuable now than another storage logo.
6. **Sell three pilots.** Validate the consultancy buyer and repeated job before a
   hosted control plane becomes the product.

## Next public-release gates

- [x] Public release gate runs without ignored/private state.
- [x] Agent Skill validators pass.
- [x] MCP initialize/list/add/search is checked in.
- [x] Three-OS CI workflow is present and statically validated.
- [x] Snapshot push/pull/restore and corruption/traversal rejection are checked in.
- [x] Remote adapter APIs fail closed on plaintext private Concepts unless the
  caller uses an explicit dangerous override.
- [x] Obsidian support is labelled by level and common semantics are tested.
- [x] README, security policy, threat model, compatibility matrix, and Pages source
  are present.
- [ ] GitHub-hosted CI is green on the published commit.
- [ ] GitHub Pages is enabled and visually verified at its public URL.
- [ ] A tagged release includes downloadable artifacts and checksums.
- [ ] Five real host-version handshakes are recorded.
- [ ] At least one real encrypted provider wipe/restore drill passes.
