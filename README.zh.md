# second-brain | 长脑子

> **拥有你的心理分身,而不是租一个。** 一个本地文件型容器,为一个*真实的人*建模 —— TA 的决策、偏好,以及背后的情绪,带双时态有效期与事实更替(supersession);同时也是 AI agent 原生读写的 OKF v0.1 知识图谱。一个 SQLite 文件,零依赖,数据完全归你,靠 git 多设备同步。
>
> [English](./README.md) · [架构设计](./references/architecture.md) · [Skill 定义](./SKILL.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org)
[![Dependencies: 0](https://img.shields.io/badge/dependencies-0-green.svg)](#安装)
[![Schema: v2.1](https://img.shields.io/badge/schema-v2.1-blueviolet.svg)](./scripts/schema.sql)

---

> **那些"数字心智"平台,想把你租回给你自己。** Delphi、Personal.ai,以及它们身后的一整波 —— 它们很乐意造一个 AI 版的*你*:你的声音、你的决策、你的性格,然后存在它们的服务器上,锁在它们的 API 后面,按它们的定价收费。你的心理分身,变成一笔月供。哪天条款一改、价格一涨、或者公司被收购了,"你是谁"这个模型,就跟着易主。这是世上最私密的数据,而整个行业都在抢着替你托管它。

> `second-brain` 押注另一边:**你的分身,是你自己 git 里的一堆纯 markdown。** 关于这个人的每一条记忆 —— TA 做过什么决定、偏好什么、当时是什么情绪、以及这些在*什么时候*为真 —— 都躺在你能读、能 diff、能版本化、能永远带走的文件里。没有哪个厂商拥有"你"这个模型。不存在"迁移计划",因为根本没谁可迁。**没有人让你*拥有*自己的心理分身,只让你*租*。这就是全部的意义。**

> 换个更糙的说法:你不是在养第二个脑子,你在租一个。每隔几年,房租就涨一次 — 导出要 Pro、API 收紧、公司差点倒闭(或者被收购)。你迁一次数据,丢一次结构,然后循环重来。`second-brain` 的赌注是另一边:一个文件,在你的 home 目录,版本化在你的 git repo。从来没进过别人的服务器,所以也没什么好迁的。

---

## 这是什么

`second-brain` 是一个为 AI agent 设计的个人知识存储。笔记保存在 `~/.secondbrain/brain.db` 这一个 SQLite 文件中,只依赖 Python 标准库 —— 没有 `pip install`,没有 `docker compose up`,没有云服务账号。

笔记之间通过正文里的 `[[wikilinks]]` 自动建立关联,在你写作的同时就构建出知识图谱。系统支持全文检索、类型化关系、标签、集合、软删除,以及与 Markdown 的双向导出。

仓库根目录的 `SKILL.md` 让 `second-brain` 成为一个开箱即用的 [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills):任何加载该 skill 的 agent 都能在对话中保存、搜索、链接你脑子里的笔记。

## 这是用来做什么的

整个行业都在抢着造你的**数字分身** —— 然后把它托管起来。`second-brain` 是同一个野心,只是把所有权反过来:**分身归你,在你的磁盘上,在你的 git 里。** 它用同一套文件,干两件事。

### 1. 拥有一个真人的"心理分身"(深层目标)

把自动捕获 hook 接到你真实的会话上,脑子会悄悄把一个*人*的耐久信号 —— TA 的决策、偏好、知识,以及背后的情绪 —— 提炼成一条条带标题的 concept,绝不是原始聊天。让它成为*分身*、而不是一堆便签的,是这几样:

- **Subject(主体,`sb_subject`)** 把每条记忆归到*它讲的是谁/是什么*,一句查询就能拉出某个人的人格子图。
- **结构化情绪(`sb_affect`)** 记录一条记忆背后的情绪效价/唤起度/情绪类型 —— 这是"知道关于某人的一个事实"和"知道 TA 对此*什么感受*"之间的区别。
- **双时态有效期(`sb_valid_from`/`sb_valid_to`)+ 事实更替(supersession)** 让这个人的模型随 TA 的变化保持最新 —— `supersede()` 关掉旧的有效区间,而不是删掉它 —— 同时仍可按历史回溯:`recall --as-of <日期>` 能还原 *TA 在过去任意一天是什么样*。人不是快照;它建模的是一条轨迹。

久而久之,这会沉淀成一个归你所有、不断生长的容器,刻画一个真人到底怎么想、怎么感受、怎么变 —— 这正是一个 agent 想忠实"影"住某个具体的人(而不是演一个泛泛的角色)所需要的地基。而因为它就是纯 OKF markdown,你能用文本编辑器打开"你自己"这个模型,一行行读。

### 2. 给 agent 一个人格

同一套原语,指向一个虚构的主体,就给了 agent 一个耐久的**人格**:有自己的历史、偏好和情绪色彩的一致性格,存成你拥有的文件,而不是每开一次新会话都要重贴一遍的 system prompt。

### 把话说清楚

捕获流水线、心理字段、双时态历史,**今天就已经能跑**(见[功能](#功能))。在这之上做一个开箱即用的"模仿我"agent,是**方向,不是成品** —— 而且单论模仿的逼真度,那些拿了大钱的云平台跑得更靠前。`second-brain` *现在*能保证、而它们都给不了的,是**底座归你**:一个人的模型永远不被租走、不黑盒、不被一个随时能改条款或消失的厂商锁住。

## 租来的数字分身 vs 自己拥有的心理分身

| | "你"住在哪 | 模型归你吗 | 心理结构 | 它们跑路 / 改条款时 |
|---|---|---|---|---|
| **Delphi / Personal.ai**(数字心智平台) | 它们的云 | 不归 —— 托管,按它们的条款和定价 | 有,但私有且黑盒 | "你"这个模型跟着它们走 |
| **Letta / MemGPT** | 你的基础设施或它们的云 | 部分(运行时可自托管) | agent 状态记忆块 —— 不是对人的建模 | 你留下的是个运行时,不是可带走的分身 |
| **Mem0 / Zep** | 厂商云 / API | 不归 / 部分 | 双时态图谱(Zep),但为 *agent* 记忆而设计 | 厂商说了算;Zep 的社区版已被弃用 |
| **second-brain** | **你的 git,纯 markdown** | **完全归你** | **Subject + 双时态有效期 + 情绪 + 事实更替,写在你能读的 OKF 里** | **什么都不变 —— 那是你的文件** |

云平台赢在能力 —— 声音、逼真度、规模。`second-brain` 赢在那条事后再也补不回来的轴:**分身归你。** 而那个交集 —— *归你所有、本地、文件型、且有心理结构* —— 据我们所能查到,除了这个项目,是空的。

## 为什么做这个

目前大多数"AI 记忆"产品都把你的数据存放在第三方云端,API 收费,而且供应商可以随时调整定价、政策,甚至关停。即使是 Obsidian 这类本地优先的工具,也无法原生与 agent 对接 —— 你最终要在两个工具之间切换:一个给"人"用,一个按调用付费给"AI"用。

`second-brain` 是一个克制的替代方案:

- **一个文件。** SQLite 数据库,任何客户端都能打开,`cp` 就能复制,`rsync` 就能备份,`git` 就能版本化。
- **标准 schema。** 表结构以 `scripts/schema.sql` 形式直接进仓库,纯 SQL —— 没有私有格式,没有迁移服务。
- **Agent 原生。** 每个操作都是一条 CLI 命令。Agent 和人用同一套接口读、同一套接口写。
- **零依赖。** 只要 Python 3.8+ 和 SQLite,就能跑。

## 功能

- **扁平知识图谱。** 笔记(Concept)携带标签、可选的 collection(集合),以及类型化的关系。没有需要维护的目录树。
- **`[[wikilinks]]` 自动建链。** 正文里的双向链接在写入时即被解析,关系永远不会与正文漂移。
- **Pending links(待定链接)。** 指向尚未存在笔记的前向引用会先存在一张带索引的表里,目标笔记一创建就自动转正。
- **全文检索。** SQLite FTS5,自动忽略软删除的笔记。在 5 万条笔记规模下返回结果 < 100ms。
- **软删除是默认。** `delete` 可撤销;`delete --hard` 才是永久删除。
- **类型化关系。** `references`(引用)、`contradicts`(矛盾)、`expands`(扩展)、`related`(相关),可附 strength(强度)权重。
- **图谱遍历。** 基于递归 CTE,从任一节点出发遍历子图。
- **导入 / 导出。** 支持 JSON、Markdown(兼容 Obsidian)、CSV 三种格式的双向转换。
- **Distill 与 Archive。** 目标导向的 `distill --query "X"` 写出一个聚焦的工作脑子(原脑子不动,加 `--activate` 才替换);`archive --older-than-days 180` 把长期不碰的笔记搬到冷库,顺手 VACUUM 把工作脑子收小。要找回来用 `merge-brain --from <archive>`。
- **多设备同步(靠 git)。** 把脑子导出成 Bundle、commit、pull/rebase/push,在另一台设备 rebuild。Git 是唯一的同步主干;两台设备改同一条笔记会停泊成 `*.conflict.md` 而不是互相覆盖。全程可离线。
- **心理记忆地基。** 笔记可携带 **subject**(这条记忆讲的是谁/什么;支撑人格子图)、**时间有效期**(`sb_valid_from`/`to`;支撑历史回溯)、**情绪**(效价/唤起度/情绪类型)与**事实更替**(新事实顶替旧事实,但不删旧的)。这些字段都写在 OKF frontmatter 里 —— 合起来,就是一个归你所有、会生长的"对人的模型",而不是一堆扁平笔记(见[这是用来做什么的](#这是用来做什么的))。
- **按标签选择性加密。** 标了 `private` 的笔记在远端是密文,普通笔记照样可 diff —— 私密的部分上锁,其余的留着可读。
- **日志归日志,脑子保持干净。** `Stop` hook 把每次会话的完整原始 transcript 存成 `~/.secondbrain/logs/` 下的纯文件——绝不写进脑子。脑子(`brain.db`)只放*提炼后*的 know-how:会话结束时 agent 抽取出来的决策、偏好、事实、可复用知识,以及你显式保存的内容。检索知识时不会再翻出一大堆原始聊天记录。
- **主动回忆。** `UserPromptSubmit` hook 会拿你每条 prompt 去检索干净的脑子,在 agent 回答*之前*把相关笔记注入上下文——你不用主动问"我对 X 知道些什么"。
- **`/history` 斜杠命令。** 浏览磁盘上的对话日志,挑一条进去看。
- **Phase 2(规划中)。** 通过 `sqlite-vec` 提供的可选向量检索,以及 MCP server 接口。

## 安装

```bash
git clone https://github.com/stancsz/second-brain.git
cd second-brain
python3 scripts/brain_cli.py stats    # 首次运行会自动创建 ~/.secondbrain/brain.db
```

可选 —— 把命令缩短成 `brain`:

```bash
ln -s "$(pwd)/scripts/brain_cli.py" /usr/local/bin/brain
# 或
alias brain='python3 ~/path/to/second-brain/scripts/brain_cli.py'
```

唯一运行依赖是 Python 3.8+ 自带的 `sqlite3`。Schema 使用 FTS5、JSON1、递归 CTE:Python 自带 SQLite 3.9+ 已包含这些,否则需要 SQLite 3.41+。

## 快速上手

```bash
# 存
python3 scripts/brain_cli.py add "RAG" "检索增强生成" \
  --collection AI --tags rag,llm

# 找
python3 scripts/brain_cli.py search "RAG"

# 连(正文里的 [[RAG]] 自动解析为 references 关系;
# 如果 RAG 还不存在,就进 pending_links,等 RAG 创建时自动连上)
python3 scripts/brain_cli.py add "Vector Search" "见 [[RAG]]" --collection AI

# 遍历图谱
python3 scripts/brain_cli.py related <id>
python3 scripts/brain_cli.py traverse <id> --depth 2

# 脑子健康度
python3 scripts/brain_cli.py summary

# Distill:基于目标做聚焦,原脑子留着做时间点备份
python3 scripts/brain_cli.py distill --query "RAG" --output focused.db --activate

# Archive:把长期不碰的笔记挪到冷库,工作脑子收小
python3 scripts/brain_cli.py archive --output archive-2026.db --older-than-days 180

# 把归档的笔记找回来
python3 scripts/brain_cli.py merge-brain --from archive-2026.db

# 浏览历史对话日志(也提供 /history 斜杠命令)
ls -1t ~/.secondbrain/logs/*/*/*.jsonl 2>/dev/null | head

# 导出(兼容 Obsidian)
python3 scripts/brain_cli.py export --format markdown --output brain.md
```

## 在 Claude Code 中使用

本仓库本身就是一个 Claude Code skill —— `SKILL.md` 定义了触发条件与行为契约。三种安装方式:

**项目级**(只对当前项目生效):

```bash
mkdir -p .claude/skills
git clone https://github.com/stancsz/second-brain.git .claude/skills/second-brain
```

**个人级**(所有项目都生效):

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/stancsz/second-brain.git ~/.claude/skills/second-brain
```

**Submodule**(锁定版本,跟随项目升级):

```bash
git submodule add https://github.com/stancsz/second-brain.git .claude/skills/second-brain
```

装好后,agent 会自动识别 "记一下"、"我之前写过 X 吗"、"catch me up on project Y" 这类表达,并从你脑中的笔记里找答案。

### 自动捕获每次对话(可选,但推荐)

要让脑子**自动记住所有对话**,把仓库里的 `settings.example.json` 拷到你的 Claude Code 配置里:

```bash
# 个人级:所有项目、所有对话都生效
cp <repo>/settings.example.json ~/.claude/settings.json
# 然后编辑,把里面的 /path/to/second-brain 替换成真实路径

# 或项目级:只对当前项目生效
cp <repo>/settings.example.json .claude/settings.json
# 然后编辑
```

设计原则就一句:**日志归日志,脑子保持干净。** 原始 transcript 进 `~/.secondbrain/logs/` 纯文件;提炼出的 know-how 进脑子。这会接入三个 hook:

- **`Stop`**(`hooks/capture_conversation.py`)— 把 transcript 存到磁盘日志,然后提示 agent 一次,把这次对话里值得留下的决策/偏好/事实提炼成干净的 concept 存进脑子(不是原始 transcript)。静默、不会卡住会话,审计写在 `hooks/capture_conversation.log`。
- **`PreCompact`** *(可选)* — 长会话上下文压缩前快照一份日志,不做提炼。觉得吵就注释掉。
- **`UserPromptSubmit`**(`hooks/recall_memories.py`)— 主动回忆:拿每条 prompt 检索干净的脑子,把相关笔记注入上下文。

环境开关:`SECONDBRAIN_SKIP_CAPTURE=1`(关捕获)、`SECONDBRAIN_SKIP_DISTILL=1`(只记日志、不提示提炼)、`SECONDBRAIN_SKIP_RECALL=1`(关主动回忆)、`SECONDBRAIN_LOGS_DIR=/path`(改日志目录)。

要临时关掉,不删除 hook:

```bash
SECONDBRAIN_SKIP_CAPTURE=1 claude
```

### `/history` 斜杠命令

仓库里 `commands/history.md` 是一个斜杠命令,用来浏览磁盘上的对话**日志**(`~/.secondbrain/logs/` 里的文件,不是脑子)。软链一下就能用(`install.sh` 会替你做):

```bash
# 个人级
mkdir -p ~/.claude/commands
ln -s <repo>/commands/history.md ~/.claude/commands/history.md
```

之后输入 `/history`,agent 就会列出最近的会话日志,挑一条可读地展示出来。你也可以直接说"给我看看最近的 3 次对话"。从那里还能按需把某条日志**提炼**进脑子。

## 与同类工具的对比

| 工具 | 数据位置 | Agent 可读 | 锁定 | 备份 | 跨会话记忆 | 安装方式 |
|---|---|---|---|---|---|---|
| Notion AI | Notion 云 | 否 | 高 | 厂商控制 | 否 | 浏览器 |
| ChatGPT Memory | OpenAI 云 | 否 | 完全黑盒 | 厂商控制 | 是(不可见) | 浏览器 |
| Claude Projects | Anthropic 云 | 否 | 高 | 厂商控制 | 是(项目内) | 浏览器 |
| mem0 | 厂商 Postgres | 是(按 API 收费) | 中(SDK 绑定) | 厂商控制 | 是(API) | `pip install` + key |
| Obsidian | 本地 `.md` | 否(需插件) | 无 | 手动 | 否(自己接) | 桌面 App |
| Logseq | 本地 `.md` | 否 | 无 | 手动 | 否 | 桌面 App |
| Anytype | 本地(P2P) | 否 | 无 | 手动同步 | 否 | 桌面 App |
| Quivr / privateGPT | 本地向量库 | 通过 API | 无 | 手动 | 否 | Docker + 模型 |
| Apple Notes / Keep / OneNote | 厂商云 | 否 | 高 | 厂商控制 | 否 | 系统自带 |
| Evernote | 厂商云 | 否 | 高(历史教训) | 厂商控制 | 否 | 桌面 / Web |
| **second-brain** | **本地 SQLite** | **是(CLI)** | **无** | **`cp` / `git push`** | **是(agent 原生)** | **`git clone`** |

**这份列表里,只有 `second-brain` 能给的承诺:**

1. **数据完全归你。** 存储就是一个普通 SQLite 文件,`sqlite3 brain.db` 直接打开。Schema 在仓库里以 `scripts/schema.sql` 形式维护。没有"导出"这个流程,因为从来没有进过别人的服务器。
2. **可版本化。** 整个脑子就一个文件。`git init` 它,`git push` 到私人 GitHub repo,免费拿到历史、diff、灾备。
3. **Agent 原生。** CLI 就是 API。不存在一个独立的"AI 模式"需要你再付一笔钱。

## 适合你,如果

- 你使用 AI agent(Claude Code、Cursor、Aider、Continue、自建脚本),并希望它们跨会话"记得"。
- 你希望知识库在任何一家供应商消失后依然存在。
- 你能接受一个 200 行的 Python CLI + 一个 SQLite 文件。
- 你希望人和 agent 用同一份数据、同一个接口。

## 不适合你,如果

- 你要的是面向非技术用户的所见即所得笔记 App → 用 Obsidian 或 Notion。
- 你要的是带权限、评论的团队 Wiki → 用 Notion 或 Confluence。
- 你要存几百万条文档、跑大规模向量检索 → 用专业向量数据库;`second-brain` 是个人量级的。
- 你本地不能跑 Python → 用托管笔记服务。

## 架构

参见 [`references/architecture.md`](./references/architecture.md),包含:

- 数据模型(3 张表 + FTS + `pending_links`)
- FTS5 正确性说明(v2 的 bug 与 v2.1 的修复)
- Wikilink 解析规则(写时冻结)
- 软删除语义
- Phase 2 的 MCP 接口契约
- v1 → v2 迁移
- 性能目标

## 备份策略

推荐方案:把 `~/.secondbrain/brain.db` 放进一个私人 GitHub repo 做版本化。整个数据库就一个文件,即使 5 万条笔记也通常 < 100 MB,`git push` 完全没问题。

要持续备份,可配 [litestream](https://litestream.io/) 把 WAL 流复制到 S3、Backblaze 或任何 S3 兼容的对象存储。Schema 迁移与灾难恢复都是标准 SQLite 操作。

## 路线图

- **v2.1(当前)。** FTS5、软删除、写时冻结的 wikilinks、`pending_links` 表、递归遍历。
- **Phase 2。** MCP server 接口,基于 `sqlite-vec` 的语义检索,相似度超阈值时自动建立 `inferred` 类型关系。
- **北极星 —— 被"影"住的那个人。** 心理记忆层(subject / 双时态有效期 / 情绪 / 事实更替)加上自动提炼循环,是让一个 agent 能忠实"影"住某个*具体*真人的地基。接下来要做的:从子图做更丰富的人格合成、跨事实更替的漂移/一致性检查,以及一个能还原"这个人在 X 日是什么样"的回忆接口,给"模仿 agent"打底。
- **想法。** Markdown 双向同步、Obsidian 兼容导出改进、本地加密副本。

## 贡献

欢迎提 Issue 和 PR。Schema 就是 API —— 加表、加列前请先开个 Issue 讨论。

## 许可

[MIT](./LICENSE) © 2026 second-brain contributors
