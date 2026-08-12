# Security policy

`second-brain` stores personal knowledge, project decisions, and optionally
psychological data. Treat a populated brain as sensitive as private source code or a
password-manager export.

## Supported versions

Security fixes target the latest tagged release and `main`. Older releases may receive
a patch when the migration risk warrants it, but this is not yet a formal long-term
support commitment.

## Report a vulnerability

Use GitHub's **Security → Report a vulnerability** flow for this repository. Do not put
keys, private notes, proof-of-concept plaintext, or exploitable details in a public
issue. If private reporting is unavailable, open a public issue containing only a
request for a private contact channel.

Include, when safe:

- affected version or commit
- operating system and Python version
- attack preconditions and expected impact
- minimal reproduction using synthetic data
- whether a key, remote, hook, or MCP client is involved
- suggested mitigation, if known

Maintainers should acknowledge a private report within seven days, provide a status
update within fourteen days, and coordinate disclosure after a fix or mitigation is
available. These are project targets, not a paid SLA.

## Security posture

- The local Python core makes no network calls by itself.
- The OKF Markdown Bundle is canonical; SQLite is a rebuildable local index.
- Git sync and optional storage backends cross the local trust boundary.
- Claude Code hooks can read conversation transcripts and write local logs.
- The stdio MCP server grants its parent client the brain operations it exposes.
- Optional encryption currently uses a locally stored Fernet key.

Read [the threat model](./docs/THREAT_MODEL.md) before configuring a remote or a
multi-user host.

## Safe operating rules

1. Never commit `secret.key`, `*.key`, `.env*`, or `brain.db*`.
2. Keep the encryption key outside the Bundle and back it up separately.
3. Use a private remote with least-privilege credentials.
4. Enable strict encryption before syncing private/psychological Concepts.
5. Inspect hook configuration and transcript retention before installing automation.
6. Run MCP under a user account with access only to the intended brain.
7. Test restore with synthetic data before trusting a backup path.
8. Do not put third-party psychological data into a shared brain without consent and a
   retention/correction process.

## Not a certification

Local-first design and offline operation can reduce exposure. They do not make this
project HIPAA, SOC 2, GDPR, or other regulatory compliance out of the box. Compliance
depends on deployment, access controls, policies, contracts, and qualified review.
