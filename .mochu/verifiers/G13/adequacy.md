# Adequacy audit: selective-encryption (G13 / R13)

Three lazy artifacts that would pass a weak suite — and how this suite blocks each:

1. **Marks the file `sb_encrypted: true` but leaves the body plaintext** — a
   "fix" that adds the marker and an encrypted SIDE field but still writes the
   real content in the clear, so the secret is on the git remote anyway. Blocked
   by Phase 3: asserts the literal secret string is ABSENT from the file bytes on
   disk (not merely that a marker exists), and Phase 5 still proves round-trip, so
   the encryption must be real and reversible.

2. **Encrypts the concept file but leaks the title via index.md / log.md** — the
   per-concept file is ciphertext, but the auto-generated bundle index and update
   log (also pushed to the remote) list the private concept's title and a body
   snippet. Blocked by Phase 4: asserts the private title appears in neither
   index.md nor log.md, while the public title still does.

3. **Silently writes plaintext when no key is configured** — encryption only
   engages if a key happens to be present; with no key, the private concept is
   exported as plaintext (worst case: the user thinks it's protected). Blocked by
   Phase 6: with no key, export must RAISE and the suite greps the whole bundle to
   assert the plaintext secret was not written anywhere.

The suite exercises the real export→rebuild path end to end and drives a
subprocess (Phase 7) that encrypts, writes to disk, reads the raw bytes back, and
asserts ciphertext + round-trip — blocking a fix that only works in-process.
