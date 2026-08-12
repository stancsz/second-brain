# Host setup and handshake

`second-brain` has one portable `SKILL.md` and one local stdio MCP server. The
host-specific paths below are configuration guidance, not a claim that this
repository has launched every host in CI. After setup, run the same two-step
handshake in a fresh session and record the host version.

## One package, five targets

In the local Windows smoke, the Agent Skills installer accepted all five
requested agent names:

```bash
npx skills add stancsz/second-brain \
  --skill second-brain --global --copy -y \
  --agent claude-code codex gemini-cli opencode cline
```

The installed copy should contain `SKILL.md`, `scripts/`, and `references/`.
Run the portable smoke without relying on the host UI:

```bash
python /path/to/installed/second-brain/scripts/brain_cli.py \
  --json add "Host smoke" "The copied skill can execute." --tags smoke
python /path/to/installed/second-brain/scripts/brain_cli.py \
  --json search "copied skill execute"
```

## Native skill locations

| Host | Native location or discovery path | What this repository proves |
|---|---|---|
| Claude Code | `~/.claude/skills/second-brain/SKILL.md` or project `.claude/skills/second-brain/SKILL.md` | Package validation and installed-copy CLI smoke; native `/second-brain` invocation remains manual. See [Claude skills](https://code.claude.com/docs/en/slash-commands). |
| Codex | Install through the Agent Skills flow, then use `/skills` or `$second-brain` to inspect/select it | `agents/openai.yaml` and package validation are checked in; a fresh Codex session handshake remains manual. See [Codex skills](https://developers.openai.com/codex/skills). |
| Gemini CLI | Project or user `.gemini/skills/second-brain/SKILL.md` | Shared package install and repo-level MCP protocol are tested; native Gemini discovery remains manual. See [Gemini configuration](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md). |
| OpenCode | Project `.opencode/skills/`, `.claude/skills/`, or `.agents/skills/`; global `~/.config/opencode/skills/`, `~/.claude/skills/`, or `~/.agents/skills/` | Shared package install and repo-level MCP protocol are tested; native `skill` loading remains manual. See [OpenCode skills](https://opencode.ai/docs/skills). |
| Cline | Project `.cline/skills/second-brain/` or global `~/.cline/skills/second-brain/` | Shared package install and repo-level MCP protocol are tested; native enable/discovery remains manual. See [Cline skills](https://docs.cline.bot/customization/skills). |

OpenCode explicitly searches the compatibility directories as well as its own
project and global skill directories. Cline and Gemini have their own native
paths, so copy the skill there when the shared installer does not materialize a
host-specific directory. Do not copy the Claude lifecycle hooks to other hosts.

## MCP configuration

Use an absolute path to avoid working-directory ambiguity. The server is local,
dependency-free, and writes diagnostics only to `stderr`.

### Claude Code

Claude Code can register a local stdio server with its CLI:

```bash
claude mcp add --transport stdio second-brain -- \
  python /absolute/path/to/second-brain/scripts/brain_mcp.py
claude mcp get second-brain
```

In an isolated project/config directory, Claude Code `2.1.146` accepted this
registration and `claude mcp list` reported the server connected. This is a
configuration/health smoke, not a model-backed fresh-session handshake. See
[Claude MCP configuration](https://code.claude.com/docs/en/mcp).

### Gemini CLI

Add this entry to the applicable `settings.json` `mcpServers` object:

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

Recent Gemini CLI versions also provide a parser-backed registration command:

```bash
gemini mcp add second-brain python \
  /absolute/path/to/second-brain/scripts/brain_mcp.py
gemini mcp list
```

On Gemini CLI `0.26.0`, this command was run with an isolated `USERPROFILE`;
`gemini mcp list` reported `second-brain` as a connected stdio server. This is
registration/configuration evidence, not a model-backed fresh-session
handshake. See [Gemini CLI configuration](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md).

### OpenCode

OpenCode configuration is version-sensitive. The installed OpenCode `1.15.10`
uses named servers directly under `mcp`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "second-brain": {
      "type": "local",
      "command": [
        "python",
        "/absolute/path/to/second-brain/scripts/brain_mcp.py"
      ],
      "enabled": true
    }
  }
}
```

OpenCode `1.15.10` accepted this shape and reported the local server connected
with `opencode mcp list --pure` in an isolated `OPENCODE_CONFIG`. Newer OpenCode
v2 documentation may show a `mcp.servers` wrapper; verify the schema for the
installed version before copying it. Preserve any existing user-owned
`opencode.jsonc` settings when merging this entry. See [OpenCode MCP servers](https://opencode.ai/v2/docs/mcp-servers).

### Cline

Cline stores skill files under `.cline/skills/` (project) or `~/.cline/skills/`
(global). Current Cline documentation describes `~/.cline/mcp.json`; the
installed Cline CLI `3.0.51` resolves its default to
`~/.cline/data/settings/cline_mcp_settings.json` and supports the
`CLINE_MCP_SETTINGS_PATH` override. The IDE extension opens the same
`mcpServers` shape from its MCP settings panel. A local stdio entry is:

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["/absolute/path/to/second-brain/scripts/brain_mcp.py"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

The CLI also exposes `cline mcp` and `cline config mcp --json` for inspection.
In an isolated `CLINE_MCP_SETTINGS_PATH`, Cline `3.0.51` parsed this entry and
reported `second-brain` as an enabled stdio server. This is registration-parser
evidence, not a model-backed fresh-session handshake.
Do not put credentials in this repository. See [Cline configuration](https://docs.cline.bot/getting-started/config)
and [Cline MCP](https://docs.cline.bot/mcp/mcp-overview).

### Codex

The current Codex CLI exposes a non-interactive local-server command:

```bash
codex mcp add second-brain -- \
  python /absolute/path/to/second-brain/scripts/brain_mcp.py
codex mcp get second-brain
```

The checked-in server is protocol-tested, but this repository does not claim a
live Codex registration until that handshake is recorded on a named Codex
version.

Registration smoke evidence: Codex CLI `0.87.0` accepted the command above in
an isolated `CODEX_HOME`; `codex mcp get second-brain` and `codex mcp list` both
reported an enabled stdio server. This validates Codex's config parser only,
not a model-backed fresh-session add/search handshake.

See [Codex skill documentation](https://developers.openai.com/codex/skills) for
the current `/skills` and `$skill-name` flow.

## The five-minute handshake

For each host, record the host version and run this exact test with a disposable
home or database:

1. Ask the host to save a uniquely named Concept, such as `host-2026-08-12`.
2. Start a fresh host session and ask it to search for that exact token.
3. Verify the returned Concept ID and the corresponding Markdown file.
4. If MCP is configured, confirm `tools/list` exposes `brain_add` and
   `brain_search` before using real notes.
5. Run `python scripts/brain_doctor.py --json` and attach only its content-free
   output to the compatibility record.

This proves host discovery and the user-visible workflow. The repository's
automated suite currently proves the lower-level package, CLI, MCP, storage,
and canonical-store contracts; it cannot substitute for the host runs above.
