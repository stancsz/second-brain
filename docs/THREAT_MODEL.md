# Threat model

**Status:** living design document
**Scope:** local CLI, OKF Bundle, SQLite index, git sync, hooks, stdio MCP, and optional
snapshot/projection adapters.

## Assets

| Asset | Why it matters |
|---|---|
| OKF Bundle | Canonical knowledge, provenance, relationships, psychological fields |
| SQLite index | Searchable local projection; may contain plaintext copies |
| Conversation logs | Raw prompts, outputs, tool results, and potentially secrets |
| Encryption key | Decrypts every Concept protected by that key |
| Git history | May retain deleted or previously plaintext material indefinitely |
| Remote credentials | Can read, overwrite, or delete backups/sync state |
| MCP process | Can read/write the brain on behalf of a client |
| Derived projections | Postgres/vector/search copies of canonical data |

## Trust boundaries

```text
user + local agent host
        │
        ├── hooks ──► raw local transcript logs
        │
        ├── CLI / stdio MCP ──► SQLite index
        │                         │
        │                         ▼
        └────────────────────► OKF Bundle (canonical)
                                  │
                   network boundary
                                  │
                 git remote / snapshot mirror / projection
```

The local filesystem is not automatically trusted: other processes under the same user,
backup software, indexing services, and malware may read it. A remote adapter is never a
mere implementation detail; it changes who can access encrypted metadata, ciphertext,
history, and operational logs.

## Adversaries and failures

- A malicious or compromised local process reading the brain, logs, or key.
- A compromised agent/MCP client issuing unintended reads, writes, or deletes.
- A malicious note containing prompt-injection text that an agent later recalls.
- A stolen remote credential or cloud administrator reading remote state.
- Accidental key/database staging in a Bundle repository.
- Private Concepts exported as plaintext because encryption was unavailable.
- A sync conflict, partial upload, or stale writer overwriting newer state.
- A crafted snapshot escaping its restore directory through path traversal.
- A multi-tenant projection returning another tenant's rows.
- Key loss making encrypted Concepts unrecoverable.
- Git history retaining data after a user believes it was deleted.
- Third-party personal data stored without consent, correction, or deletion rights.

## Security invariants

1. **Files remain truth.** A remote database or vector index is disposable.
2. **No implicit secret transport.** Keys and credentials never enter a Bundle,
   manifest, log, command output, or error message.
3. **Remote private data fails closed.** A remote write must refuse private Concepts
   when encryption requirements are unmet unless a user explicitly opts into plaintext.
4. **Restore is verified.** Every restored file is constrained to the destination and
   checked against a cryptographic manifest before activation.
5. **Activation is recoverable.** Restore or rebuild writes a new target and swaps only
   after validation; an existing target is renamed, not recursively deleted.
6. **Adapters are least privilege.** Mirror adapters cannot mutate unrelated prefixes;
   projections are tenant-scoped and rebuildable.
7. **Logs are separate.** Raw transcripts do not silently become durable Concepts.
8. **Recall is untrusted input.** Agents treat recalled note bodies as user data, never
   as higher-priority instructions.

## Current controls

- Repository and generated Bundle ignore rules for keys, environment files, and local
  databases.
- Soft delete and git history provide recovery from common accidental deletion.
- Optional per-Concept encryption for configured private tags/types.
- Strict-encryption preflight before git sync setup.
- SQLite parameter binding and a narrow MCP tool schema.
- Tests for hook non-blocking behavior and core round-trips.

## Known gaps before hosted use

- Snapshot mirrors preserve Bundle bytes and cannot retroactively encrypt them.
  Remote backend APIs inspect verified snapshot bytes and refuse plaintext private
  Concepts unless the caller makes an explicit dangerous override; new formats or
  privacy markers must extend that classifier before they are remotely supported.
- Encryption-key recovery, rotation, and device revocation are not complete.
- Current encryption metadata and historical plaintext need a documented migration and
  erasure procedure.
- Git remote authentication and repository access policy are operator responsibilities.
- Note-level prompt injection is not labeled or sandboxed.
- The local MCP server has no authentication layer; stdio inherits the client's access.
- Multi-tenant RLS and isolation do not exist because a control plane is not shipped.
- Signed releases, SBOMs, and reproducible build artifacts are not yet available.
- Full consent/provenance/retention semantics for memories about other people are not
  implemented.

## Deployment modes

### Local-only

No remote configured. Best privacy boundary, but still protect the user account, key,
logs, and local backups.

### Encrypted mirror

The device encrypts private Concepts and uploads immutable verified snapshots. The
service can see tenant/bucket identifiers, object sizes, timing, and any deliberately
plaintext public Concepts, but should not receive keys.

### Zero-knowledge managed operations

The control plane stores device identity, manifest hashes, job state, audit events, and
billing. Search/decryption stays on device. Server-side semantic search is unavailable.

### Managed search (explicit opt-in)

The tenant explicitly permits server-side decryption/indexing. This is a different trust
model and must use tenant isolation, KMS-backed key handling, access logs, retention,
breach response, and qualified privacy/security review.

## Release security checklist

- Run the public CI/release gate from a clean clone.
- Scan the full diff and release artifact for secret-shaped material.
- Execute an encrypted push, local wipe, verified restore, and rebuild drill.
- Test corrupt manifest/archive and traversal payload rejection.
- Confirm no key/DSN appears in logs or errors.
- Verify remote writes are scoped to the configured namespace/prefix.
- Review migrations for plaintext copies and rollback behavior.
- Publish checksums and security-relevant release notes.
