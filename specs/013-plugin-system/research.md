# Research: Plugin System for Multi-Agent and Multi-Stack Support

**Feature**: 013-plugin-system | **Date**: 2026-03-18

## R-01: Plugin Discovery Pattern for Python Packages

**Decision**: Module-scanning discovery using `importlib` + naming conventions

**Rationale**: The plugin system needs to discover built-in plugins from the installed package and custom plugins from project directories. Python's `importlib` provides reliable introspection of package contents. Entry-point-based discovery (setuptools entry_points) is overkill for an internal plugin system where all built-in plugins ship in the same package. Module scanning with naming convention (`*_plugin.py`) is simpler, faster, and doesn't require package rebuild for new plugins.

**Alternatives Considered**:
- **setuptools entry_points**: Too heavy; requires package metadata modification for each new plugin. More appropriate for third-party plugin ecosystems.
- **Explicit registration in __init__.py**: Fragile; easy to forget when adding a new plugin. Defeats the purpose of automatic discovery.
- **Plugin config file (plugins.json)**: Unnecessary indirection; the file system IS the registry.

**Implementation**:
```python
# Discovery algorithm
def _discover_built_in_stacks() -> dict[str, type[StackPlugin]]:
    """Scan plugins/stacks/ for *_plugin.py modules, import, find StackPlugin subclasses."""
    pkg = importlib.import_module("specforge.plugins.stacks")
    pkg_path = Path(pkg.__file__).parent
    plugins = {}
    for path in pkg_path.glob("*_plugin.py"):
        module = importlib.import_module(f"specforge.plugins.stacks.{path.stem}")
        for cls in _find_subclasses(module, StackPlugin):
            plugins[cls().plugin_name()] = cls
    return plugins
```

---

## R-02: Rule Override Merge Strategy

**Decision**: Stack plugins return PromptRule-compatible dicts keyed by governance domain. PromptFileManager appends plugin rules to generated governance files during init.

**Rationale**: The spec clarification confirms "rule overrides only, layered on top of base governance rules." The existing governance file format uses `### RULE-ID: Title` blocks with structured fields (severity, scope, rule, threshold, example_correct, example_incorrect). Plugin-provided rules follow the same format and are appended after the base template rules. This keeps governance files as the single source of truth — PromptContextBuilder reads them unchanged.

**Alternatives Considered**:
- **Template-level Jinja2 conditionals**: Would require `{% if architecture == "microservice" %}` blocks in every governance template. Mixes data with presentation. Makes templates harder to maintain.
- **Runtime rule injection in PromptContextBuilder**: Would require loading plugins every time context is built. Governance files wouldn't reflect the full rule set, confusing users who inspect them.
- **Separate plugin rule files alongside governance files**: Additional file management complexity. Users would need to understand two rule sources.

**Merge algorithm**:
1. PromptFileManager renders the base governance template (e.g., `backend.dotnet.md.j2`) → base content
2. PluginManager calls `StackPlugin.get_prompt_rules(arch)` → `dict[str, list[PluginRule]]`
3. For each domain, plugin rules are formatted as markdown rule blocks via the `plugin_rule_block.md.j2` Jinja2 template (constitution II compliance: no string concatenation for file output) and appended to the rendered base content
4. Checksum is recomputed over the complete content (base + plugin rules)
5. Final merged file is written to `.specforge/prompts/`

---

## R-03: Agent Plugin Config File Patterns

**Decision**: Group agent plugins by config file pattern to maximize code reuse. Use a `SingleFileAgentPlugin` base for agents that write one file, and `DirectoryAgentPlugin` for agents that write to a directory.

**Rationale**: Of the 25+ agents, the majority use one of a few patterns:
1. **Single dotfile**: `.cursorrules`, `.windsurfrules`, etc. — same format, different path
2. **Single markdown**: `CLAUDE.md`, `CODEX.md`, etc.
3. **Directory-based**: `.github/copilot-instructions.md` + `.github/prompts/`, `.gemini/`, etc.

Creating a class hierarchy reduces the ~25 agent implementations to mostly configuration (file path, template name) with only 3-4 requiring custom logic.

**Agent groupings**:

| Pattern | Agents | Base Class |
|---------|--------|------------|
| Single dotfile | Cursor, Windsurf, Roo Code, Kilo Code, Trae, Antigravity | `SingleFileAgentPlugin` |
| Single markdown | Claude Code, Codex CLI, Amp, Auggie CLI, CodeBuddy CLI, IBM Bob, Jules, opencode, Pi, Qoder, Qwen, SHAI, Tabnine, Mistral Vibe, Kimi Code | `SingleFileAgentPlugin` |
| Directory-based | GitHub Copilot, Gemini CLI, Kiro CLI | `DirectoryAgentPlugin` |
| Custom | Generic (user-specified path) | Direct `AgentPlugin` subclass |

---

## R-04: Architecture Type Parameterization in Stack Plugins

**Decision**: Use `ArchitectureType` string literal type (existing) as the parameter to all StackPlugin methods. Plugins return empty/None for unsupported combinations.

**Rationale**: The existing `ArchitectureType = Literal["monolithic", "microservice", "modular-monolith"]` is already defined in config.py and used throughout the codebase. Stack plugins receive this as a parameter and branch internally. For modular-monolith, plugins should return monolith base rules + boundary enforcement additions.

**Rule differentiation by architecture**:

| Domain | Microservice Rules | Monolith Rules | Modular-Monolith Rules |
|--------|-------------------|----------------|----------------------|
| backend | Per-service app patterns, container build, event handlers, isolated data context | Single app, shared data context, mediator pattern, no containers/events | Monolith rules + strict module boundary enforcement, interface contracts |
| database | Per-service schema, migration per service, no cross-service joins | Single schema, shared migrations, module-scoped tables | Module-scoped schemas within single DB, enforced access boundaries |
| cicd | Per-service pipeline, container registry, health checks | Single pipeline, single deployment artifact | Single pipeline with module-level test gates |

---

## R-05: PromptFileManager Integration Points

**Decision**: Modify `PromptFileManager.generate_one()` to accept optional `extra_rules: list[PluginRule]` parameter. Rules are formatted and appended after template rendering, before checksum computation.

**Rationale**: Minimal change to existing code. The existing flow is: render template → compute checksum → inject checksum → write. The new flow inserts one step: render template → append plugin rules → compute checksum → inject checksum → write. The `generate()` method is updated to accept a `plugin_rules_by_domain` dict and pass the appropriate rules to each `generate_one()` call.

**Modified init_cmd.py flow**:
```
1. CLI receives --stack, --agent, --arch
2. detect_agent() / StackDetector.detect() (existing, unchanged)
3. PluginManager.get_stack_plugin(stack) → StackPlugin instance
4. PluginManager.get_agent_plugin(agent) → AgentPlugin instance
5. stack_plugin.get_prompt_rules(arch) → dict[str, list[PluginRule]]
6. ScaffoldBuilder.build_scaffold_plan() (existing, unchanged)
7. ScaffoldWriter.write_scaffold() (existing, unchanged)
8. PromptFileManager.generate(project_name, stack, extra_rules_by_domain=plugin_rules)  ← MODIFIED
9. agent_plugin.generate_config(target_dir, context) → list[Path]  ← NEW STEP
10. git init (if enabled, existing)
11. Print summary (existing)
```

---

## R-06: Custom Plugin Loading from Project Directory

**Decision**: Scan `.specforge/plugins/stacks/` and `.specforge/plugins/agents/` for `*_plugin.py` files. Load using `importlib.util.spec_from_file_location()`. Validate interface compliance before registration.

**Rationale**: Project-level custom plugins allow teams to extend SpecForge for proprietary stacks. Using `importlib.util.spec_from_file_location()` allows loading Python modules from arbitrary paths without modifying `sys.path` permanently. Interface validation catches common errors (missing methods) early with helpful messages.

**Safety**: Custom plugins execute arbitrary Python code. This is acceptable because:
- SpecForge runs in the developer's local environment (not a server)
- The developer explicitly placed the file in their project
- Same trust model as pip installing a package

**Error handling**: Each custom plugin load is wrapped in try/except. Failures log a Rich warning with the file path and error, then continue loading remaining plugins. No crash.

---

## R-07: Agent Config File Format Research

**Decision**: Each agent plugin uses Jinja2 templates for config file generation, stored in `src/specforge/templates/base/agents/`. Templates receive governance context (project name, stack, architecture, rules summary) and produce agent-specific output.

**Rationale**: Using Jinja2 templates (consistent with the rest of SpecForge) keeps agent config generation auditable and editable. Templates produce markdown/text output tailored to each agent's expected format. The `AgentPlugin.generate_config()` method renders the template and writes it to the correct location.

**Key agent config locations**:

| Agent | Config Path | Format | Base Class |
|-------|------------|--------|------------|
| Claude Code | `CLAUDE.md` | Markdown with slash commands | SingleFile |
| GitHub Copilot | `.github/copilot-instructions.md` + `.github/prompts/*.md` | Markdown | Directory |
| Cursor | `.cursorrules` | Plain text rules | SingleFile |
| Gemini CLI | `.gemini/style-guide.md` | Markdown | Directory |
| Windsurf | `.windsurfrules` | Plain text rules | SingleFile |
| Codex CLI | `AGENTS.md` | Markdown | SingleFile |
| Kiro CLI | `.kiro/rules.md` | Markdown | Directory |
| Amp | `AMP.md` | Markdown | SingleFile |
| Auggie CLI | `AUGGIE.md` | Markdown | SingleFile |
| CodeBuddy CLI | `CODEBUDDY.md` | Markdown | SingleFile |
| IBM Bob | `.bob/rules.md` | Markdown | Directory |
| Jules | `JULES.md` | Markdown | SingleFile |
| Kilo Code | `.kilocode` | Plain text rules | SingleFile |
| opencode | `OPENCODE.md` | Markdown | SingleFile |
| Pi Coding Agent | `PI.md` | Markdown | SingleFile |
| Qoder CLI | `QODER.md` | Markdown | SingleFile |
| Qwen Code | `QWEN.md` | Markdown | SingleFile |
| Roo Code | `.roo/rules.md` | Markdown | Directory |
| SHAI (OVHcloud) | `SHAI.md` | Markdown | SingleFile |
| Tabnine CLI | `TABNINE.md` | Markdown | SingleFile |
| Mistral Vibe | `MISTRAL.md` | Markdown | SingleFile |
| Kimi Code | `KIMI.md` | Markdown | SingleFile |
| Antigravity (agy) | `.agy/rules.md` | Markdown | Directory |
| Trae | `.trae/rules.md` | Markdown | Directory |
| Generic | User-specified directory | Markdown | Direct subclass |
