# 05 — Backup Backends & Encryption

## Backend (backup) interface
```python
class Backend(Protocol):
    name: str
    def push(self, bundle_dir: Path, manifest: Manifest) -> PushResult: ...
    def pull(self, dest: Path) -> PullResult: ...      # for restore / seed
    def list(self) -> list[RemoteEntry]: ...
```
Each adapter lazy-imports its SDK; a missing dep yields a clear "pip install / configure" error
instead of an import crash. Core SecondBrain stays dependency-free.

| Adapter | Mechanism | Notes |
|---|---|---|
| `GitRemote` | `git push/pull/rebase` | **The sync spine, not a backup** — the only bidirectional channel. |
| `S3Backend` | `boto3` or shell `aws s3 sync` | Object-store mirror of the Bundle tree. |
| `GCSBackend` | `google-cloud-storage` or `gsutil rsync` | Native OKF home (GCS is OKF's reference target). |
| `GDriveBackend` | **prefer connected Drive MCP**, else SDK | Reuse the session's Drive connector before raw SDK. |
| `OneDriveBackend` | **prefer connected OneDrive MCP**, else Graph API | Same pattern. |
| *future* `CloudDBBackend` | serialize Bundle → rows | "Any cloud DB" — out of MVP, one new class. |

Config in `~/.secondbrain/sync.toml`; secrets via env / OS keyring, **never committed**.
All cloud adapters are **one-way mirrors** of the git tree. Restore path = `pull` into an empty
Bundle, then rebuild the DB.

## Encryption — selective by tag
The diffability-vs-privacy tension is resolved **per-Concept**, not globally.

- A Concept is encrypted-at-rest iff `sb_private: true`, or it carries a configured trigger tag
  (defaults: `private`, `psych`, `therapy`). **Default: all `Episode` and `RelationshipModel`
  Concepts are private** unless explicitly marked public.
- Mechanism: **age** (`age`/`rage` CLI or `pyrage`), one recipient key per device; keys never
  committed. Encrypted Concept stored as `<slug>.md.age`.
- A *plaintext* sidecar `<slug>.meta` keeps `type`, `sb_id`, `tags`, `timestamp` so the index/graph
  still function without the key. You can search titles/tags; **bodies need the key** (accepted gap).
- Plaintext Concepts stay fully diffable and Obsidian-readable.
- Encryption happens at **serialize / pre-push**. Configurable: "encrypt only on push" vs
  "encrypt at rest locally too".

## Restore & disaster recovery
1. `brain restore --from <backend>` → pulls Bundle into `~/.secondbrain/okf/`.
2. Decrypt `*.md.age` with the device key (or import a key).
3. `brain rebuild` → fresh `brain.db`.
4. Optionally re-attach the git remote and resume sync.
