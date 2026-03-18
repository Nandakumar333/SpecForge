# Feature Specification: Plugin System for Multi-Agent and Multi-Stack Support

**Feature Branch**: `013-plugin-system`  
**Created**: 2026-03-18  
**Status**: Draft  
**Input**: User description: "Build the plugin system for multi-agent and multi-stack support"

## Clarifications

### Session 2026-03-18

- Q: How many stack plugins ship in v1? → A: Three — .NET, Node.js, Python. Go and Java deferred to v2.
- Q: How many agent plugins ship in v1? → A: All supported agents (25+) including Claude Code, GitHub Copilot, Cursor, Gemini CLI, Windsurf, Codex CLI, Kiro CLI, Amp, Auggie CLI, CodeBuddy CLI, IBM Bob, Jules, Kilo Code, opencode, Pi Coding Agent, Qoder CLI, Qwen Code, Roo Code, SHAI (OVHcloud), Tabnine CLI, Mistral Vibe, Kimi Code, Antigravity (agy), Trae, and a Generic fallback for unsupported agents.
- Q: Should plugins version their prompt rules? → A: No versioning in v1. Rules evolve with SpecForge releases. Stack-version differentiation deferred.
- Q: Should StackPlugin.get_prompt_rules() return full rules or rule overrides? → A: Rule overrides only, layered on top of base governance rules. Cross-cutting domains (security, testing, architecture) inherited from defaults; plugins provide stack-specific additions/overrides for domains like backend, database, cicd.
- Q: How should the plugin system interact with Feature 003's PromptContextBuilder? → A: PromptContextBuilder is the downstream consumer — it remains UNCHANGED. Plugin rule overrides are fed into PromptFileManager, which appends formatted rules to governance files after template rendering. PromptContextBuilder reads the merged governance files and concatenates them in precedence order. Plugins are decoupled from context assembly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stack-Aware Prompt Generation (Priority: P1)

As a developer using a specific technology stack (e.g., Python, .NET, Node.js), I want SpecForge to generate prompt files whose content is tailored to both my stack AND my chosen architecture pattern, so that my AI coding agents receive accurate, context-specific guidance rather than generic instructions.

**Why this priority**: This is the core value proposition of the plugin system. Without architecture-aware stack plugins, all prompt files contain the same generic content regardless of whether the project is a microservice or monolith — making the governance system ineffective for real-world projects.

**Independent Test**: Can be fully tested by running `specforge init --stack python --arch microservice` and verifying the generated `backend.prompts.md` contains Python-specific microservice patterns (e.g., FastAPI per-service, containerized deployment, event-driven communication) and does NOT contain .NET or Node.js rules.

**Acceptance Scenarios**:

1. **Given** a new project directory, **When** a user runs `specforge init --stack python --arch microservice`, **Then** `backend.prompts.md` contains Python-specific microservice rules including per-service application patterns, containerized deployment guidance, event-driven communication patterns, and per-service data model isolation.
2. **Given** a new project directory, **When** a user runs `specforge init --stack python --arch monolithic`, **Then** `backend.prompts.md` contains Python monolith rules including single-application patterns, module communication via internal calls, shared data model configuration, and NO container orchestration or event bus rules.
3. **Given** a new project directory, **When** a user runs `specforge init --stack dotnet --arch microservice`, **Then** `backend.prompts.md` contains .NET microservice rules including per-service application patterns, containerized multi-stage build guidance, inter-service communication protocols, event handler patterns, and per-service data context isolation.
4. **Given** a new project directory, **When** a user runs `specforge init --stack nodejs --arch microservice`, **Then** `backend.prompts.md` contains Node.js-specific microservice rules distinct from both Python and .NET rules.

---

### User Story 2 - Agent-Specific Configuration Files (Priority: P2)

As a developer using a specific AI coding agent (e.g., Cursor, Claude, Copilot), I want SpecForge to generate configuration files in the format my agent understands, so I can immediately benefit from SpecForge governance without manual file conversion.

**Why this priority**: Different AI agents read configuration from different file paths and formats. Without agent plugins, users must manually create or convert configuration files for their chosen agent — a tedious and error-prone process that undermines adoption.

**Independent Test**: Can be fully tested by running `specforge init --agent cursor` and verifying that `.cursorrules` is created with SpecForge governance content and slash command definitions appropriate for Cursor.

**Acceptance Scenarios**:

1. **Given** a new project directory, **When** a user runs `specforge init --agent claude`, **Then** a `CLAUDE.md` file is generated containing SpecForge governance rules and slash command definitions appropriate for Claude.
2. **Given** a new project directory, **When** a user runs `specforge init --agent copilot`, **Then** `.github/copilot-instructions.md` is generated AND `.github/prompts/` directory is populated with prompt files in the format Copilot expects.
3. **Given** a new project directory, **When** a user runs `specforge init --agent cursor`, **Then** `.cursorrules` is generated with SpecForge governance content.
4. **Given** a new project directory, **When** a user runs `specforge init --agent gemini`, **Then** `.gemini/` directory is created and populated with Gemini-compatible configuration.
5. **Given** a new project directory, **When** a user runs `specforge init --agent windsurf`, **Then** `.windsurfrules` is generated with SpecForge governance content.
6. **Given** a new project directory, **When** a user runs `specforge init --agent codex`, **Then** codex-compatible configuration files are generated.

---

### User Story 3 - Combined Stack and Agent Initialization (Priority: P2)

As a developer, I want to specify both my stack and agent in a single init command, so that SpecForge generates a fully tailored project setup combining stack-specific prompt content with agent-specific file formats.

**Why this priority**: This is the natural usage pattern — developers have both a stack and an agent. The combined flow must work seamlessly without conflicts between the two plugin types.

**Independent Test**: Can be fully tested by running `specforge init --stack python --agent cursor --arch microservice` and verifying both `.cursorrules` (agent config) and `backend.prompts.md` (stack-specific content) are generated correctly and consistently.

**Acceptance Scenarios**:

1. **Given** a new project directory, **When** a user runs `specforge init --stack python --agent cursor --arch microservice`, **Then** both `.cursorrules` and stack-specific prompt files are generated, with prompt content reflecting Python microservice patterns.
2. **Given** a new project directory with auto-detectable stack markers, **When** a user runs `specforge init --agent claude` (no explicit stack), **Then** the stack is auto-detected and the appropriate stack plugin is loaded alongside the Claude agent plugin.

---

### User Story 4 - Plugin Discovery and Registration (Priority: P2)

As a developer, I want the system to automatically discover and register all built-in plugins at startup, so that all supported stacks and agents are available without manual configuration.

**Why this priority**: Plugin discovery is the foundation that enables all other user stories. If plugins cannot be found and loaded reliably, no stack or agent customization can occur.

**Independent Test**: Can be fully tested by verifying that after installation, all 3 built-in stack plugins and all 25+ built-in agent plugins are discoverable and loadable without any user configuration.

**Acceptance Scenarios**:

1. **Given** SpecForge is installed, **When** the system starts up, **Then** all v1 built-in stack plugins (dotnet, nodejs, python) are discovered and registered.
2. **Given** SpecForge is installed, **When** the system starts up, **Then** all built-in agent plugins (25+ agents including Generic fallback) are discovered and registered.
3. **Given** an unknown stack name is provided, **When** a user runs `specforge init --stack unknown`, **Then** a clear error message lists all available stack plugins.

---

### User Story 5 - Custom Stack Plugin (Priority: P3)

As a team with a proprietary or niche framework, I want to create a custom stack plugin that SpecForge can discover and use, so I can generate prompt files tailored to our internal technology stack.

**Why this priority**: While built-in plugins cover the most common stacks, extensibility is essential for enterprise adoption and niche technology communities. This is lower priority because most users will be served by built-in plugins first.

**Independent Test**: Can be fully tested by creating a Python module implementing the stack plugin interface, placing it in the designated plugin directory, and verifying `specforge init --stack custom_stack` loads and uses it.

**Acceptance Scenarios**:

1. **Given** a custom stack plugin file implementing the required interface and placed in the project's plugin directory, **When** a user runs `specforge init --stack custom_stack`, **Then** the system discovers and loads the custom plugin, generating prompt files using its rules.
2. **Given** a custom stack plugin with an invalid or incomplete interface, **When** the system attempts to load it, **Then** a descriptive error message identifies which required methods are missing.
3. **Given** both a built-in and custom plugin with the same name, **When** the system loads plugins, **Then** the custom plugin takes precedence over the built-in one, and a warning is displayed.

---

### User Story 6 - Architecture-Dependent Build and Structure Guidance (Priority: P3)

As a developer, I want stack plugins to provide not only prompt rules but also build command guidance and folder structure recommendations that vary by architecture, so that my project setup reflects real-world practices for my stack-architecture combination.

**Why this priority**: Build commands and folder structures are secondary to prompt content but add significant value for project scaffolding. They make the init output more complete and actionable.

**Independent Test**: Can be fully tested by running `specforge init --stack dotnet --arch microservice` and verifying the output includes microservice-appropriate build commands (multi-stage container build) and folder structure (per-service directories), distinct from monolith output.

**Acceptance Scenarios**:

1. **Given** a stack plugin for .NET and a microservice architecture, **When** prompt files are generated, **Then** build guidance includes multi-stage container build with publish commands, and folder structure shows per-service directories.
2. **Given** a stack plugin for .NET and a monolithic architecture, **When** prompt files are generated, **Then** build guidance includes standard build commands without container orchestration, and folder structure shows a single application directory with module sub-directories.

---

### Edge Cases

- What happens when a user specifies `--stack agnostic`? The system should generate generic prompt files without stack-specific rules, using only architecture-level and governance-domain-level guidance.
- What happens when a custom plugin directory does not exist? The system should silently skip custom plugin discovery and proceed with built-in plugins only.
- What happens when a custom plugin raises an exception during loading? The system should catch the error, log a warning with the plugin file path and error details, and continue loading remaining plugins.
- What happens when `--arch` is not provided? The system should default to the project's existing architecture (from manifest) or fall back to "monolithic" if no architecture is configured.
- What happens when a stack plugin does not support container configuration (e.g., Go monolith)? The plugin returns no container configuration for that architecture, and the system omits container-related guidance from generated files.
- What happens when multiple stack markers are detected (e.g., both `pyproject.toml` and `package.json` exist)? The existing stack detection priority order is respected, and the first match wins. An explicit `--stack` flag always overrides detection.
- What happens when `specforge init` is re-run and agent config files already exist? The system should overwrite existing agent config files with a Rich warning indicating which files were replaced. Governance prompt files already handle this via checksum-based change detection.

## Requirements *(mandatory)*

### Functional Requirements

#### Plugin Interface & Registration

- **FR-001**: System MUST define a stack plugin interface with methods for retrieving prompt rules, build commands, container configuration, test commands, and folder structure — each parameterized by architecture type.
- **FR-002**: System MUST define an agent plugin interface with methods for generating agent-specific configuration files and reporting which config files it produces.
- **FR-003**: System MUST automatically discover and register all built-in stack plugins when plugin functionality is invoked (e.g., during `specforge init` or `specforge plugins list`) without user configuration. In v1, built-in stack plugins are: .NET, Node.js, Python. Go and Java are deferred to v2.
- **FR-004**: System MUST automatically discover and register all built-in agent plugins when plugin functionality is invoked without user configuration. v1 ships support for all 25+ agents: Claude Code, GitHub Copilot, Cursor, Gemini CLI, Windsurf, Codex CLI, Kiro CLI, Amp, Auggie CLI, CodeBuddy CLI, IBM Bob, Jules, Kilo Code, opencode, Pi Coding Agent, Qoder CLI, Qwen Code, Roo Code, SHAI (OVHcloud), Tabnine CLI, Mistral Vibe, Kimi Code, Antigravity (agy), Trae, and a Generic fallback for unsupported agents.
- **FR-005**: System MUST support loading custom stack plugins from a designated project-level plugin directory.
- **FR-006**: System MUST give custom plugins precedence over built-in plugins when names conflict, displaying a warning to the user.

#### Stack Plugins — Architecture-Aware Content

- **FR-007**: Each stack plugin MUST return rule overrides (not full rule sets) based on the provided architecture type (monolithic, microservice, modular-monolith). Overrides are layered on top of base governance rules; cross-cutting domains (security, testing, architecture) are inherited from defaults. Stack plugins provide overrides for at minimum the `backend` domain; they SHOULD also provide overrides for `database` and `cicd` domains where the stack×architecture combination has distinct patterns (e.g., per-service migrations for microservice, single pipeline for monolith).
- **FR-008**: The .NET stack plugin MUST generate microservice-specific rules including per-service application patterns, multi-stage container build guidance with publish commands, inter-service communication via protocol buffer compilation, event handler patterns using message transport, and per-service data context isolation.
- **FR-009**: The .NET stack plugin MUST generate monolith-specific rules including single data context with module-scoped schemas, intra-module communication via mediator pattern, and must NOT include container orchestration, protocol buffers, or event bus rules.
- **FR-010**: The Python stack plugin MUST generate microservice-specific rules including per-service web framework patterns, container build with slim base images, event-driven task processing, and per-service data model isolation.
- **FR-011**: The Python stack plugin MUST generate monolith-specific rules including single-application patterns, shared data models, synchronous internal communication, and must NOT include container orchestration or event bus rules.
- **FR-012**: The Node.js stack plugin MUST generate microservice-specific rules including per-service web framework patterns, container build with Alpine-based images, message queue event handlers, and per-service schema isolation.
- **FR-012a**: The Node.js stack plugin MUST generate monolith-specific rules including single-application patterns, shared schema configuration, synchronous internal communication, and must NOT include container orchestration or message queue event bus rules.
- **FR-012b**: Each stack plugin (.NET, Node.js, Python) MUST generate modular-monolith rules that extend monolith-specific rules with strict module boundary enforcement and interface contract requirements. Modular-monolith rules inherit all monolith base rules and add boundary enforcement; they must NOT include microservice-specific patterns (containers, event bus, per-service schemas).
- **FR-013**: The Go stack plugin MUST generate architecture-aware rules following the same microservice vs. monolith content differentiation pattern. *(Deferred to v2)*
- **FR-014**: The Java stack plugin MUST generate architecture-aware rules following the same microservice vs. monolith content differentiation pattern. *(Deferred to v2)*

#### Agent Plugins — Config File Generation

- **FR-015**: Each agent plugin MUST generate configuration files in the correct location and format for that agent. The `AgentPlugin.generate_config(target_dir, context)` method receives a context dict containing: `project_name` (str), `stack` (str), `architecture` (str), and `governance_summary` (str — concatenated governance rules from all generated `.prompts.md` files). Concrete implementations produce agent-specific output (e.g., Claude → `CLAUDE.md`, Copilot → `.github/copilot-instructions.md` + `.github/prompts/`, Cursor → `.cursorrules`, Gemini → `.gemini/`, Windsurf → `.windsurfrules`, Codex → `AGENTS.md`, Kiro → `.kiro/rules.md`, Roo Code → `.roo/rules.md`, Antigravity → `.agy/rules.md`, Trae → `.trae/rules.md`; remaining single-file agents write `<AGENT_NAME>.md` at project root). Full agent-to-path mapping is documented in research.md R-07.
- **FR-016**: The system MUST include a Generic agent plugin that serves as a fallback for unsupported agents, accepting a user-specified config output directory.
- **FR-017**: All 25+ agent plugins MUST implement the same `AgentPlugin` interface and be discoverable through the same registry mechanism as stack plugins.

#### Integration & Error Handling

- **FR-018**: The `specforge init` command MUST accept combined `--stack`, `--agent`, and `--arch` flags and coordinate both plugin types during initialization.
- **FR-019**: System MUST fall back to "agnostic" behavior (generic prompt content, no agent-specific files) when no stack or agent is specified and none can be auto-detected.
- **FR-020**: System MUST validate that the provided `--stack` value matches a registered stack plugin and display available plugins on mismatch.
- **FR-021**: System MUST validate that the provided `--agent` value matches a registered agent plugin and display available plugins on mismatch.
- **FR-022**: System MUST catch and report errors from custom plugin loading without crashing, logging the plugin file path and error details.
- **FR-023**: System MUST default architecture to "monolithic" when `--arch` is not provided and no existing project architecture is configured.
- **FR-024**: The plugin registry MUST feed stack plugin rule overrides into PromptFileManager, which appends formatted rules to governance files after template rendering and before checksum computation. PromptContextBuilder (Feature 003) reads the merged governance files unchanged and handles context assembly using the established governance precedence order. Plugins MUST NOT perform context assembly directly.

#### Plugin Metadata & Inspection

- **FR-025**: Each plugin MUST expose metadata including its name, a human-readable description, and the list of architecture types it supports.
- **FR-026**: System MUST provide a way for users to list all available plugins and their supported architectures (e.g., via a `specforge plugins list` command or similar mechanism).
- **FR-027**: Plugin rules MUST NOT be versioned in v1. Rules evolve with SpecForge releases; stack-version differentiation (e.g., .NET 8 vs .NET 9) is deferred.

### Key Entities

- **Stack Plugin**: A component responsible for generating stack-specific prompt rules, build commands, container configuration, test commands, and folder structure — all parameterized by architecture type. Attributes: name, description, supported architectures.
- **Agent Plugin**: A component responsible for generating agent-specific configuration files. Attributes: name, description, list of config files produced.
- **Plugin Manager**: The central orchestrator that discovers, validates, registers, and provides access to all available stack and agent plugins. Provides lookup by name, listing, and conflict resolution (custom overrides built-in). Implemented as `PluginManager` class.
- **Architecture Type**: An enumeration of supported architecture patterns (monolithic, microservice, modular-monolith) that parameterizes stack plugin behavior.
- **Plugin Rule**: A frozen dataclass representing a single governance rule override from a stack plugin. Contains: rule_id, title, severity, scope, description, thresholds, example_correct, example_incorrect. Grouped by governance domain in the dict returned by `StackPlugin.get_prompt_rules()`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running initialization with any v1 supported stack-architecture combination produces prompt files with content specific to that exact combination — verified by content assertions for 3 stacks × 3 architectures (9 combinations in v1).
- **SC-002**: Running initialization with any of the 25+ supported agents produces correctly located and formatted configuration files specific to that agent — verified by file existence and content structure checks.
- **SC-003**: A developer can create and use a custom stack plugin in under 15 minutes by following the plugin authoring documentation and implementing the required interface.
- **SC-004**: 100% of built-in plugins are discovered and registered automatically — no manual configuration needed after installation.
- **SC-005**: Invalid or broken custom plugins do not crash the system — the error is reported and all other plugins continue to function.
- **SC-006**: Generated prompt files for microservice architectures contain zero rules that apply only to monolithic architectures, and vice versa — verified by content analysis of generated files.

## Assumptions

- The existing `ArchitectureType` literal type (`"monolithic"`, `"microservice"`, `"modular-monolith"`) is sufficient and does not need extension for this feature.
- The existing `GOVERNANCE_DOMAINS` list (architecture, backend, frontend, database, security, testing, cicd) covers all domains needed for stack plugin rule generation.
- The existing `AgentPlugin` base class in `plugins/agents/base.py` provides the correct interface for agent plugins and does not need redesign — only concrete implementations are needed.
- Custom plugin discovery uses a well-known project-level directory path (e.g., `plugins/stacks/`, `plugins/agents/`) rather than a registry-based or entry-point-based mechanism.
- Go and Java stack plugins will follow the same architecture in v2 using the same `StackPlugin` interface validated by v1.
- The `--arch` flag on the init command reuses the existing `VALID_ARCHITECTURES` validation.
- Stack plugins produce rule overrides only; base governance rules provide the foundation. The existing PromptContextBuilder (Feature 003) handles merging using the governance precedence order.
- No plugin rule versioning in v1; framework version differentiation (e.g., .NET 8 vs .NET 9) is deferred until demand materializes.
