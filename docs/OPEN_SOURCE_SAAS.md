# Open-source SaaS strategy

The product should not start as “host every person's psychological twin.” That is a
large trust ask before the project has proven a smaller repeated job.

Start with **portable project memory for multi-agent development teams**.

## First user, payer, and job

- **First user:** an individual developer who switches among two or more AI coding
  agents and loses decisions between sessions.
- **First paying buyer:** an owner or platform/DevEx lead at a 5–30 person AI
  consultancy handling client IP.
- **Repeated job:** whenever a developer switches agent, repository, or device,
  retrieve the relevant verified project decisions and capture durable updates while
  keeping the canonical memory in storage the consultancy controls.

The acceptance test is concrete: save a decision in agent A, recall it in agent B,
then wipe and restore the memory from the customer's storage account.

## Sell a service before a platform

Offer a fixed pilot before building a broad control plane:

> **Agent Memory Portability Setup** — configure 2–5 developers, three agent hosts,
> one customer-owned storage backend, migrate existing notes, run a wipe-and-restore
> drill, and provide 30 days of support.

Test **$750–$1,500** per pilot. This is a pricing hypothesis, not market evidence.
Require three paid pilots before investing in a general hosted search or collaboration
product.

## Open-source boundary

Keep these capabilities fully usable offline and open source:

- OKF/file format, migrations, and compatibility fixtures
- local engine and rebuildable SQLite projections
- CLI and local MCP server
- git sync
- encryption and key tooling
- Obsidian import/export
- storage adapters
- agent installation/configuration generators
- conformance and compatibility test suites

Do not paywall export or storage connectors. The ownership promise fails if users must
pay to leave or to use their own infrastructure.

Charge for operating the system:

- device and workspace inventory
- scheduled sync/backup health
- restore drills and alerts
- encrypted relay
- team RBAC and audit trails
- SSO/SCIM, policy controls, SLA, and support
- managed upgrades and compatibility qualification

Keep the existing MIT core. If a self-hostable control plane is created, AGPL is a
reasonable option for that new component, subject to contributor and legal review.
Operational excellence and trust—not closed connectors—should be the moat.

## Hosted architecture and trust boundary

The local daemon is the only default plaintext writer:

```text
agent hosts
    │  local MCP / CLI
    ▼
local daemon ──► OKF Markdown Bundle (canonical)
    │                   │
    │                   ├──► SQLite index (disposable)
    │                   ├──► Git revision sync (bidirectional)
    │                   └──► encrypted snapshots (one-way mirrors)
    ▼
control plane: tenant, device, manifest hashes, job state, audit, billing
```

Use four explicit adapter categories:

1. `AgentAdapter`: Claude, Codex, Gemini, OpenCode, Cline.
2. `SyncProvider`: bidirectional revision/conflict semantics; Git remains first.
3. `MirrorBackend`: immutable encrypted snapshot/restore for object stores.
4. `ProjectionBackend`: disposable search/control-plane projections such as
   Postgres or pgvector.

Postgres and Supabase must not silently become the source of truth. Supabase Storage
can hold snapshots; Postgres can hold control-plane metadata or an optional projection
that can be erased and rebuilt from the Bundle.

An end-to-end encrypted service cannot also promise server-side plaintext search by
default. Publish two explicit modes:

- **Zero-knowledge:** decrypt and search on the user's device.
- **Managed search:** explicit tenant opt-in to server-side decryption and indexing.

## Integration order

1. Filesystem reference backend and conformance suite.
2. Generic S3-compatible snapshots (AWS S3, Cloudflare R2, MinIO, Backblaze B2,
   Wasabi, and compatible services).
3. Google Cloud Storage.
4. Azure Blob Storage.
5. Drive, OneDrive, WebDAV, and SFTP through focused/community adapters.
6. Postgres/Supabase projection after object-store recovery is proven.

A single `rclone` mirror adapter can provide broad optional coverage, but do not turn
“rclone supports it” into “second-brain live-tested it.” Publish adapter conformance and
live-provider certification separately.

## Pricing hypotheses

| Offer | Hypothesis |
|---|---:|
| Local/self-hosted OSS | Free forever |
| Setup pilot | $750–$1,500 one time |
| Managed Personal | $9–$12/month |
| Managed Team | $19–$24/user/month, $99 workspace minimum |
| Enterprise | Annual self-host/support/SLA contract |

The local product is the free tier. Avoid a permanent free hosted tier until hosting
cost and activation behavior are understood.

## Adoption loop

```text
ask an agent to install
        ↓
verified add/search handshake across two agents
        ↓
content-free compatibility + restore-health report
        ↓
shareable badge, case study, or adapter contribution
        ↓
another external user installs
```

The report must never expose note content. Telemetry is opt-in. The best promotional
artifact is a reproducible continuity/restore result, not a broad privacy slogan.

## 90-day proof plan

### Days 0–14: truth and activation

- Restore CI and the release gate.
- Resolve documentation/encryption contradictions.
- Publish the landing site and repository homepage.
- Package a versioned installable release.
- Test the add/search handshake on five named agent hosts.
- Conduct ten buyer interviews and five observed fresh installs.

**Gate:** first useful recall in under five minutes, every homepage claim backed by a
test, and two paid-pilot commitments.

### Days 15–35: portability and recovery

- Reach Obsidian compatibility level 2.
- Ship S3-compatible and GCS snapshot/restore.
- Use the shipped content-free `brain_doctor.py` report in every host and restore
  case study.
- Run encrypted wipe-and-restore drills.

**Gate:** checksum-identical restore, zero plaintext-leak tests, first paid pilot live.

### Days 36–60: BYOC operations alpha

- Build a small customer-owned-cloud control plane.
- Add Postgres/Supabase metadata projection only.
- Add device health, scheduled backups, audit, and restore alerts.

**Gate:** three paid pilots, ten external weekly active users, at least 95% successful
scheduled jobs.

### Days 61–90: public beta

- Publish one evidence-rich case study.
- Open an adapter/conformance program.
- Launch the managed/BYOC beta.

**Gate:** 20 external activated users, 30% or better week-four retention, two external
contributions, and either $300 MRR or three renewed pilots. If the gate fails, narrow
the buyer or job before adding providers.

## Hosted-launch security gates

- Remote encryption fails closed by default.
- Key recovery, rotation, device revocation, and loss behavior are documented/tested.
- Git-history erasure has a supported workflow.
- Memories carry provenance, correction, consent, and retention semantics.
- Third-party psychological data is treated as sensitive personal data.
- Multi-tenant isolation and RLS have adversarial tests.
- Releases are signed and ship checksums/SBOM.
- `SECURITY.md`, threat model, governance, DCO, and compatibility policy exist.
- “Compliant” is never claimed without an actual certification or qualified review.
