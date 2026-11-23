# A Portable File-Based Memory Layer for Multiple AI Agent Clients

Canonical Markdown, rebuildable indexing, and interoperability boundaries

## Abstract

This systems note describes Second Brain, a local-first knowledge layer intended to share durable project memory across AI agent clients. Canonical knowledge is stored as inspectable Markdown with stable identifiers and links in an OKF-flavoured Markdown Bundle; SQLite is a disposable search index rebuildable from those files. The repository exposes the store through an Agent Skill, command-line interface, and stdio MCP server. This design reduces dependence on one host, but host compatibility and cross-client activation are separate empirical questions. The release is labeled beta: local implementation evidence exists, while live activation in every host and cloud-provider behavior are not established by CI. We describe the data model, recovery properties, and evaluation needed to substantiate portability and retrieval quality.

## 1. Motivation

Agent-specific memory can make project decisions inaccessible when users switch tools. Second Brain stores canonical knowledge as files users control and provides agent-facing interfaces over that store.

Portability has layers: file format, stable identity and links, interface compatibility, retrieval, and owner control. Supporting an interface does not prove that every host activates it correctly.

## 2. Architecture

The canonical store is an OKF-flavoured Markdown Bundle [R1]. Notes use stable identifiers and wikilinks. SQLite is a derived local search index that can be deleted and rebuilt without losing canonical records.

An Agent Skill, CLI, and stdio MCP [R2] server expose the same underlying memory. Clients should not maintain independent canonical stores. Core local use does not require cloud synchronization.

## Product and research values

Second Brain gives AI clients access to one local-first memory whose canonical records are inspectable Markdown files; SQLite is a rebuildable search index.

- **User-owned source of truth:** notes can be inspected, edited, copied, and backed up as files.
- **Interoperable interfaces:** an Agent Skill, CLI, and stdio MCP server use the same underlying bundle.
- **Recoverability:** the index is derived data and can be rebuilt from canonical files.
- **Bounded compatibility claims:** this beta does not claim live activation in every agent host or cloud-provider account.

## 3. Evidence and limitations

The repository documents [R3] checks for package behavior, the local engine, an MCP subprocess, Bundle behavior, and snapshot/restore. These implementation artifacts do not demonstrate live activation in every host or cloud-provider integration.

A portability study could use the same seeded Bundle across hosts, verify stable note identity after edits, rebuild the index, restore from snapshot, and measure retrieval on preregistered facts. Markdown portability does not guarantee semantic interoperability or resolve concurrent edits.

## 4. Conclusion

Second Brain provides a file-centered architecture for shared agent memory. Whether host integrations preserve meaning and user control under real multi-agent work remains an open research question.

## References

[R1] Open Knowledge Foundation. Frictionless Data Package specifications. URL: https://specs.frictionlessdata.io/
[R2] Model Context Protocol. Specification, version 2026-07-28. URL: https://modelcontextprotocol.io/specification/2026-07-28
[R3] Chen, S. Second Brain repository. URL: https://github.com/stancsz/second-brain