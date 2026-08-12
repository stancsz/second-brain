# Verified Bundle snapshots

This is the first storage tranche for SecondBrain. It backs up the canonical
OKF Bundle as immutable, content-addressed snapshots. It does **not** make a
cloud database authoritative, and it does **not** replace git as the only
bidirectional multi-device sync path.

## Guarantees

`scripts/storage.py` creates an uncompressed tar whose bytes are deterministic
for the same Bundle bytes:

- files are ordered by their Bundle-relative POSIX paths;
- tar timestamps, owner ids/names, and modes are normalized;
- `.git/` is excluded;
- symlinks, Windows junctions/reparse points, special files, unsafe paths, and
  cross-platform case collisions are refused;
- every file has a size and SHA-256 in a canonical JSON manifest;
- the manifest also pins the tar byte length and SHA-256;
- the snapshot id is the SHA-256 of the canonical manifest bytes.

The snapshot is verified immediately after creation and again after every pull.
Restore never uses `tar.extractall()`: it validates all members, stages regular
files under a new sibling directory, and only then swaps the verified directory
into place.

An existing non-empty destination is refused by default. `--force` is still
non-destructive: the old destination is renamed to a unique
`<name>.pre-restore-<UTC timestamp>` sibling and that backup path is returned.
It is never removed automatically.

Obsidian-format extensions such as `sb_obsidian_path` and
`sb_obsidian_frontmatter` are ordinary canonical Bundle bytes, so they are
included in snapshots and restored with the rest of the Bundle.

## CLI

Local filesystem (reference backend):

```powershell
python scripts/storage_cli.py push --backend local `
  --store D:\secondbrain-backups --bundle $HOME\.secondbrain\okf

python scripts/storage_cli.py list --backend local `
  --store D:\secondbrain-backups

python scripts/storage_cli.py pull --backend local `
  --store D:\secondbrain-backups --dest D:\restored-okf
```

Choose a specific snapshot with `pull --snapshot <64-hex-id>`. Omit it to use
the newest complete snapshot reported by the backend. Pass `--json` before the
subcommand for machine-readable output.

After restoring the Bundle, rebuild the disposable SQLite index explicitly:

```powershell
python scripts/bundle.py rebuild D:\restored-okf D:\restored-brain.db
```

That low-level rebuild is a disposable projection. To use the restored files as
the normal paired working store, open them once through the coordinator:

```powershell
python scripts/brain_cli.py --db D:\restored-brain.db `
  --bundle D:\restored-okf stats
```

This records a local pair receipt and refuses later stale or mixed-generation
writes. The receipt is included in verified snapshots but ignored by the
Bundle's Git repository, so separate checkouts regenerate their own receipt.

### rclone: S3, GCS, Azure Blob, R2, B2, Drive, OneDrive, WebDAV, SFTP, and more

Use a preconfigured rclone remote. Credentials stay in rclone's configuration;
they are never accepted by this CLI.

```powershell
python scripts/storage_cli.py push --backend rclone `
  --remote s3:my-bucket/secondbrain --bundle $HOME\.secondbrain\okf

python scripts/storage_cli.py pull --backend rclone `
  --remote gcs:my-bucket/secondbrain --dest D:\restored-okf
```

The same adapter accepts any configured rclone remote, including AWS S3,
Cloudflare R2, Google Cloud Storage, Azure Blob, Backblaze B2, MinIO, Wasabi,
Google Drive, OneDrive, WebDAV, and SFTP. The provider name belongs in the
rclone remote configuration; this project does not pretend that a generic
adapter is a provider-specific certification.

The adapter lazily invokes the `rclone` executable and uses only:

- `copyto --checksum --immutable` for `<snapshot-id>.tar` and its manifest;
- `lsjson` for listing;
- `cat` for a verified pull.

It never invokes `sync`, `delete`, or a shell. Uploading the same snapshot is
safe; an immutable remote object cannot be replaced through this adapter.

Remote pushes fail closed when a plaintext Markdown Concept is tagged `private`
or `psych`, has `sb_private: true`, or has type `Episode` or
`RelationshipModel`. An encrypted envelope is accepted only when its marker is
exactly `sb_encrypted: fernet` and its body is one canonical URL-safe Base64
token with a plausible Fernet frame version and length. A truthy-but-wrong
marker or plaintext body does not bypass the gate. This structural check cannot
authenticate the token without the user's key; rebuild performs actual Fernet
decryption/HMAC verification. The gate runs on the exact snapshot bytes in both
the rclone and Postgres backend APIs, before any network/dependency call.

### Postgres and Supabase

Install the optional adapter only where it is needed:

```powershell
pip install "psycopg[binary]"
$env:SECONDBRAIN_POSTGRES_DSN = "postgresql://..."
python scripts/storage_cli.py push --backend postgres `
  --bundle $HOME\.secondbrain\okf
```

The backend creates `secondbrain_snapshots` with one row per snapshot. The tar
and canonical manifest are opaque `BYTEA` values inserted in the same database
transaction; the manifest-derived id is the primary key. An idempotent repeat
is accepted only if both stored byte strings are identical and verify.
Listing also reconstructs and verifies each stored snapshot, so a corrupt row
is reported as an integrity failure rather than advertised as a healthy backup.

Supabase uses the same Postgres adapter. Keep its DSN in a named environment
variable and select that name without exposing the DSN on the command line:

```powershell
$env:SUPABASE_DB_URL = "postgresql://..."
python scripts/storage_cli.py list --backend postgres --dsn-env SUPABASE_DB_URL
```

Use `--table schema.table` when the default table is not suitable. Both name
parts are strictly validated and quoted; arbitrary SQL is rejected.

## Python API

```python
from storage import LocalBackend, create_snapshot, restore_snapshot

snapshot = create_snapshot("~/.secondbrain/okf")
backend = LocalBackend("D:/secondbrain-backups")
backend.push(snapshot)

verified = backend.pull(snapshot.snapshot_id)
result = restore_snapshot(verified, "D:/restored-okf")
```

All adapters implement `push(snapshot)`, `pull(snapshot_id=None)`, and `list()`.
Optional dependencies are resolved only when their adapter is called. Missing
dependencies/configuration produce `StorageError` subclasses with an actionable
message rather than breaking local snapshot support at import time.

### Community adapter contract

An adapter is compatible when it preserves the same `Backend` protocol and
these invariants:

1. `snapshot_id` is the lowercase SHA-256 identity of the canonical manifest;
   it is the only remote object/row key.
2. `push()` is idempotent for identical bytes and raises
   `SnapshotConflictError` if an existing id maps to different bytes.
3. `list()` and `pull()` verify the manifest, archive, member hashes, and id
   before returning anything; incomplete pairs and orphan objects are errors,
   not healthy snapshots.
4. Remote `push()` calls the plaintext-private gate before network or database
   I/O, and only the explicit dangerous override can bypass it.
5. Restore uses `restore_snapshot()` so traversal, links, unsafe paths, and
   non-empty destinations retain the same protections across providers.

The local and fake-rclone backends in `tests/test_storage.py` are reference
implementations. New adapters should copy their contract cases and add a
provider-specific emulator or live qualification record; a provider logo alone
is not compatibility evidence.

For an exceptional, deliberate plaintext remote upload, both remote backend
constructors accept `allow_plaintext_private=True`, and the CLI exposes the
conspicuous `push --allow-plaintext-private` override. The CLI prints a warning.
This is never enabled implicitly and does not affect local snapshots.

## Trust boundary and current limits

- These backends are one-way backup mirrors. They do not merge concurrent edits.
- Snapshotting preserves the Bundle bytes exactly; it does not encrypt plaintext.
  Remote pushes refuse known private plaintext by default. Configure the existing
  Bundle encryption path and use `SECONDBRAIN_REQUIRE_ENCRYPTION=1` when exporting;
  the upload gate is defense in depth, not a replacement for fail-closed export.
- Restore produces a verified Bundle but intentionally does not rebuild or swap
  a user's working `brain.db`; use the explicit coordinator step above when a
  paired working store is wanted. Files remain authoritative.
- Native cloud SDK adapters, schedules/retention, remote pruning, key recovery,
  and hosted multi-tenant controls are later tranches. rclone is the current
  broad provider surface.
