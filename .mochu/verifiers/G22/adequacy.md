# G22 — Verifier Adequacy Audit

Claim under test: R14 (\"no secrets ever committed; sync.toml secrets via
env/keyring\") is satisfied — both halves, not just the diff-scanning half
that ship_gate already covers.

Two sub-claims, each with a distinct check:

- (a) **History cleanliness.** No secret-shaped string (AWS, GitHub, OpenAI,
  Anthropic, Slack, Google, PEM private key) appears in any git commit,
  past or present. ship_gate.py only scans diff + untracked — it cannot
  detect a secret that landed in iter-3 and was merged to main. G22 closes
  the historical gap.
- (b) **Config-shape safety.** No tracked config file (`.toml`, `.ini`,
  `.yaml`, `.yml`, `.env`) contains an inline literal `password = ...`,
  `api_key = ...`, `token = ...`, `secret_key = ...` with a 16+ char
  non-empty value. Env-var references (`$VAR`, `${VAR}`, `{{var}}`) are
  explicitly allowed and skipped — the rule is "secrets via env/keyring,
  never committed," not "no env-var syntax in config."

## Three lazy artifacts (summary list)

1. **Diff-only passthrough.** A verifier that just re-runs ship_gate's PAT
   regex against `git diff HEAD` and calls itself a "history scan" without
   actually scanning history. Misses every secret merged before the scan
   was added.
2. **Whack-a-mole with new patterns only.** A verifier that copies
   ship_gate.py's PAT verbatim and adds a few more regexes (e.g.,
   Slack tokens), but never checks the config half of R14. Misses the
   sync.toml half entirely.
3. **Config regex that flags env-var references as leaks.** A verifier
   that matches any `password = $ENV_VAR` and reports it as a secret
   leak. False-positives would push the team to remove env-var syntax
   and re-introduce plaintext secrets — the exact opposite of R14.

## How the suite blocks each

- **Artifact 1 (diff-only).** G22 runs `git log --all -p` (not diff), so
  every commit's full patch is in scope. The output reports the
  history-line count scanned (e.g., \"15804 history lines scanned\") so
  the coverage is auditable. If the count drops to \"diff-only\" (a few
  hundred lines), it's obvious something is wrong.
- **Artifact 2 (patterns only).** G22 has a second scan loop (the
  config-shape scan) that walks tracked `*.toml/*.ini/*.yaml/*.yml/*.env`
  files and applies a separate regex. Output reports
  `N config files checked`. The two scans are independent; one passing
  doesn't satisfy R14.
- **Artifact 3 (env-var false positive).** The config regex is verbose
  and case-insensitive, captures the value, and explicitly skips values
  that start with `$` or `{{`. Inline test (recorded in the commit
  message) demonstrates the skip:
  - `api_key = "$ENV_VAR"` → skipped (env-var ref)
  - `password = ""` → not matched (16-char minimum)
  - `password = "hunter2-but-actually-long-enough-to-trip"` → flagged
  This means the team's existing convention (env-var references in
  config) stays valid; only literal leaks are caught.

## Strongest-pattern check

- **EXEC (not grep).** Runs `git log -p` and `git ls-files` as
  subprocesses; reads file contents; applies structured regex with
  named captures. Auditable via the output summary.
- **Discrimination proof.** Inline test (recorded in commit message):
  - AWS key `AKIA<16 uppercase chars>` detected
  - GitHub PAT `ghp_<36 alphanumeric chars>` detected
  - Prose word "password" in a comment NOT detected
  - `password = ""` NOT detected (16-char min)
  - `api_key = "$ENV_VAR"` SKIPPED (env-var ref, not a leak)
- **Cross-references.** ship_gate.py's diff scan is the front-line
  defense (catches leaks at commit time). G22 is the historical audit
  (catches leaks that already shipped). The two are complementary, not
  duplicates — ship_gate stays in the fast path; G22 is a slower
  full-history walk run on every corpus cycle.

## Out of scope (own gaps, not G22)

- **Dependency / lockfile secret scan.** A `package-lock.json` with a
  leaked `npm` token would not be caught by G22's PAT regex (npm tokens
  use a different prefix). If/when the project ships a JS dep, G22 should
  be extended.
- **Live secret rotation.** G22 only catches secrets IN the repo. A
  secret that was committed and removed is still a leak until rotated
  with the provider. R14's \"no secrets ever committed\" is half-satisfied
  by G22; the other half is a process (rotate on detection).
- **Binary files / large files.** G22 only reads text config files
  (<1MB). A 5MB binary with a secret embedded would not be scanned.
  Tracked binary files in this repo are limited to PNG icons; the risk
  is low.
