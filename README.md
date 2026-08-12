# second-brain

**One memory for Claude, Codex, Gemini, OpenCode, and Cline — stored as files you own.**

[![CI](https://github.com/stancsz/second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/stancsz/second-brain/actions/workflows/ci.yml)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-validated-1f6feb)](https://agentskills.io/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-151713)](LICENSE)

`second-brain` is a local-first knowledge graph for AI agents. Its canonical
store is an OKF-flavoured Markdown Bundle; SQLite is a disposable search index.
The same memory is available through an Agent Skill, a command-line interface,
and a stdio MCP server.

> **Beta, with evidence.** The package, local engine, MCP subprocess, Obsidian
> format behaviour, snapshot/restore path, and 262-test suite are checked in.
> Live activation in every agent host and live cloud-provider accounts are not
> yet part of CI. See the [compatibility matrix](docs/COMPATIBILITY.md).

## Why this exists

Ask one agent to remember an architectural decision, switch tools, and the next
agent usually starts cold. Hosted memory products solve that by putting another
vendor between you and your own history.

`second-brain` takes the opposite approach:

- **Files are truth.** Notes remain inspectable Markdown with stable IDs and
  wikilinks.
- **Agents are clients.** Claude, Codex, Gemini, OpenCode, and Cline share the
  same open skill package; MCP-capable clients can call the same brain over
  JSON-RPC. Host activation evidence is tracked explicitly below.
- **Indexes are replaceable.** Delete SQLite, rebuild it from the Bundle, and
  continue.
- **Writes are paired.** Supported CLI/MCP mutations flush Markdown before they
  report success; a lock, receipt, and crash journal refuse stale or mixed
  generations instead of guessing.
- **Storage stays yours.** Git handles bidirectional sync. Immutable snapshots
  can go to local disk, rclone providers, PostgreSQL, or Supabase.
- **No account is required.** The Python core uses the standard library.

## Install the skill

Install one package for all five target hosts with the open Agent Skills
installer:

```bash
npx skills add stancsz/second-brain \
  --skill second-brain --global --copy -y \
  --agent claude-code codex gemini-cli opencode cline
```

The installer accepts all five host names and the package validates locally and
with the official Agent Skills validator. That proves installation/package
compatibility—not native activation inside each host. Host application
activation remains a manual smoke test until the project has a maintained
host-version matrix.

In a Windows smoke using this exact command, the installer materialized copies
under `.agents/skills/second-brain` and `.claude/skills/second-brain`. That is
useful package-install evidence; it does not prove that Gemini CLI, OpenCode,
or Cline will discover the skill in their current native configuration.

The copied `.agents` skill was then run from its installed path in an isolated
home: `add --json` created a Concept and `search --json` retrieved it. This
proves the package remains executable after copying; it is still not a native
host handshake.

Prefer a plain clone, or only want the CLI?

```bash
git clone https://github.com/stancsz/second-brain.git
cd second-brain
python scripts/brain_cli.py add "Atlas storage decision" \
  "Markdown is canonical; SQLite is rebuilt from it." \
  --collection Decisions --tags atlas,architecture
python scripts/brain_cli.py search "Why SQLite?"
```

Data is created under `~/.secondbrain/`. Use `--db PATH` to isolate a different
brain.

## What works where

| Surface | Claude Code | Codex | Gemini CLI | OpenCode | Cline |
|---|---:|---:|---:|---:|---:|
| Agent Skill package | package-validated | package-validated | documented target + MCP registration smoke | documented target + MCP registration smoke | documented target + MCP registration smoke |
| Local stdio MCP server | registration/health smoke on Claude Code 2.1.146 | registration smoke on Codex 0.87.0 | registration smoke on Gemini CLI 0.26.0 | registration smoke on OpenCode 1.15.10 | registration smoke on Cline 3.0.51 |
| Automatic capture/recall hooks | tested | — | — | — | — |

“Subprocess protocol-tested” means the repository launches the MCP subprocess
and exercises `initialize`, `tools/list`, `brain_add`, and `brain_search` in an
isolated home. The named registration smokes additionally exercise a host CLI
configuration parser; neither level proves a model-backed fresh-session
handshake. The [evidence matrix](docs/COMPATIBILITY.md) separates repo tests,
package validation, parser smokes, and live-host gaps.

For host-specific skill paths, MCP configuration, and the fresh-session test,
see [HOST_SETUP.md](docs/HOST_SETUP.md).
Run `python scripts/host_matrix.py --json` for a content-free package/MCP
readiness report covering all five named hosts. It marks native host launch as
a separate manual gate; it does not pretend that a repository test operated a
proprietary host UI.

Claude Code users can optionally install the included `Stop`, `PreCompact`, and
`UserPromptSubmit` hooks:

```bash
bash install.sh
```

The installer merges settings instead of replacing them. Review any lifecycle
hook before enabling it; conversation capture is sensitive data.

## Core workflow

```text
Claude / Codex / Gemini / OpenCode / Cline
                 │
        Agent Skill · MCP · CLI
                 │
        OKF Markdown Bundle       ← canonical
          ├── SQLite FTS index    ← rebuildable
          ├── git history         ← bidirectional sync
          └── snapshots           ← one-way restore mirrors
```

Useful commands:

```bash
# Capture and recall
python scripts/brain_cli.py add "Decision" "Use customer-owned storage" --tags decision
python scripts/brain_cli.py search "customer storage"
python scripts/brain_cli.py show <id-or-title>

# Organize and connect
python scripts/brain_cli.py list --collection Decisions --sort updated
python scripts/brain_cli.py relate <from-id> <to-id> --type references
python scripts/brain_cli.py traverse <id> --depth 2

# Recoverable lifecycle
python scripts/brain_cli.py delete <id>
python scripts/brain_cli.py restore <id>
python scripts/brain_cli.py summary
```

Run `python scripts/brain_cli.py --help` for the complete command set, including
point-in-time and affect-aware recall, distillation, archival, and brain merge.

For a content-free install and pairing report, run the read-only doctor:

```bash
python scripts/brain_doctor.py --json
```

It checks the package, MCP protocol, storage surface, journals, and paired
database/Bundle digests without opening a writable database or printing note
contents. Add `--strict` when an uninitialized brain should fail the check.

## MCP

Run the dependency-free stdio server:

```bash
python /absolute/path/to/second-brain/scripts/brain_mcp.py
```

Register that command using your host's MCP configuration shape. The common
payload is:

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["/absolute/path/to/second-brain/scripts/brain_mcp.py"]
    }
  }
}
```

The server and CLI operate on the same local database. Diagnostics go to
`stderr`; JSON-RPC alone is written to `stdout`.

## Obsidian compatibility

Export one Markdown file per Concept:

```bash
python scripts/brain_cli.py export --format markdown --output ./MyVault
```

Import a vault recursively (`.md` and `.markdown`):

```bash
python scripts/brain_cli.py import ./MyVault --merge
```

Repository tests cover YAML frontmatter, CRLF input, recursive folders,
`[[alias|label]]`, heading/block fragments, wikilink/manual-relation coexistence,
and OKF manual-relation rebuild. Nested relative note paths (including
`.markdown`) are preserved through the namespaced `sb_obsidian_path` extension.
This is **level-2-format progress**, not a native Obsidian plugin or live
two-way sync. Unknown top-level YAML blocks are preserved through the
namespaced `sb_obsidian_frontmatter` extension, but the importer does not
interpret every YAML type and path-qualified links are not resolved by
basename. Keep that limitation in mind before pointing it at a heavily
customized vault.

Attachments are deliberately opt-in and remain outside the canonical memory
model. To mirror non-Markdown files from an existing vault during export:

```bash
python scripts/brain_cli.py export --format markdown --output ./MyVault \
  --attachments-from ./OriginalVault
```

The mirror rejects symlinks and conflicting destination files; it is not a
cross-device attachment sync protocol.

## Git sync

The OKF Bundle is the bidirectional synchronization spine:

```bash
python scripts/sync.py ~/.secondbrain/okf <git-remote> ~/.secondbrain/brain.db
```

Sync exports files, commits, pulls with rebase, parks conflicting Markdown as
`*.conflict.md`, pushes, then rebuilds SQLite. The generated Bundle `.gitignore`
blocks key, database, environment-secret, and local pair-state patterns from
staging. If a pull or rebuild is interrupted, the sync journal makes the Bundle
authoritative on retry; it never exports the stale pre-pull database over newer
Markdown.

## Backups: local, S3/GCS/Azure/R2/B2, Postgres, Supabase

Backups are immutable, content-addressed snapshots. They are deliberately
one-way mirrors, not a concurrent-edit protocol.

Local reference backend:

```bash
python scripts/storage_cli.py push --backend local \
  --store ./backups --bundle ~/.secondbrain/okf
python scripts/storage_cli.py pull --backend local \
  --store ./backups --dest ./restored-okf
python scripts/bundle.py rebuild ./restored-okf ./restored-brain.db
```

For a restored brain that should become a normal paired working store, open it
through the coordinator once (this writes the local pair receipt):

```bash
python scripts/brain_cli.py --db ./restored-brain.db \
  --bundle ./restored-okf stats
```

The low-level `bundle.py rebuild` command remains useful for disposable
projections, but it intentionally does not claim ownership of a user's paired
working store.

Any configured [rclone](https://rclone.org/) remote uses the same verified
snapshot format. This covers S3, GCS, Azure Blob, Cloudflare R2, Backblaze B2,
MinIO, Wasabi, and many other providers without putting credentials on this
CLI's command line:

```bash
python scripts/storage_cli.py push --backend rclone \
  --remote s3:my-bucket/second-brain --bundle ~/.secondbrain/okf
```

PostgreSQL and Supabase use an optional lazy adapter:

```bash
pip install "psycopg[binary]"
export SECONDBRAIN_POSTGRES_DSN='postgresql://...'
python scripts/storage_cli.py push --backend postgres \
  --bundle ~/.secondbrain/okf
```

Supabase is PostgreSQL here: pass its database connection string through a named
environment variable with `--dsn-env SUPABASE_DB_URL`. No live cloud account is
exercised in CI. Exact guarantees and restore behaviour are in
[references/storage.md](references/storage.md).

For the complete publication and qualification gates, see the
[public release checklist](docs/RELEASE_CHECKLIST.md).

## Security before remote sync

The local database and ordinary Markdown exports are plaintext. Optional Fernet
encryption protects Concepts tagged `private` or `psych`, plus `Episode` and
`RelationshipModel` types, when a key is configured:

```bash
pip install cryptography
python scripts/crypto.py init
export SECONDBRAIN_REQUIRE_ENCRYPTION=1
```

Set `SECONDBRAIN_REQUIRE_ENCRYPTION=1` **before any remote export or snapshot**.
Without strict mode and without a configured key, the legacy export path warns
but can still write sensitive Concepts as plaintext. Remote snapshots preserve
Bundle bytes; they do not add encryption themselves. As defense in depth, the
rclone and PostgreSQL/Supabase backends inspect the verified snapshot and refuse
recognized plaintext private Concepts before any remote I/O. A deliberately
dangerous `--allow-plaintext-private` override exists for exceptional migrations.

Read [SECURITY.md](SECURITY.md) and the [threat model](docs/THREAT_MODEL.md) before
using psychological or third-party personal data. Never sync `secret.key`.

## Evidence and development

Reproduce the public release gate:

```bash
python scripts/validate_skill.py .
python scripts/run_corpus.py
python scripts/ship_gate.py
```

The integrated suite contains 262 tests. It covers the engine, CLI,
OKF export/rebuild, sync, encryption paths, MCP subprocess, skill packaging,
Obsidian-format behaviour, and storage snapshots. CI runs on Ubuntu, Windows,
and macOS with Python 3.10 and 3.14. Optional-crypto and platform-specific tests
skip when their prerequisite is unavailable.

Project status and remaining gates:

- [Compatibility and evidence](docs/COMPATIBILITY.md)
- [Independent project review](docs/PROJECT_REVIEW.md)
- [Security policy](SECURITY.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Storage contract](references/storage.md)

## Open-source SaaS direction

The open core should remain completely useful offline: format, CLI, SQLite
projection, MCP, Obsidian path, cryptography, git sync, backup contract, and
provider adapters. A paid product can operate the difficult layer around it:

- device and workspace fleet health;
- scheduled encrypted snapshots and restore drills;
- BYOC control plane, RBAC, audit, SSO/SCIM, alerts, and support;
- team onboarding and migration.

The recommended first offer is a paid **Agent Memory Portability Setup** for a
small AI consultancy, before building a broad hosted platform. The full buyer,
pricing hypotheses, technical boundary, and 90-day gates are in
[docs/OPEN_SOURCE_SAAS.md](docs/OPEN_SOURCE_SAAS.md).

## Contributing

Start with an issue that names the user-visible behaviour and evidence required.
New storage adapters should conform to the snapshot contract rather than making
their service authoritative. New agent integrations should add a real
host-version handshake, not only a configuration snippet.

Run the release gate before opening a pull request. Security issues should follow
[SECURITY.md](SECURITY.md), not a public issue.

MIT licensed. Your knowledge is your intellectual history; keep the files.
