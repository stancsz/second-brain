# Compatibility and evidence

This project has two portable integration surfaces and one host-specific surface:

1. `SKILL.md` is an Agent Skills package. It tells a compatible agent when and
   how to use the local CLI.
2. `scripts/brain_mcp.py` is a stdio MCP server. It exposes the same local brain
   to a host that can launch MCP subprocesses.
3. `install.sh`, `settings.example.json`, `hooks/`, and `commands/` integrate
   Claude Code session hooks. They are not a cross-agent automation layer.

For copy-pasteable host paths and MCP configuration examples, see
[HOST_SETUP.md](./HOST_SETUP.md).

## Evidence terms

- **Repo-tested:** a checked-in automated test executes the behavior.
- **Package-validated:** repository structure and metadata pass the local
  standards gate; this does not prove activation inside a host application.
- **Documented target:** the portable surface should be usable by a compatible
  host, but this repository does not yet run a host-level end-to-end test.
- **Not portable:** the behavior depends on a host-specific hook or command API.

## Agent hosts

| Host | Native Agent Skill | MCP | Automatic capture and recall hooks |
|---|---|---|---|
| Claude Code | Package-validated; native install is documented. Live skill activation remains manual. | Repo-tested server; isolated `claude mcp add/list` health smoke on Claude Code 2.1.146, not CI. | Claude-specific installer and hooks have unit tests. A live installed-session test remains manual. |
| Codex | Package-validated, including quoted `agents/openai.yaml` UI metadata and a `$second-brain` default prompt. Codex CLI `0.87.0` accepted an isolated MCP registration smoke. Fresh-session skill activation remains manual. | Repo-tested server; isolated `codex mcp add/get/list` registration smoke, not CI. | Not portable; no Codex lifecycle integration is shipped. |
| Gemini CLI | Documented target through the shared Agent Skills package; Gemini CLI `0.26.0` accepted an isolated MCP registration smoke. Fresh-session skill activation remains manual. | Repo-tested server; isolated `gemini mcp add/list` reported the server connected, not CI. | Not portable; no Gemini lifecycle integration is shipped. |
| OpenCode | Documented target through the shared Agent Skills package. OpenCode `1.15.10` accepted an isolated local skill/MCP config smoke; fresh-session skill activation remains manual. | Repo-tested server; isolated `opencode mcp list --pure` reported the server connected, not CI. | Not portable; no OpenCode lifecycle integration is shipped. |
| Cline | Documented target through the shared Agent Skills package; project/global skill paths are documented. Cline `3.0.51` parsed an isolated MCP registration; fresh-session skill activation remains manual. | Repo-tested server; isolated `cline config mcp --json` registration smoke, not CI. | Not portable; no Cline lifecycle integration is shipped. |

The MCP subprocess test covers `initialize`, `notifications/initialized`,
`tools/list`, `brain_add`, and `brain_search` against a temporary home directory.
It proves the checked-in server's core JSON-RPC path without touching the user's
real database. It is not a complete MCP conformance suite and does not prove
registration UX in every host.

### Installer smoke

On 2026-08-12, the documented `npx skills add` command was run against this
working tree on Windows with all five requested agent names. The command exited
successfully and copied the skill into `.agents/skills/second-brain` and
`.claude/skills/second-brain`. The installer accepted the Gemini CLI, OpenCode,
and Cline names. Isolated registration-parser/health smokes were also run for
Claude Code `2.1.146`, Gemini CLI `0.26.0`, Codex `0.87.0`, OpenCode `1.15.10`,
and Cline `3.0.51`; these do not prove native skill discovery or a model-backed
fresh-session handshake.

The copied `.agents` package was then executed from its installed path in an
isolated home: `brain_cli.py --json add` created a Concept and
`brain_cli.py --json search` retrieved it. This verifies post-copy execution of
the portable package, not native host registration or a fresh-session agent
handshake.

`python scripts/brain_doctor.py --json` provides a content-free local report for
package, MCP, storage, journal, and paired-store state. It uses a read-only
SQLite connection when both sides exist; it never repairs a marker or prints
Concept content. A passing doctor report is local evidence, not live host or
provider certification.

Run `python scripts/host_matrix.py --json` for the checked-in five-host package
and MCP matrix. It reports `package-ready`, not native host activation; each
host row still requires a fresh-session handshake on a named host version.

## Obsidian

Current support is **export compatibility**, not a native Obsidian plugin or
two-way live vault sync. The checked-in tests exercise Markdown export, recursive
`.md`/`.markdown` vault import, one file per Concept, YAML frontmatter, rebuild,
typed-relation round trips, and Obsidian alias/heading/block wikilink semantics
without rewriting note content. Nested relative note paths are preserved through
the namespaced `sb_obsidian_path` extension. The resulting files are intended to be readable
in Obsidian, but CI does not launch Obsidian itself. Treat this as compatibility
level 2-format progress: readable, portable Markdown with tested nested-path
and unknown-top-level-property preservation. A golden-vault run covering
attachments and a maintained plugin remain future gates. An opt-in
`--attachments-from` export mirror copies regular non-Markdown files but is not
a persisted or bidirectional attachment-sync protocol.

## Storage backends

The canonical store remains a local Markdown Bundle with a rebuildable SQLite
index; git remains the bidirectional synchronization path. Remote storage is an
immutable **backup snapshot** surface, not shared-database authority or a merge
protocol.

| Storage surface | Implementation and evidence |
|---|---|
| Local filesystem | Repo-tested deterministic, content-addressed snapshots; canonical manifest/file/archive SHA-256; corrupt and unsafe archives rejected; verified pull; staged restore; non-empty refusal; recoverable `--force` backup. Paired receipts are snapshotted; interrupted canonical/Git writes are refused until recovery. |
| S3, GCS, Azure Blob, Cloudflare R2, Backblaze B2, MinIO, Wasabi, Google Drive, OneDrive, WebDAV, SFTP, and other rclone stores | Shipped through the generic lazy `RcloneBackend`, which uses preconfigured rclone credentials and immutable copy operations. Deterministic fake-rclone contract tests cover list/pull, missing archives, and manifest identity checks; no live provider account is exercised in CI. Native provider-SDK adapters are not shipped. |
| PostgreSQL | A lazy `PostgresBackend` stores each manifest and tar atomically as `BYTEA` and verifies rows during list/pull. Optional dependency, configuration, and identifier-safety paths are repo-tested; no live Postgres integration runs in CI. |
| Supabase | Shipped through the PostgreSQL snapshot backend with a named DSN environment variable. Selection/configuration behavior is repo-tested; no live Supabase project runs in CI. |

All remote adapters preserve the Bundle as the portable source of truth. They
refuse recognized plaintext private Concepts before remote I/O unless the caller
selects the explicit dangerous override. This is frontmatter-based defense in
depth, not a replacement for encrypted Bundle export. The adapters do not yet
prove provider-side retention, concurrent edit merging, key recovery, or hosted
multi-tenant controls. See `references/storage.md` for the exact trust boundary
and reproducible CLI surface. Community adapters should implement the documented
snapshot/list/pull/privacy/restore contract before claiming compatibility.

Git sync keeps the pair receipt local to each checkout and records an explicit
Bundle-authority journal before pull/rebase. A failed rebuild is therefore
recoverable by reopening or rerunning sync; stale SQLite is never exported over
Markdown that arrived from a pull.

## Reproduce the checked-in evidence

```bash
python scripts/validate_skill.py .
python -m unittest discover -s tests -p "test_*.py" -v
python -c "import pathlib, py_compile; [py_compile.compile(str(path), doraise=True) for root in ('scripts', 'hooks', 'tests') for path in pathlib.Path(root).rglob('*.py')]"
```

CI runs these gates on Ubuntu, Windows, and macOS with Python 3.10 and 3.14.
