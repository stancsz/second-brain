# Documentation map

Start with the documents that describe the current, tested product:

1. [Compatibility and evidence](./COMPATIBILITY.md) — exact host, Obsidian,
   storage, and test boundaries.
2. [Host setup and handshake](./HOST_SETUP.md) — native skill paths, MCP
   configuration shapes, and the reproducible five-minute host test.
3. [Project review](./PROJECT_REVIEW.md) — candid readiness score and remaining
   world-class gates.
4. [Threat model](./THREAT_MODEL.md) — sensitive-data and remote-sync risks.
5. [Open-source SaaS plan](./OPEN_SOURCE_SAAS.md) — buyer, product boundary,
   pricing hypotheses, architecture, and 90-day validation gates.
6. [Storage contract](../references/storage.md) — immutable snapshot and restore
   guarantees.
7. [Public release checklist](./RELEASE_CHECKLIST.md) — local, host, provider,
   GitHub, and SaaS proof gates.

`index.html` and `assets/` are the static GitHub Pages site. The Pages workflow
publishes only those public files; it does not upload the internal design notes.

## Historical design records

Documents `01` through `10`, `brief.md`, `board.md`, `HANDOFF.md`, `PROTOCOL.md`,
and `tasks/` record earlier decisions and proposals. They are useful history, but
they are not an implementation-status ledger. In particular, old references to
`.mochu`, native cloud SDK adapters, `age` encryption, release counts, or a
`growth/` directory may describe plans that changed.

The current implementation uses:

- optional Fernet encryption via `cryptography`;
- a generic rclone provider adapter plus PostgreSQL/Supabase snapshots;
- the checked-in public test and release gates;
- an OKF-flavoured Markdown Bundle with a rebuildable SQLite projection.

When a historical design record conflicts with code, tests, or
`COMPATIBILITY.md`, treat the current evidence as authoritative.
