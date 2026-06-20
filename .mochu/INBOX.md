# INBOX — questions/decisions for the human (loop writes, human answers)

## G13 selective encryption (R13) — deferred from iter-19 to its own WIP chain
The mechanical selector ranked G13 top (release-linked, rotation-allowed) at iter-19,
but it was deferred because it is a security-sensitive crypto feature that warrants a
milestone chain + careful review, not a single inline build. Two direction decisions
to confirm before building (defaults proposed):

1. **Crypto backend** — `age` CLI binary (external tool, simple, the design-doc default)
   vs Python `cryptography` lib (pip dep, in-process, no shell-out). Default proposal:
   `age` via lazy subprocess, since it matches the memory'd design and keeps Python deps
   at zero (it's a tool, not an import).
2. **Missing-backend policy** — when a `private`/`Episode`/`RelationshipModel` Concept
   is about to be pushed but no encryption backend/key is configured, should sync
   (a) REFUSE to push those concepts (safe default, proposed), or (b) warn-and-skip, or
   (c) warn-and-push-plaintext? Proposed: (a) refuse — never leak private data silently.

If you don't answer, the loop will build M1 with the proposed defaults (age + refuse).
