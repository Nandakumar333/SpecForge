# Data Model: Interactive AI Model Selection & Commands Directory

**Feature**: 014-interactive-model-selection
**Date**: 2026-03-18

## Entity Diagram

```text
┌─────────────────────┐      ┌──────────────────────┐
│   AgentPlugin       │      │  CommandRegistrar     │
│   (base.py)         │      │  (command_registrar)  │
├─────────────────────┤      ├──────────────────────┤
│ + agent_name()      │──────│ + register_commands() │
│ + commands_dir      │      │ + render_markdown()   │
│ + command_format    │      │ + render_toml()       │
│ + command_extension │      └──────────┬───────────┘
│ + args_placeholder  │                 │
│ + generate_config() │                 │
│ + config_files()    │                 │ writes
└─────────────────────┘                 ▼
                              ┌──────────────────────┐
                              │  Command File        │
                              │  (on disk)           │
                              ├──────────────────────┤
                              │ path: commands_dir/  │
                              │   specforge.{stage}  │
                              │   {extension}        │
                              │ content: rendered    │
                              │   template           │
                              └──────────────────────┘
                                        │
                                        │ recorded in
                                        ▼
                              ┌──────────────────────┐
                              │  config.json         │
                              │  (.specforge/)       │
                              ├──────────────────────┤
                              │ project_name: str    │
                              │ stack: str           │
                              │ agent: str           │  ← NEW
                              │ commands_dir: str    │  ← NEW
                              │ version: str         │
                              │ created_at: str      │
                              └──────────────────────┘
```

## Entities

### AgentPlugin (modified — base.py)

Existing abstract base class, extended with 3 new abstract properties:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `agent_name()` | `str` | Existing — agent identifier | `"claude"` |
| `commands_dir` | `str` | **NEW** — agent-native commands directory path | `".claude/commands"` |
| `command_format` | `str` | **NEW** — output format: `"markdown"` or `"toml"` | `"markdown"` |
| `command_extension` | `str` | **NEW** — file extension for command files | `".md"` |
| `args_placeholder` | `str` | **NEW** — agent-native argument token | `"$ARGUMENTS"` |

**Default implementations** (in `SingleFileAgentPlugin` and `DirectoryAgentPlugin`):
- `commands_dir` → derived from `_dir_path` + `/commands` or `.specforge/commands` for root-level single-file agents
- `command_format` → `"markdown"`
- `command_extension` → `".md"`
- `args_placeholder` → `"$ARGUMENTS"`

**Override examples**:
- `CopilotPlugin.commands_dir` → `".github/prompts"`; `command_extension` → `".prompt.md"`
- `GeminiPlugin.command_format` → `"toml"`; `command_extension` → `".toml"`; `commands_dir` → `".gemini/commands"`
- `GenericPlugin.commands_dir` → user-supplied path (default `"commands"`)

### CommandRegistrar (new — core/command_registrar.py)

New domain service responsible for rendering and writing command files.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `register_commands()` | `agent: AgentPlugin, target_dir: Path, context: dict, force: bool` | `Result[list[Path], str]` | Render + write all 8 stage command files |
| `render_markdown()` | `template_name: str, context: dict` | `str` | Render Markdown command via Jinja2 |
| `render_toml()` | `template_name: str, context: dict` | `str` | Render TOML command (description + prompt block) |

*Note: `write_copilot_stub()` removed — Copilot `.prompt.md` files are written via standard `register_commands()` using `command_extension=".prompt.md"` (per plan §D-07).*

**Injected dependencies**: Jinja2 `Environment` (via constructor)

**Constants** (in `config.py`):
```python
PIPELINE_STAGES: list[str] = [
    "decompose", "specify", "research", "plan",
    "tasks", "implement", "status", "check",
]
COMMAND_PREFIX: str = "specforge"
```

### Config.json (extended schema)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `project_name` | `str` | Yes | — | Project name |
| `stack` | `str` | Yes | `"agnostic"` | Technology stack |
| `agent` | `str` | Yes | `"generic"` | **NEW** — Selected AI agent |
| `commands_dir` | `str` | Yes | `"commands"` | **NEW** — Relative path to commands directory |
| `version` | `str` | Yes | `"1.0"` | Config schema version |
| `created_at` | `str` | Yes | — | ISO date |

### DetectionResult (modified — project.py)

| Field | Type | Change |
|-------|------|--------|
| `source` | `Literal["explicit", "auto-detected", "interactive", "generic"]` | **Modified** — added `"interactive"` source; `"agnostic"` → `"generic"` |

### ScaffoldResult (modified — project.py)

| Field | Type | Change |
|-------|------|--------|
| `agent_source` | `Literal["explicit", "auto-detected", "interactive", "generic"]` | **Modified** — added `"interactive"`; `"agnostic"` → `"generic"` |
| `commands_written` | `list[Path]` | **NEW** — list of command files written |

## State Transitions

```text
init_cmd.py flow:

  ┌─────────────┐
  │ Parse flags  │
  └──────┬──────┘
         │
         ▼
  ┌──────────────────┐
  │ --agent provided? │──Yes──► detect_agent(explicit=agent)
  └──────┬───────────┘         source = "explicit"
         │ No
         ▼
  ┌──────────────────┐
  │ stdin.isatty()?   │──No──► detect_agent()
  └──────┬───────────┘        source = "auto-detected" or "generic"
         │ Yes
         ▼
  ┌──────────────────┐
  │ Prompt.ask()     │
  │ agent selection  │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ "generic"?       │──Yes──► Prompt.ask() for commands_dir
  └──────┬───────────┘
         │ No
         ▼
  ┌──────────────────┐
  │ Build scaffold   │
  │ + register cmds  │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Write config.json│
  │ (agent + dir)    │
  └──────────────────┘
```

## Validation Rules

| Field | Rule | Error |
|-------|------|-------|
| `commands_dir` (custom) | Must be relative path | "Commands directory must be a relative path" |
| `commands_dir` (custom) | Must not contain `..` | "Commands directory must not traverse outside project root" |
| `commands_dir` (custom) | Must not be absolute | "Commands directory must be a relative path" |
| Agent selection | Must be in plugin registry or "generic" | Rich Prompt validates via `choices` param |
