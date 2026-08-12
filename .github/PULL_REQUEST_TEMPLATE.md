## Outcome

Describe the user-visible behavior this pull request adds or fixes.

Closes #

## Scope and design

- What changed:
- Why this is the smallest useful change:
- Bundle/schema, privacy, network, or migration impact:
- Known limitations:

## Evidence level

Check the highest level this pull request actually demonstrates.

- [ ] Proposed/documented only
- [ ] Package-validated
- [ ] Repo-tested with checked-in synthetic tests
- [ ] Live-verified in the named host/provider below

Live environment, exact version, operating system, and date (if applicable):

## Validation

Paste concise results; do not paste private data or credentials.

```text
python scripts/validate_skill.py .
python scripts/run_corpus.py
python scripts/ship_gate.py
```

- [ ] The public release gate passes.
- [ ] New or changed behavior has regression and failure-path coverage.
- [ ] Documentation and `docs/COMPATIBILITY.md` match the demonstrated evidence.
- [ ] Any skipped or unavailable check is named above rather than reported as passing.

## Data safety

- [ ] Tests, logs, screenshots, and examples use only synthetic notes.
- [ ] This change includes no brain database, transcript, private note, key,
      token, DSN, provider configuration, identifying path, or other secret.
- [ ] Security-sensitive behavior follows `SECURITY.md` and
      `docs/THREAT_MODEL.md`.

## Storage adapter checklist (when applicable)

- [ ] Not applicable, or the full checklist in `CONTRIBUTING.md` is completed.
- [ ] The Bundle remains authoritative and the adapter is an immutable mirror.
- [ ] Push/pull/list, idempotency, integrity, corruption, missing dependency,
      and missing configuration paths are tested.
- [ ] Credentials use provider configuration or a named environment variable
      and never appear in process arguments or output.
- [ ] Provider limits and the difference between repo-tested and live-verified
      behavior are documented.

## Host compatibility handshake (when applicable)

- [ ] Not applicable, or the handshake template in `CONTRIBUTING.md` is attached.
- [ ] The exact host version, OS, install scope, package commit, and date are named.
- [ ] Skill discovery/selection and CLI save/recall were tested with one
      synthetic Concept, or the untested step is explicit.
- [ ] MCP `initialize`, `tools/list`, `brain_add`, and `brain_search` were tested
      when the host supports stdio MCP, or the limitation is explicit.

## Reviewer focus

Call out the files, assumptions, or risks that deserve the closest review.
