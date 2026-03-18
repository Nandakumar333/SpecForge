# Tasks: Plugin System for Multi-Agent and Multi-Stack Support

**Input**: Design documents from `/specs/013-plugin-system/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/plugin-interfaces.md, quickstart.md
**Tests**: TDD — test files created BEFORE implementation files (per constitution IV and user directive)
**Organization**: Tasks grouped by user story. DotnetPlugin is reference implementation (most detailed). Other plugins follow same pattern with [P] markers.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/specforge/` (existing project structure)
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/snapshots/`
- **Templates**: `src/specforge/templates/base/agents/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package structure and configuration constants for the plugin system

- [ ] T001 Add plugin system constants to `src/specforge/core/config.py`: `CUSTOM_PLUGIN_DIR` (`.specforge/plugins`), `PLUGIN_NAME_PATTERN` regex, valid severity values `PLUGIN_SEVERITIES`, and `ARCHITECTURE_DEFAULT` (`"monolithic"`)
- [ ] T002 [P] Create `src/specforge/plugins/stacks/__init__.py` package init (empty, enables module scanning)
- [ ] T003 [P] Create `src/specforge/templates/base/agents/` directory for agent config Jinja2 templates

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models, abstract base classes, PluginManager core, and PromptFileManager integration — MUST complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Models (TDD)

- [ ] T004 Write unit tests for PluginRule frozen dataclass in `tests/unit/test_plugin_rule.py`: construction, immutability, field validation (rule_id pattern, severity values), equality, repr
- [ ] T005 Write unit tests for DockerConfig frozen dataclass in `tests/unit/test_plugin_rule.py`: construction, optional fields, None handling
- [ ] T006 Implement PluginRule and DockerConfig frozen dataclasses in `src/specforge/plugins/stack_plugin_base.py` — follow contracts/plugin-interfaces.md exactly

### StackPlugin ABC (TDD)

- [ ] T007 Write unit tests for StackPlugin ABC contract in `tests/unit/test_stack_plugin_base.py`: verify ABC cannot be instantiated, verify all abstract methods/properties are enforced, test a minimal concrete subclass that implements all methods, verify `get_prompt_rules()` returns `dict[str, list[PluginRule]]` keyed by governance domain names, verify `get_docker_config()` can return None
- [ ] T008 Implement StackPlugin ABC in `src/specforge/plugins/stack_plugin_base.py` — abstract properties: `plugin_name`, `description`, `supported_architectures`; abstract methods: `get_prompt_rules(arch)`, `get_build_commands(arch)`, `get_docker_config(arch)`, `get_test_commands()`, `get_folder_structure(arch)` per contracts/plugin-interfaces.md

### PluginManager (TDD)

- [ ] T009 Write unit tests for PluginManager in `tests/unit/test_plugin_manager.py`: test `discover()` finds built-in stack and agent plugins, test `get_stack_plugin("dotnet")` returns Ok with correct plugin, test `get_stack_plugin("unknown")` returns Err with available plugin names, test `get_agent_plugin("claude")` returns Ok, test `list_stack_plugins()` returns all registered plugins, test `list_agent_plugins()` returns all registered plugins, test discovery with mock plugin directories using `tmp_path`
- [ ] T010 Implement PluginManager in `src/specforge/plugins/plugin_manager.py`: constructor takes `project_root: Path | None`, `discover()` scans `specforge.plugins.stacks` and `specforge.plugins.agents` packages via `importlib`, registers StackPlugin and AgentPlugin subclasses by name, `get_stack_plugin(name)` and `get_agent_plugin(name)` return `Result[T, str]`, `list_stack_plugins()` and `list_agent_plugins()` return sorted lists
- [ ] T011 Update `src/specforge/plugins/__init__.py` to re-export PluginManager, StackPlugin, PluginRule, DockerConfig for convenient imports

### Rule Formatting Utility (TDD)

- [ ] T012 Write unit tests for PluginRule → markdown formatting in `tests/unit/test_rule_formatter.py`: test single rule formats to correct `### RULE-ID: Title` block with severity, scope, rule, threshold, example_correct, example_incorrect fields; test multiple rules concatenated; test empty thresholds dict; test multiline examples
- [ ] T013 Implement rule formatting via Jinja2 template: create `src/specforge/templates/base/governance/plugin_rule_block.md.j2` template that renders a list of PluginRule objects into governance-compatible `### RULE-ID: Title` markdown blocks. Implement `format_plugin_rules(rules: list[PluginRule]) -> str` in `src/specforge/plugins/rule_formatter.py` that renders the template via TemplateRenderer (constitution II compliance: no string concatenation for file content)

### PromptFileManager Integration (TDD)

- [ ] T014 Write unit tests for PromptFileManager plugin rule integration in `tests/unit/test_prompt_manager_plugin_rules.py`: test `generate_one()` with `extra_rules=None` produces identical output to current behavior, test `generate_one()` with `extra_rules=[PluginRule(...)]` appends formatted rules after base template rules, test checksum is recomputed over merged content, test `generate()` with `extra_rules_by_domain={"backend": [...]}` passes rules to correct domain only
- [ ] T015 Modify `src/specforge/core/prompt_manager.py`: add optional `extra_rules: list[PluginRule] | None = None` parameter to `generate_one()`, append formatted rules after template rendering but before checksum computation; add optional `extra_rules_by_domain: dict[str, list[PluginRule]] | None = None` parameter to `generate()`, pass domain-specific rules to each `generate_one()` call

**Checkpoint**: Foundation ready — StackPlugin ABC, PluginManager, PluginRule, rule formatting, and PromptFileManager integration all functional. User story implementation can begin.

---

## Phase 3: User Story 1 — Stack-Aware Prompt Generation (Priority: P1) 🎯 MVP

**Goal**: Generate governance prompt files with architecture-specific rule content tailored to the developer's technology stack. Running `specforge init --stack dotnet --arch microservice` produces `.specforge/prompts/backend.dotnet.prompts.md` with .NET microservice-specific rules appended after base template rules.

**Independent Test**: Run `specforge init --stack python --arch microservice` in a temp dir and assert `backend.python.prompts.md` contains Python microservice rules (e.g., "FastAPI", "per-service", "container") and does NOT contain .NET or Node.js rules.

### DotnetPlugin — Reference Implementation (TDD, most detailed)

- [ ] T016 Write comprehensive unit tests for DotnetPlugin in `tests/unit/test_dotnet_plugin.py`: test `plugin_name` returns `"dotnet"`, test `supported_architectures` includes all 3 types, test `get_prompt_rules("microservice")` returns rules in `"backend"` domain containing per-service application patterns + multi-stage container build + gRPC proto compilation + MassTransit event handlers + per-service DbContext, test `get_prompt_rules("monolithic")` returns rules in `"backend"` domain containing single DbContext + MediatR module communication + NO container/gRPC/event bus rules, test `get_prompt_rules("modular-monolith")` returns monolith rules PLUS strict module boundary enforcement + interface contracts, test rules are in `"database"` and `"cicd"` domains too, test each rule has valid PluginRule fields (non-empty rule_id/title/severity/scope/description, correct severity values)
- [ ] T017 Implement DotnetPlugin in `src/specforge/plugins/stacks/dotnet_plugin.py`: concrete StackPlugin subclass. Rule data MUST be extracted to a separate data module `src/specforge/plugins/stacks/dotnet_rules.py` to keep the plugin class under 200 lines (constitution III). The rules module defines `BASE_RULES`, `MICROSERVICE_RULES`, `MONOLITH_RULES`, `MODULAR_MONOLITH_RULES` as lists of PluginRule keyed by domain. Plugin class delegates: `_base_dotnet_rules()` loads from data module, `_microservice_rules()` for per-service patterns/container build/gRPC/MassTransit/per-service DbContext, `_monolith_rules()` for single DbContext/MediatR/no containers, `_modular_monolith_rules()` extending monolith with boundary enforcement. Return rules keyed by domain (`backend`, `database`, `cicd`). `get_docker_config("microservice")` returns DockerConfig with `mcr.microsoft.com/dotnet/sdk` and `mcr.microsoft.com/dotnet/aspnet` stages. `get_docker_config("monolithic")` returns None. `get_test_commands()` returns `["dotnet test"]`. `get_build_commands(arch)` varies by architecture.

### PythonPlugin (TDD, follows DotnetPlugin pattern)

- [ ] T018 [P] [US1] Write unit tests for PythonPlugin in `tests/unit/test_python_plugin.py`: test `plugin_name` returns `"python"`, test microservice rules contain FastAPI per-service + Docker python:slim + Celery/Dramatiq events + SQLAlchemy per-service models, test monolith rules contain single-app + shared models + synchronous communication + NO container/event bus rules, test modular-monolith adds boundary enforcement, test rules span `backend`/`database`/`cicd` domains, test all rules have valid PluginRule fields
- [ ] T019 [P] [US1] Implement PythonPlugin in `src/specforge/plugins/stacks/python_plugin.py` with rule data in `src/specforge/plugins/stacks/python_rules.py` (200-line class limit compliance): concrete StackPlugin subclass following DotnetPlugin pattern. Python-specific: FastAPI, SQLAlchemy, Celery, Docker python:slim, pytest. `get_docker_config("microservice")` returns DockerConfig with `python:3.11-slim`. `get_test_commands()` returns `["pytest"]`.

### NodejsPlugin (TDD, follows DotnetPlugin pattern)

- [ ] T020 [P] [US1] Write unit tests for NodejsPlugin in `tests/unit/test_nodejs_plugin.py`: test `plugin_name` returns `"nodejs"`, test microservice rules contain Express/Fastify per-service + Docker node:alpine + NATS/RabbitMQ event handlers + Prisma/TypeORM per-service schema, test monolith rules contain single-app + shared schema + NO container/event bus rules, test modular-monolith adds boundary enforcement, test rules span `backend`/`database`/`cicd` domains, test all rules have valid PluginRule fields
- [ ] T021 [P] [US1] Implement NodejsPlugin in `src/specforge/plugins/stacks/nodejs_plugin.py` with rule data in `src/specforge/plugins/stacks/nodejs_rules.py` (200-line class limit compliance): concrete StackPlugin subclass following DotnetPlugin pattern. Node.js-specific: Express/Fastify, Prisma/TypeORM, NATS, Docker node:alpine. `get_docker_config("microservice")` returns DockerConfig with `node:20-alpine`. `get_test_commands()` returns `["npm test"]`.

### Snapshot Tests

- [ ] T022 [US1] Create snapshot tests for all 9 stack×arch combinations in `tests/snapshots/test_stack_plugin_snapshots.py`: for each of (dotnet, python, nodejs) × (microservice, monolithic, modular-monolith), call `plugin.get_prompt_rules(arch)`, format rules via `format_plugin_rules()`, and snapshot the output using syrupy. Assert microservice snapshots contain container/event patterns, monolith snapshots do NOT.

**Checkpoint**: At this point, US1 is fully functional. Running `PluginManager().discover()` → `get_stack_plugin("dotnet")` → `get_prompt_rules("microservice")` returns architecture-specific .NET rules. PromptFileManager can merge these into governance files.

---

## Phase 4: User Story 2 — Agent-Specific Configuration Files (Priority: P2)

**Goal**: Generate agent-specific configuration files (CLAUDE.md, .cursorrules, .github/copilot-instructions.md, etc.) that contain SpecForge governance content in the format each AI coding agent expects.

**Independent Test**: Run agent plugin `generate_config()` in a temp dir and assert the correct file(s) exist at the expected path with non-empty governance content.

### Agent Plugin Base Classes (TDD)

- [ ] T023 [US2] Write unit tests for SingleFileAgentPlugin and DirectoryAgentPlugin in `tests/unit/test_agent_plugin_bases.py`: test SingleFileAgentPlugin generates one file at the configured path, test DirectoryAgentPlugin creates directory and writes multiple files, test both call Jinja2 template rendering with governance context, test `config_files()` returns correct paths
- [ ] T024 [US2] Implement SingleFileAgentPlugin in `src/specforge/plugins/agents/single_file_base.py`: subclass of AgentPlugin that takes `file_path` and `template_name` config, renders template via TemplateRenderer, writes to `target_dir / file_path`. Implement DirectoryAgentPlugin in `src/specforge/plugins/agents/directory_base.py`: subclass that takes `dir_path` and `file_specs` config, creates directory, renders multiple templates.

### Agent Jinja2 Templates

- [ ] T025 [P] [US2] Create Jinja2 templates for agent config files in `src/specforge/templates/base/agents/`: `cursor.rules.j2` (plain text rules format), `claude.md.j2` (markdown with slash commands), `copilot-instructions.md.j2` (Copilot instructions format), `copilot-prompt.md.j2` (individual prompt file), `gemini-style-guide.md.j2`, `windsurf.rules.j2`, `codex.md.j2`, `kiro-rules.md.j2`, `generic.md.j2` (fallback template). Each template receives context: `project_name`, `stack`, `architecture`, `governance_summary`.

### Reference Agent Implementations (TDD)

- [ ] T026 [US2] Write unit tests for CursorPlugin in `tests/unit/test_agent_plugins.py`: test `agent_name()` returns `"cursor"`, test `config_files()` returns `[".cursorrules"]`, test `generate_config()` writes `.cursorrules` in target dir with governance content
- [ ] T027 [US2] Implement CursorPlugin in `src/specforge/plugins/agents/cursor_plugin.py`: SingleFileAgentPlugin subclass, `file_path=".cursorrules"`, `template_name="cursor.rules.j2"`
- [ ] T028 [US2] Write unit tests for CopilotPlugin in `tests/unit/test_agent_plugins.py`: test `agent_name()` returns `"copilot"`, test `config_files()` returns copilot paths, test `generate_config()` creates `.github/copilot-instructions.md` AND `.github/prompts/` directory with prompt files
- [ ] T029 [US2] Implement CopilotPlugin in `src/specforge/plugins/agents/copilot_plugin.py`: DirectoryAgentPlugin subclass, creates `.github/copilot-instructions.md` + `.github/prompts/*.md`
- [ ] T030 [US2] Write unit tests for ClaudePlugin in `tests/unit/test_agent_plugins.py`: test `agent_name()` returns `"claude"`, test `config_files()` returns `["CLAUDE.md"]`, test `generate_config()` writes `CLAUDE.md` with slash commands
- [ ] T031 [US2] Implement ClaudePlugin in `src/specforge/plugins/agents/claude_plugin.py`: SingleFileAgentPlugin subclass, `file_path="CLAUDE.md"`, `template_name="claude.md.j2"`

### Remaining Agent Plugins (parallel batch — follow SingleFile/Directory pattern)

- [ ] T032 [P] [US2] Implement GeminiPlugin in `src/specforge/plugins/agents/gemini_plugin.py`: DirectoryAgentPlugin subclass, creates `.gemini/` directory with style guide
- [ ] T033 [P] [US2] Implement WindsurfPlugin in `src/specforge/plugins/agents/windsurf_plugin.py`: SingleFileAgentPlugin, `.windsurfrules`
- [ ] T034 [P] [US2] Implement CodexPlugin in `src/specforge/plugins/agents/codex_plugin.py`: SingleFileAgentPlugin, `AGENTS.md`
- [ ] T035 [P] [US2] Implement KiroPlugin in `src/specforge/plugins/agents/kiro_plugin.py`: DirectoryAgentPlugin, `.kiro/rules.md`
- [ ] T036 [US2] Write parametrized unit test in `tests/unit/test_agent_plugins.py` that iterates ALL 25+ agent plugins, verifies each: has non-empty `agent_name()`, has non-empty `config_files()`, `generate_config()` in a `tmp_path` produces files at expected paths with non-empty content. This test MUST be written before T037 (TDD compliance — constitution IV).
- [ ] T037 [P] [US2] Implement batch of single-file agent plugins — each is a SingleFileAgentPlugin subclass with agent-specific file path: `src/specforge/plugins/agents/amp_plugin.py` (AMP.md), `auggie_plugin.py` (AUGGIE.md), `codebuddy_plugin.py` (CODEBUDDY.md), `bob_plugin.py` (.bob/rules.md), `jules_plugin.py` (JULES.md), `kilocode_plugin.py` (.kilocode), `opencode_plugin.py` (OPENCODE.md), `pi_plugin.py` (PI.md), `qoder_plugin.py` (QODER.md), `qwen_plugin.py` (QWEN.md), `roocode_plugin.py` (.roo/rules.md), `shai_plugin.py` (SHAI.md), `tabnine_plugin.py` (TABNINE.md), `mistral_plugin.py` (MISTRAL.md), `kimi_plugin.py` (KIMI.md), `antigravity_plugin.py` (.agy/rules.md), `trae_plugin.py` (.trae/rules.md)
- [ ] T038 [US2] Write unit tests for GenericPlugin in `tests/unit/test_generic_plugin.py`: test `agent_name()` returns `"generic"`, test `generate_config()` writes to user-specified directory, test fallback behavior when no directory is specified
- [ ] T039 [US2] Implement GenericPlugin in `src/specforge/plugins/agents/generic_plugin.py`: direct AgentPlugin subclass that accepts `commands_dir` parameter and writes governance content to specified directory

**Checkpoint**: All 25+ agent plugins produce correctly located configuration files. Each agent's config contains SpecForge governance content in the format that agent expects.

---

## Phase 5: User Story 3 — Combined Stack and Agent Initialization (Priority: P2)

**Goal**: `specforge init --stack python --agent cursor --arch microservice` produces BOTH `.cursorrules` (agent config) AND `backend.python.prompts.md` with Python microservice rules — in a single command.

**Independent Test**: Run full `specforge init` with combined flags in a temp dir and assert both agent config files and architecture-specific governance files exist.

- [ ] T040 [US3] Write integration tests for init with plugins in `tests/integration/test_init_with_plugins.py`: test `specforge init --stack python --agent cursor --arch microservice` produces `.cursorrules` AND `backend.python.prompts.md` with microservice rules, test `specforge init --stack dotnet --agent copilot --arch monolithic` produces `.github/copilot-instructions.md` AND `backend.dotnet.prompts.md` with monolith rules, test `specforge init --agent claude` (no explicit stack) auto-detects stack and loads both plugins, test `specforge init` with no flags falls back to agnostic behavior
- [ ] T041 [US3] Modify `src/specforge/cli/init_cmd.py` to integrate PluginManager: after existing detection and scaffold steps, instantiate PluginManager, call `discover()`, retrieve stack plugin via `get_stack_plugin(resolved_stack)`, call `get_prompt_rules(architecture)` to get extra rules, pass `extra_rules_by_domain` to `PromptFileManager.generate()`, retrieve agent plugin via `get_agent_plugin(detection.agent)`, call `generate_config(target_dir, context)` to write agent config files. Add `--arch` Click option using `VALID_ARCHITECTURES` choices with default `"monolithic"`.
- [ ] T042 [US3] Add architecture to `src/specforge/core/project.py` ProjectConfig: add `architecture: str = "monolithic"` field, update `create()` factory method to accept and validate architecture parameter
- [ ] T043 [US3] Update scaffold summary output in `src/specforge/cli/init_cmd.py` to display: detected/explicit stack plugin name, detected/explicit agent plugin name, architecture type, list of agent config files written

**Checkpoint**: Combined `--stack + --agent + --arch` flow works end-to-end. Users get both stack-tailored governance files and agent-specific config files from a single init command.

---

## Phase 6: User Story 4 — Plugin Discovery and Registration (Priority: P2)

**Goal**: All built-in plugins auto-discovered at startup. Users can list available plugins and get helpful error messages for unknown plugin names.

**Independent Test**: Call `PluginManager.discover()` and verify all 3 stack plugins + 25+ agent plugins are registered. Run `specforge init --stack unknown` and verify error message lists available stacks.

- [ ] T044 [US4] Write integration test for full discovery in `tests/integration/test_plugin_discovery.py`: test `discover()` registers exactly 3 stack plugins (dotnet, nodejs, python) and 25+ agent plugins, test each registered plugin has non-empty `plugin_name`/`agent_name` and description
- [ ] T045 [US4] Write unit tests for plugin validation error messages in `tests/unit/test_plugin_manager.py`: test `get_stack_plugin("unknown")` returns Err containing all available stack names, test `get_agent_plugin("unknown")` returns Err containing all available agent names
- [ ] T046 [US4] Implement `specforge plugins list` CLI command in `src/specforge/cli/plugins_cmd.py`: Click command group `plugins` with `list` subcommand that instantiates PluginManager, calls `discover()`, displays all stack plugins with name/description/supported architectures and all agent plugins with name/config files using Rich Table output
- [ ] T047 [US4] Register `plugins` command group in `src/specforge/cli/main.py` Click group

**Checkpoint**: `specforge plugins list` displays all available plugins. Unknown `--stack`/`--agent` values produce helpful error messages listing alternatives.

---

## Phase 7: User Story 5 — Custom Stack Plugin (Priority: P3)

**Goal**: Teams can create custom stack plugins in `.specforge/plugins/stacks/` that SpecForge discovers, validates, and uses alongside built-in plugins.

**Independent Test**: Create a `mock_plugin.py` implementing StackPlugin in a temp `.specforge/plugins/stacks/` directory, run discovery, and verify the custom plugin is registered and its rules are used.

- [ ] T048 [US5] Write integration tests for custom plugin loading in `tests/integration/test_custom_plugin_loading.py`: test discovery loads `*_plugin.py` from `.specforge/plugins/stacks/` via `importlib.util.spec_from_file_location()`, test custom plugin with valid interface is registered, test custom plugin with missing abstract methods logs warning and is skipped, test custom plugin that raises exception during import is caught and logged, test custom plugin with same name as built-in overrides it with Rich warning, test discovery with no `.specforge/plugins/` directory silently continues
- [ ] T049 [US5] Implement custom plugin discovery in `src/specforge/plugins/plugin_manager.py`: add `_discover_custom_stacks()` and `_discover_custom_agents()` methods that scan `.specforge/plugins/stacks/` and `.specforge/plugins/agents/` using `importlib.util.spec_from_file_location()`, validate interface compliance (check all abstract methods present), register with conflict resolution (custom overrides built-in + Rich console warning)
- [ ] T050 [US5] Write unit test for interface validation in `tests/unit/test_plugin_manager.py`: test `_validate_stack_plugin(cls)` returns Ok for valid subclass, returns Err with missing method names for incomplete subclass

**Checkpoint**: Custom plugins from project directory are discovered, validated, and registered. Invalid plugins produce helpful error messages without crashing.

---

## Phase 8: User Story 6 — Architecture-Dependent Build and Structure Guidance (Priority: P3)

**Goal**: Stack plugins provide build commands, Docker config, and folder structure that vary by architecture. This data is available for scaffold output and documentation.

**Independent Test**: Call `DotnetPlugin().get_build_commands("microservice")` and verify it includes multi-stage container build commands; call with `"monolithic"` and verify no container commands.

- [ ] T051 [P] [US6] Write unit tests for build commands and folder structure in `tests/unit/test_dotnet_plugin.py`: test `get_build_commands("microservice")` includes `dotnet publish` + Docker build commands, test `get_build_commands("monolithic")` includes `dotnet build`/`dotnet run` without Docker, test `get_folder_structure("microservice")` shows per-service directories, test `get_folder_structure("monolithic")` shows single project structure
- [ ] T052 [P] [US6] Write unit tests for build commands and folder structure in `tests/unit/test_python_plugin.py`: test microservice build includes Docker + pip/uv, test monolith build includes pip/uv without Docker, test folder structures differ by architecture
- [ ] T053 [P] [US6] Write unit tests for build commands and folder structure in `tests/unit/test_nodejs_plugin.py`: test microservice build includes Docker + npm, test monolith build includes npm without Docker, test folder structures differ by architecture
- [ ] T054 [US6] Verify all 3 stack plugins' `get_docker_config("microservice")` returns valid DockerConfig and `get_docker_config("monolithic")` returns None — add assertions to existing plugin tests if not already covered

**Checkpoint**: All stack plugins provide architecture-specific build, Docker, and folder structure guidance. Microservice configs include container tooling; monolith configs do not.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final quality checks across all user stories

- [ ] T055 [P] Run full test suite with `pytest --cov=specforge -q` and verify all tests pass with ≥90% coverage on new plugin modules
- [ ] T056 [P] Run `ruff check src/specforge/plugins/ tests/unit/test_plugin* tests/unit/test_agent* tests/unit/test_dotnet* tests/unit/test_python_plugin* tests/unit/test_nodejs* tests/integration/test_init_with* tests/integration/test_custom* tests/integration/test_plugin*` and fix any linting issues
- [ ] T057 Validate quickstart.md scenarios: execute the 3 example init commands from `specs/013-plugin-system/quickstart.md` in temp directories and verify expected output
- [ ] T058 Verify `src/specforge/plugins/__init__.py` exports clean public API: `PluginManager`, `StackPlugin`, `AgentPlugin`, `PluginRule`, `DockerConfig`
- [ ] T059 Run snapshot update `pytest --snapshot-update` for all 9 stack×arch rule snapshots and commit baseline snapshots

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — PluginManager + StackPlugin ABC + PromptFileManager integration must exist
- **US2 (Phase 4)**: Depends on Phase 2 — PluginManager + AgentPlugin ABC must exist. **Independent of US1** (different plugin type)
- **US3 (Phase 5)**: Depends on US1 + US2 — needs both stack and agent plugins working
- **US4 (Phase 6)**: Depends on US1 + US2 — needs all plugins registered to test full discovery
- **US5 (Phase 7)**: Depends on Phase 2 — needs PluginManager discovery infrastructure
- **US6 (Phase 8)**: Depends on US1 — extends stack plugins with build/docker/folder methods
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — No dependencies on other stories. **This is the MVP.**
- **US2 (P2)**: Can start after Phase 2 — **Independent of US1**, can run in parallel
- **US3 (P2)**: Depends on both US1 and US2 completing (integration of both plugin types)
- **US4 (P2)**: Depends on US1 and US2 for full discovery validation; `plugins list` command independent
- **US5 (P3)**: Can start after Phase 2 — **Independent of US1/US2** (custom loading is infrastructure-level)
- **US6 (P3)**: Depends on US1 (extends stack plugin methods already implemented)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD per constitution IV)
- Data models before services
- Base classes before concrete implementations
- Reference implementation (DotnetPlugin / CursorPlugin) before parallel batch
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 2 internal**: T004+T005 (data model tests) can run in parallel
**Phase 3 (US1)**: T018+T019 (PythonPlugin) and T020+T021 (NodejsPlugin) can run in parallel after DotnetPlugin reference is complete
**Phase 4 (US2)**: T032–T036 (remaining agent plugins) can ALL run in parallel after reference agents are done
**Cross-story**: US1 and US2 can run in parallel after Phase 2 completes — they are independent plugin types
**Cross-story**: US5 can run in parallel with US1/US2 after Phase 2 completes

---

## Parallel Example: Phase 3 (US1)

```text
# After DotnetPlugin reference (T016-T017) is complete:

# Launch PythonPlugin and NodejsPlugin in parallel:
Worker A: T018 → T019 (PythonPlugin tests → implementation)
Worker B: T020 → T021 (NodejsPlugin tests → implementation)

# Then snapshot tests:
Both: T022 (snapshot all 9 combinations)
```

## Parallel Example: Phase 4 (US2)

```text
# After reference agents (T026-T031) are complete:

# Launch remaining reference agents in parallel:
Worker A: T032 (GeminiPlugin)
Worker B: T033 (WindsurfPlugin)
Worker C: T034 (CodexPlugin)
Worker D: T035 (KiroPlugin)

# Then TDD: parametrized test before batch:
T036 (parametrized test for all 25+ agents — TDD first)
T037 (batch of 17 single-file agents)

# Then Generic:
T038-T039 (GenericPlugin test + implementation)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T015) — **CRITICAL: blocks all stories**
3. Complete Phase 3: User Story 1 — DotnetPlugin first (T016–T017), then Python + Node.js in parallel (T018–T021), then snapshots (T022)
4. **STOP and VALIDATE**: Test US1 independently — `PluginManager().discover()` + `get_stack_plugin("dotnet").get_prompt_rules("microservice")` returns correct architecture-specific rules
5. Deploy/demo if ready — the core plugin system works

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. Add US1 → Test independently → **MVP: architecture-aware prompt generation works**
3. Add US2 → Test independently → Agent config files generated
4. Add US3 → Test independently → Combined init flow works end-to-end
5. Add US4 → Test independently → `specforge plugins list` available
6. Add US5 → Test independently → Custom plugins loadable
7. Add US6 → Test independently → Build/Docker/folder guidance complete
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Phase 2 completes:

- **Developer A**: US1 (stack plugins — DotnetPlugin reference first)
- **Developer B**: US2 (agent plugins — CursorPlugin reference first)
- **Developer C**: US5 (custom plugin loading — infrastructure-level, independent)

After US1 + US2 complete:
- **Developer A**: US3 (init_cmd.py integration)
- **Developer B**: US4 (plugins list command)
- **Developer C**: US6 (build/docker/folder guidance)

---

## Notes

- [P] tasks = different files, no dependencies on in-progress tasks
- [Story] label maps task to specific user story for traceability
- DotnetPlugin (T016–T017) is the REFERENCE IMPLEMENTATION — implement it first with maximum detail, then PythonPlugin and NodejsPlugin follow the same pattern
- CursorPlugin (T026–T027) is the REFERENCE AGENT IMPLEMENTATION — simplest single-file agent; CopilotPlugin (T028–T029) is the reference directory-based agent
- T036 is a batch task covering 17 trivial single-file agent plugins — each is ~10 lines of config subclassing SingleFileAgentPlugin
- Commit after each task or logical TDD pair (test + implementation)
- Stop at any checkpoint to validate the story independently
