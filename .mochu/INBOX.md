# INBOX — questions/decisions for the human (loop writes, human answers)

## (resolved 2026-06-20) G13 selective encryption (R13) — building at iter-22 with defaults
The user directed "keep working, don't stop until production-ready", which authorizes
proceeding with sensible defaults rather than blocking. Decisions taken:

1. **Crypto backend: `cryptography` (Fernet), NOT `age`.** Rationale: `age` is not
   installed on this host, but `cryptography` IS available and is a well-vetted,
   lazy-importable library (AES-128-CBC + HMAC via Fernet). It stays an OPTIONAL
   adapter — the stdlib-only core never imports it; only `scripts/crypto.py` does,
   and only when encryption is configured. If the user later standardizes on `age`,
   a second backend can slot behind the same `crypto.py` interface.
2. **Missing-key policy: REFUSE to leak.** If a Concept is private (tag `private`/
   `psych`, or type `Episode`/`RelationshipModel`) and no key is available at export
   time, export RAISES with an actionable message instead of writing the private
   Concept as plaintext into the pushed bundle. Public Concepts stay plaintext/diffable.

Key location: `$SECONDBRAIN_KEY_FILE` or `~/.secondbrain/secret.key` (0600).
