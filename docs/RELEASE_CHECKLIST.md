# Public release checklist

Use this checklist before calling a release production-ready. Keep local,
GitHub, host, and provider evidence separate; a green local test run does not
substitute for the other gates.

## 1. Local source gate

- [ ] `python scripts/validate_skill.py .`
- [ ] `python scripts/run_corpus.py`
- [ ] `python scripts/ship_gate.py`
- [ ] `uvx --from skills-ref agentskills validate .`
- [ ] `git diff --check`
- [ ] No secrets, real notes, provider credentials, or user-owned config files
      are staged.
- [ ] `opencode.jsonc` is intentionally handled; it is user-owned in this
      working tree and must not be staged without explicit approval.

## 2. Package and host evidence

For each host, record the exact version, operating system, commit/tag, and a
synthetic token. Never use a real memory or transcript.

- [ ] Claude Code: skill discovery and fresh-session save/search.
- [ ] Codex: skill discovery and fresh-session save/search.
- [ ] Gemini CLI: skill discovery and fresh-session save/search.
- [ ] OpenCode: skill discovery and fresh-session save/search.
- [ ] Cline: skill discovery and fresh-session save/search.
- [ ] MCP `initialize`, `tools/list`, `brain_add`, and `brain_search` pass where
      the host supports MCP.
- [ ] `python scripts/brain_doctor.py --json` output is attached without note
      content.

Registration-parser or server-health output is useful evidence, but it is not a
model-backed fresh-session handshake.

## 3. Obsidian evidence

- [ ] Import a consented synthetic vault with nested Markdown, aliases,
      heading/block fragments, Unicode, properties, and attachments.
- [ ] Export and rebuild; compare the documented preservation policy.
- [ ] Record unsupported YAML semantics, attachment behavior, and conflict
      limitations.
- [ ] Do not call this native plugin or live two-way sync unless an actual
      maintained Obsidian integration has been exercised.

## 4. Storage evidence

For each provider family, use a synthetic encrypted Bundle and record the
provider, client/runtime version, region or endpoint class, date, and hashes.

- [ ] Local snapshot push/list/pull/rebuild.
- [ ] S3-compatible object store (AWS S3, R2, MinIO, B2, or Wasabi).
- [ ] Google Cloud Storage.
- [ ] PostgreSQL.
- [ ] Supabase Postgres or Storage.
- [ ] Simulate projection loss by moving the SQLite index to a recoverable
      sibling; restore the Bundle with the safe restore helper (`--force` when
      its destination exists), then rebuild into a new index. The restore
      primitive validates before swapping and preserves the old target (see
      [THREAT_MODEL.md](./THREAT_MODEL.md)).
- [ ] Compare the restored Bundle and rebuilt logical projection hashes.
- [ ] Verify plaintext-private refusal and key recovery/rotation behavior.

The generic rclone adapter is broad compatibility, not provider certification.
Do not publish provider logos as “supported” until the corresponding live drill
is recorded.

## 5. GitHub publication

- [ ] Commit only the intended source, docs, tests, workflows, and assets.
- [ ] Push the intended branch/tag and verify the exact remote commit.
- [ ] Confirm GitHub Actions is green on the published commit.
- [ ] Confirm Pages is enabled and inspect the rendered public URL.
- [ ] Confirm the tagged release contains the source archive and SHA-256 sums.
- [ ] Link the compatibility report and known limitations from the release notes.

## 6. Adoption and SaaS proof

- [ ] Observe five fresh external installs.
- [ ] Publish one content-free continuity/restore case study.
- [ ] Recruit three paid setup pilots before building a broad hosted control
      plane.
- [ ] Keep the MIT core, file format, local engine, CLI, MCP, Obsidian exchange,
      encryption, and storage connectors usable without the hosted service.
- [ ] Charge for BYOC operations: fleet health, scheduled backups, restore
      drills, RBAC/audit, SSO/SCIM, SLA, support, and managed upgrades.

See [PROJECT_REVIEW.md](./PROJECT_REVIEW.md) for the current scorecard and
[OPEN_SOURCE_SAAS.md](./OPEN_SOURCE_SAAS.md) for the commercial boundary.
