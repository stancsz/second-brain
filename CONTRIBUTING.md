# Contributing to second-brain

Thank you for helping make durable agent memory portable. Contributions are
welcome across the Python engine, Agent Skill, MCP surface, Obsidian format,
storage adapters, tests, and documentation.

The project has one non-negotiable boundary: the user's OKF Markdown Bundle
remains portable and authoritative. SQLite is rebuildable, remote stores are
backup mirrors, and agent hosts are clients.

## Before opening an issue or pull request

- Search existing issues and pull requests for the same behavior.
- Report vulnerabilities through the private process in [SECURITY.md](SECURITY.md).
- Reproduce with a temporary brain and synthetic notes. Never paste a real
  note, transcript, database, encryption key, DSN, provider credential, or
  rclone configuration into an issue, test fixture, screenshot, or log.
- Describe the user-visible behavior and the evidence that would prove it.

Small fixes can go directly to a pull request. For schema changes, snapshot
format changes, new host automation, or a change to the open-core boundary,
open an issue or draft pull request first so the contract can be reviewed
before implementation.

## Development setup

The core supports Python 3.10 or newer and has no required third-party runtime
dependency.

```bash
git clone https://github.com/stancsz/second-brain.git
cd second-brain
python scripts/validate_skill.py .
python -m unittest discover -s tests -p "test_*.py" -v
```

Optional adapters should keep their dependencies optional and import them only
when selected. Use temporary directories and an isolated database for manual
checks; do not run contribution tests against `~/.secondbrain`.

## Public release gate

Run the same public checks used by the repository before requesting review:

```bash
python scripts/validate_skill.py .
python scripts/run_corpus.py
python scripts/ship_gate.py
```

`validate_skill.py` checks the Agent Skills package, local references, Python
syntax, and Codex metadata. `run_corpus.py` compiles Python sources and runs the
test suite. `ship_gate.py` repeats those checks and scans the current diff and
untracked text files for common secret shapes. CI runs the underlying package,
compile, and test checks on Ubuntu, Windows, and macOS.

Include the command results in the pull request. If an optional dependency or
live service was unavailable, report the exact skip or limitation; do not turn
an unrun check into a success claim.

## Evidence language

Use these levels consistently in issues, pull requests, and docs:

- **Proposed:** design or documentation only; no implementation claim.
- **Package-validated:** structure and metadata pass the package gate; this
  does not prove activation inside a host.
- **Repo-tested:** a checked-in automated test executes the behavior using
  synthetic data.
- **Live-verified:** the behavior was exercised in a named host or provider.
  Include its exact version, operating system, date, and sanitized result.

A configuration example is not live verification. A mocked provider is
repo-tested, not provider-verified. Keep claims no broader than their evidence.

## Change expectations

- Keep changes focused and preserve existing file-format compatibility unless
  the pull request explicitly proposes a migration.
- Add regression tests for behavior changes and failure-path tests for trust
  boundaries.
- Keep the stdlib-only local path working. Fail optional integrations lazily
  with an actionable error.
- Update user documentation and `docs/COMPATIBILITY.md` when support or its
  evidence level changes.
- Avoid unrelated formatting or refactors.
- Do not add telemetry, network calls, destructive cleanup, or credential
  collection without an explicit, reviewed contract.

Contributions are licensed under the repository's [MIT License](LICENSE).

## Storage-adapter conformance checklist

New storage adapters extend the immutable snapshot mirror. They do not become a
second source of truth or a concurrent-edit protocol. In the issue and pull
request, mark every item complete or explain why it is not applicable.

- [ ] Implements the `Backend` contract: `name`, `push(snapshot)`,
      `pull(snapshot_id=None)`, and `list()`; it adds no delete operation.
- [ ] Preserves canonical manifest and archive bytes without rewriting the
      Bundle or snapshot ID.
- [ ] Treats an identical push as idempotent and refuses a same-ID/different-
      bytes conflict.
- [ ] Verifies the complete snapshot after pull and before returning it.
- [ ] Lists only complete snapshots with valid 64-character SHA-256 IDs and
      has deterministic newest-snapshot behavior.
- [ ] Resolves optional libraries, executables, and configuration only when
      the adapter is selected; local snapshots still work without them.
- [ ] Accepts secrets only through the provider's normal configuration or a
      named environment variable. Secrets never appear in arguments, logs,
      exceptions, manifests, fixtures, or docs.
- [ ] Uses argument arrays rather than a shell for subprocesses, validates
      remote identifiers, and applies least-privilege provider operations.
- [ ] Has synthetic tests for push/pull/list, idempotency, missing snapshots,
      incomplete or corrupt data, and missing dependency/configuration paths.
- [ ] Documents credentials, permissions, retention, encryption, consistency,
      cost, and restore limitations without implying live verification.
- [ ] If live-verified, records provider/runtime versions, region or endpoint
      class, date, sanitized commands, and a synthetic restore hash. No real
      note content or credentials are included.

See [the storage contract](references/storage.md) for the current snapshot and
restore guarantees.

## Agent-host compatibility handshake

Use this template when adding or upgrading Claude Code, Codex, Gemini CLI,
OpenCode, Cline, or another host. Run it with an isolated home/data directory
and synthetic content.

```text
Host and exact version:
Operating system:
Date (UTC):
Install method and scope (project/user):
Package commit or release:

Skill handshake
- Discovery command or UI:
- Skill listed as `second-brain`: pass/fail/not available
- Synthetic trigger prompt:
- Correct skill selected: pass/fail/not observable
- CLI save and recall with Concept ID: pass/fail/not tested

MCP handshake (when supported)
- Server launched over stdio: pass/fail/not supported
- `initialize`: pass/fail/not tested
- `tools/list` includes brain tools: pass/fail/not tested
- `brain_add` synthetic Concept: pass/fail/not tested
- `brain_search` returns that Concept ID: pass/fail/not tested

Host-specific automation
- Hooks/lifecycle API tested:
- Consent or permission prompts observed:

Sanitized evidence attached:
Cleanup completed:
Known limitations:
```

Do not include the host's full configuration if it contains tokens, paths that
identify a person, private prompts, transcript contents, or an existing brain.

## Review and governance

Pull requests are reviewed for correctness, evidence, privacy, portability, and
scope. A green gate is necessary but does not replace review. Project roles and
decision-making are described in [GOVERNANCE.md](GOVERNANCE.md).
