# second-brain

**让 Claude、Codex、Gemini、OpenCode 和 Cline 共用一份记忆——并以你拥有的文件保存。**

[![CI](https://github.com/stancsz/second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/stancsz/second-brain/actions/workflows/ci.yml)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-validated-1f6feb)](https://agentskills.io/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-151713)](LICENSE)

[English](README.md)

`second-brain` 是面向 AI Agent 的本地优先知识图谱。它以 OKF 风格的
Markdown Bundle 为权威存储，SQLite 只是可随时重建的搜索索引。同一份记忆可通过
Agent Skill、命令行界面和 stdio MCP 服务器访问。

> **Beta，但有证据。** 仓库已包含并测试 Skill 包、本地引擎、MCP 子进程、
> Obsidian 格式行为、快照/恢复路径以及 200 多项测试。目前 CI 尚未覆盖五种 Agent
> 宿主的真实激活，也没有连接真实云服务账户。详见[兼容性矩阵](docs/COMPATIBILITY.md)。

## 为什么做这个项目

让一个 Agent 记住架构决策，再切换到另一个工具，新 Agent 通常又要从零开始。
托管式记忆产品通过在你和自己的历史之间再加入一家供应商来解决这个问题。

`second-brain` 选择相反的路径：

- **文件是真相来源。** 笔记始终是可检查的 Markdown，带稳定 ID 和 wikilink。
- **Agent 只是客户端。** Claude、Codex、Gemini、OpenCode 和 Cline 可加载同一开放
  Skill；MCP 客户端可通过 JSON-RPC 访问同一个 Brain。
- **索引可以替换。** 删除 SQLite 后，可从 Bundle 重建并继续使用。
- **存储归你。** Git 负责双向同步；不可变快照可保存到本地磁盘、rclone 提供商、
  PostgreSQL 或 Supabase。
- **无需账户。** Python 核心只使用标准库。

## 安装 Skill

使用开放的 Agent Skills 安装器，把同一个包安装到五种目标宿主：

```bash
npx skills add stancsz/second-brain \
  --skill second-brain --global --copy -y \
  --agent claude-code codex gemini-cli opencode cline
```

这条命令已在本仓库上执行，并能识别上述五个宿主名称。在项目建立持续维护的宿主
版本矩阵之前，各宿主应用中的实际激活仍需人工冒烟测试。

更喜欢直接克隆，或只想使用 CLI？

```bash
git clone https://github.com/stancsz/second-brain.git
cd second-brain
python scripts/brain_cli.py add "Atlas storage decision" \
  "Markdown is canonical; SQLite is rebuilt from it." \
  --collection Decisions --tags atlas,architecture
python scripts/brain_cli.py search "Why SQLite?"
```

数据默认创建在 `~/.secondbrain/`。使用 `--db PATH` 可隔离另一套 Brain。

## 各宿主的支持情况

| 能力 | Claude Code | Codex | Gemini CLI | OpenCode | Cline |
|---|---:|---:|---:|---:|---:|
| Agent Skill 包 | 已验证 | 包已验证 | 文档化目标 | 文档化目标 | 文档化目标 |
| 本地 stdio MCP 服务器 | 协议测试通过 | 协议测试通过 | 协议测试通过 | 协议测试通过 | 协议测试通过 |
| 自动捕获/召回 hooks | 已测试 | — | — | — | — |

“协议测试通过”表示仓库会启动 MCP 子进程，并在隔离的 home 目录中测试
`initialize`、`tools/list`、`brain_add` 和 `brain_search`。这不表示已自动完成每个
宿主的注册界面。[证据矩阵](docs/COMPATIBILITY.md)明确区分仓库测试、包验证、
文档化目标和真实宿主验证缺口。

Claude Code 用户可选装仓库附带的 `Stop`、`PreCompact` 和
`UserPromptSubmit` hooks：

```bash
bash install.sh
```

安装器会合并设置，不会直接覆盖原设置。启用任何生命周期 hook 前请先审查；
会话捕获涉及敏感数据。

## 核心工作流

```text
Claude / Codex / Gemini / OpenCode / Cline
                 │
        Agent Skill · MCP · CLI
                 │
        OKF Markdown Bundle       ← canonical
          ├── SQLite FTS index    ← rebuildable
          ├── git history         ← bidirectional sync
          └── snapshots           ← one-way restore mirrors
```

常用命令：

```bash
# Capture and recall
python scripts/brain_cli.py add "Decision" "Use customer-owned storage" --tags decision
python scripts/brain_cli.py search "customer storage"
python scripts/brain_cli.py show <id-or-title>

# Organize and connect
python scripts/brain_cli.py list --collection Decisions --sort updated
python scripts/brain_cli.py relate <from-id> <to-id> --type references
python scripts/brain_cli.py traverse <id> --depth 2

# Recoverable lifecycle
python scripts/brain_cli.py delete <id>
python scripts/brain_cli.py restore <id>
python scripts/brain_cli.py summary
```

运行 `python scripts/brain_cli.py --help` 查看全部命令，包括时间点召回、情绪感知
召回、提炼、归档和 Brain 合并。

## MCP

启动无额外依赖的 stdio 服务器：

```bash
python /absolute/path/to/second-brain/scripts/brain_mcp.py
```

按宿主所需的 MCP 配置格式注册该命令。常见配置为：

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["/absolute/path/to/second-brain/scripts/brain_mcp.py"]
    }
  }
}
```

服务器和 CLI 使用同一个本地数据库。诊断信息写入 `stderr`，`stdout` 只输出
JSON-RPC。

## Obsidian 兼容性

每个 Concept 导出为一个 Markdown 文件：

```bash
python scripts/brain_cli.py export --format markdown --output ./MyVault
```

递归导入 vault（`.md` 和 `.markdown`）：

```bash
python scripts/brain_cli.py import ./MyVault --merge
```

仓库测试覆盖 YAML frontmatter、CRLF 输入、递归目录、`[[alias|label]]`、标题/区块
片段、wikilink 与手工关系共存，以及从 OKF 重建手工关系。这是 **Level 1 vault
兼容性**，并非原生 Obsidian 插件或实时双向同步。简单 vault 导入器不会保留任意
未知 YAML 属性，带路径的链接也不会按 basename 解析。若 vault 已高度自定义，
请先在副本上验证。

## Git 同步

OKF Bundle 是双向同步主干：

```bash
python scripts/sync.py ~/.secondbrain/okf <git-remote> ~/.secondbrain/brain.db
```

同步会先导出文件并提交，再 pull/rebase；冲突 Markdown 会停放为
`*.conflict.md`，随后 push 并重建 SQLite。生成的 Bundle `.gitignore` 会阻止密钥、
数据库和环境机密模式被暂存。

## 备份：本地、S3/GCS/Azure/R2/B2、Postgres、Supabase

备份是不可变、内容寻址的快照。它们有意设计为单向恢复镜像，而不是并发编辑协议。

本地参考后端：

```bash
python scripts/storage_cli.py push --backend local \
  --store ./backups --bundle ~/.secondbrain/okf
python scripts/storage_cli.py pull --backend local \
  --store ./backups --dest ./restored-okf
python scripts/bundle.py rebuild ./restored-okf ./restored-brain.db
```

任何已配置的 [rclone](https://rclone.org/) remote 都使用同一种已验证的快照格式。
因此可以覆盖 S3、GCS、Azure Blob、Cloudflare R2、Backblaze B2、MinIO、Wasabi
等多种提供商，同时无需把凭据写在该 CLI 的命令行中：

```bash
python scripts/storage_cli.py push --backend rclone \
  --remote s3:my-bucket/second-brain --bundle ~/.secondbrain/okf
```

PostgreSQL 和 Supabase 使用按需加载的可选适配器：

```bash
pip install "psycopg[binary]"
export SECONDBRAIN_POSTGRES_DSN='postgresql://...'
python scripts/storage_cli.py push --backend postgres \
  --bundle ~/.secondbrain/okf
```

这里将 Supabase 视为 PostgreSQL：用 `--dsn-env SUPABASE_DB_URL` 从命名环境变量
传入数据库连接字符串。CI 没有连接真实云账户。精确保证和恢复行为见
[存储契约](references/storage.md)。

## 远程同步前的安全要求

本地数据库和普通 Markdown 导出都是明文。配置密钥后，可选 Fernet 加密会保护
带 `private` 或 `psych` 标签的 Concept，以及 `Episode` 和
`RelationshipModel` 类型：

```bash
pip install cryptography
python scripts/crypto.py init
export SECONDBRAIN_REQUIRE_ENCRYPTION=1
```

在任何远程导出或快照之前，务必设置 `SECONDBRAIN_REQUIRE_ENCRYPTION=1`。若未启用
严格模式且没有配置密钥，旧版导出路径只会警告，仍可能把敏感 Concept 写成明文。
远程快照只保留 Bundle 原始字节，不会额外加密。作为纵深防御，rclone 与
PostgreSQL/Supabase 后端会检查已验证的快照，并在任何远程 I/O 之前拒绝可识别的
明文私密 Concept。仅为特殊迁移保留了刻意危险的
`--allow-plaintext-private` 覆盖选项。

处理心理数据或第三方个人数据前，请阅读[安全政策](SECURITY.md)和
[威胁模型](docs/THREAT_MODEL.md)。切勿同步 `secret.key`。

## 证据与开发

复现公开发布门槛：

```bash
python scripts/validate_skill.py .
python scripts/run_corpus.py
python scripts/ship_gate.py
```

集成测试套件包含 200 多项测试，覆盖引擎、CLI、OKF 导出/重建、同步、加密路径、
MCP 子进程、Skill 打包、Obsidian 格式行为和存储快照。CI 在 Ubuntu、Windows 和
macOS 上以 Python 3.10 与 3.14 运行；缺少可选加密依赖或平台前提时，相关测试会
跳过。

项目状态和剩余验证门槛：

- [兼容性与证据](docs/COMPATIBILITY.md)
- [独立项目评审](docs/PROJECT_REVIEW.md)
- [安全政策](SECURITY.md)
- [威胁模型](docs/THREAT_MODEL.md)
- [存储契约](references/storage.md)

## 开源 SaaS 方向

开源核心应保持完整的离线可用性，包括格式、CLI、SQLite 投影、MCP、Obsidian
路径、加密、Git 同步、备份契约和提供商适配器。付费产品可以运营其周边最困难的
部分：

- 设备与工作区集群健康状态；
- 定时加密快照与恢复演练；
- BYOC 控制平面、RBAC、审计、SSO/SCIM、告警和支持；
- 团队入门与迁移。

建议先向小型 AI 咨询公司提供付费的 **Agent Memory Portability Setup**，验证需求
后再建设广泛托管平台。完整的目标买家、定价假设、技术边界和 90 天验证门槛见
[开源 SaaS 方案](docs/OPEN_SOURCE_SAAS.md)。

## 贡献

请从一个明确写出用户可见行为和所需证据的 Issue 开始。新增存储适配器应遵循
快照契约，而不是把外部服务变成权威存储。新增 Agent 集成应加入真实的宿主版本
握手验证，而不只是配置片段。

提交 Pull Request 前请运行发布门槛。安全问题请遵循[安全政策](SECURITY.md)，
不要创建公开 Issue。

MIT 许可。你的知识就是你的思想史；把文件留在自己手里。
