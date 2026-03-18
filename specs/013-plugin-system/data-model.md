# Data Model: Plugin System for Multi-Agent and Multi-Stack Support

**Feature**: 013-plugin-system | **Date**: 2026-03-18

## Entities

### StackPlugin (ABC)

Abstract base class for technology stack plugins. Each method receives architecture type.

| Field | Type | Description |
|-------|------|-------------|
| plugin_name | str (abstract property) | Unique identifier (e.g., "dotnet", "python") |
| description | str (abstract property) | Human-readable description |
| supported_architectures | list[ArchitectureType] (abstract property) | Architectures this plugin supports |

**Methods**:
- `get_prompt_rules(arch: ArchitectureType) → dict[str, list[PluginRule]]` — Returns domain-keyed rule overrides
- `get_build_commands(arch: ArchitectureType) → list[str]` — Build command suggestions
- `get_docker_config(arch: ArchitectureType) → DockerConfig | None` — Container configuration (None for monolith)
- `get_test_commands() → list[str]` — Test command suggestions
- `get_folder_structure(arch: ArchitectureType) → dict[str, str]` — Recommended folder layout

### AgentPlugin (ABC) — EXISTING

Already defined in `plugins/agents/base.py`. No changes needed.

| Field | Type | Description |
|-------|------|-------------|
| agent_name | str (abstract method) | Unique identifier (e.g., "claude", "cursor") |

**Methods**:
- `generate_config(target_dir: Path, context: dict[str, Any]) → list[Path]` — Generate config files, return written paths
- `config_files() → list[str]` — List of config file names this agent produces

### PluginRule

Data class representing a single governance rule override from a stack plugin.

| Field | Type | Description |
|-------|------|-------------|
| rule_id | str | Unique rule identifier (e.g., "BACK-DOTNET-MS-001") |
| title | str | Human-readable rule title |
| severity | str | "ERROR" or "WARNING" |
| scope | str | What the rule applies to |
| description | str | Rule body (the actual governance text) |
| thresholds | dict[str, str] | Key-value threshold pairs |
| example_correct | str | Correct code example |
| example_incorrect | str | Incorrect code example |

**Relationship**: StackPlugin.get_prompt_rules() returns `dict[str, list[PluginRule]]` where keys are governance domain names (e.g., "backend", "database", "cicd").

### DockerConfig

Optional container configuration returned by stack plugins for microservice architectures.

| Field | Type | Description |
|-------|------|-------------|
| base_image | str | Docker base image (e.g., "python:3.11-slim") |
| build_stages | list[str] | Multi-stage build stage descriptions |
| exposed_ports | list[int] | Default ports to expose |
| health_check_path | str | Health check endpoint path |

### PluginRegistry

Internal data structure within PluginManager. Not a user-facing entity.

| Field | Type | Description |
|-------|------|-------------|
| stack_plugins | dict[str, StackPlugin] | name → instance mapping |
| agent_plugins | dict[str, AgentPlugin] | name → instance mapping |

### PluginManager

Orchestrates discovery, loading, registration, and lookup.

| Field | Type | Description |
|-------|------|-------------|
| _registry | PluginRegistry | Internal plugin storage |
| _project_root | Path or None | Project root for custom plugin discovery |

**Methods**:
- `discover() → Result[int, str]` — Scan built-in + custom plugin directories, return count
- `get_stack_plugin(name: str) → Result[StackPlugin, str]` — Lookup by name
- `get_agent_plugin(name: str) → Result[AgentPlugin, str]` — Lookup by name
- `list_stack_plugins() → list[StackPlugin]` — All registered stack plugins
- `list_agent_plugins() → list[AgentPlugin]` — All registered agent plugins

## Relationships

```text
PluginManager
├── discovers → StackPlugin instances (3 built-in + custom)
├── discovers → AgentPlugin instances (25+ built-in + custom)
└── provides to → init_cmd.py

init_cmd.py
├── calls → PluginManager.get_stack_plugin(stack)
├── calls → PluginManager.get_agent_plugin(agent)
├── calls → StackPlugin.get_prompt_rules(arch) → dict[str, list[PluginRule]]
├── passes rules to → PromptFileManager.generate(..., extra_rules_by_domain=...)
└── calls → AgentPlugin.generate_config(target_dir, context)

PromptFileManager
├── renders → base governance templates (existing)
├── appends → PluginRule formatted as markdown
└── writes → .specforge/prompts/*.prompts.md (merged files)

PromptContextBuilder (UNCHANGED)
└── reads → .specforge/prompts/*.prompts.md → concatenates in precedence order
```

## State Transitions

Plugins are stateless. No lifecycle state transitions.

PluginManager has a simple lifecycle:
1. **Uninitialized** → `discover()` → **Ready**
2. **Ready** → `get_stack_plugin()` / `get_agent_plugin()` → returns plugin or error

## Validation Rules

- StackPlugin.plugin_name must be non-empty and match `[a-z][a-z0-9_-]*`
- PluginRule.rule_id must be non-empty and match `[A-Z]+-[A-Z0-9-]+`
- PluginRule.severity must be "ERROR" or "WARNING"
- Custom plugins must implement all abstract methods (validated at load time)
- Plugin names must be unique within their type (stack or agent); custom overrides built-in with warning
