# Governance

`second-brain` uses lightweight maintainer governance suitable for a small
open-source project. The goal is to make decisions in public without creating a
committee before the contributor community needs one.

## Principles

1. Users own the canonical Markdown Bundle and can leave without an export
   negotiation.
2. Compatibility and security claims are bounded by reproducible evidence.
3. Local operation remains useful without a hosted service or account.
4. Provider and agent integrations extend the core; they do not redefine its
   portable format.
5. Private note contents and credentials never belong in public project
   artifacts.

## Roles

- **Contributors** open issues, propose designs, write code or documentation,
  test releases, and review work.
- **Maintainers** are the people who currently hold write, triage, or release
  permission on this repository. They review changes, protect the compatibility
  and security contracts, merge pull requests, and publish releases.

Roles are based on demonstrated stewardship, not employment, sponsorship, or a
paid product relationship. Maintainers may grant or remove repository
permissions as the project and contributor community evolve. This document does
not name people so the repository permissions remain the current source of
truth.

## Decisions

Routine fixes and additive improvements are decided through pull-request
review. A maintainer may merge a focused change when the public gate is green,
the evidence matches the claim, and material review concerns are resolved.

Changes to the Bundle/schema contract, snapshot format, security boundary,
host lifecycle automation, licensing, or open-core boundary should begin in a
public issue or draft pull request. The proposal should state the user problem,
alternatives, migration or compatibility impact, security impact, and proof
plan.

The project seeks rough consensus, but does not require formal voting. If
consensus is not available, the maintainer responsible for the affected area
makes the decision and records the rationale and trade-offs in the issue or pull
request. Decisions can be revisited when new evidence appears.

## Review and releases

- Authors disclose known limitations, skipped checks, and relevant conflicts of
  interest.
- Reviewers evaluate behavior, tests, privacy, portability, migration risk, and
  documentation; passing CI alone is not approval.
- Releases require the public release gate in [CONTRIBUTING.md](CONTRIBUTING.md)
  to pass from the release candidate.
- Compatibility claims use the evidence levels in
  [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

Maintainers may use a private path for embargoed vulnerability work. Reporting
and disclosure follow [SECURITY.md](SECURITY.md); this governance document adds
no separate response-time promise.

## Commercial work

Commercial services may fund development, but payment does not buy undisclosed
governance control or weaker review. Changes developed for a hosted offering
must preserve the repository's license and state clearly which behavior is open
source, external, proposed, or live-verified.

## Changes to governance

Propose governance changes by pull request with the motivation and expected
effect. Maintainers merge them through the same public decision process. If the
project grows enough to need elections, working groups, or a foundation, those
mechanisms should be added only when there are real participants to operate
them.
