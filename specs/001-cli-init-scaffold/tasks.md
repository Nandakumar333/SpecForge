# Tasks: SpecForge CLI Init & Scaffold

**Input**: Design documents from `/specs/001-cli-init-scaffold/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli-commands.md, quickstart.md

**Tests**: TDD enforced per constitution. Test files MUST be created and confirmed failing BEFORE their implementation counterparts. Every task gets a conventional commit.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- Source: `src/specforge/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/snapshots/`

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure, packaging, and tooling config

- [x] T001 Create `pyproject.toml` with hatchling build backend, Click/Jinja2/Rich/GitPython dependencies, `specforge = "specforge.cli.main:cli"` entry point, and dev dependencies (pytest, pytest-cov, ruff, syrupy) — commit: `chore: add pyproject.toml with packaging and dependencies`
- [x] T002 [P] Create `src/specforge/__init__.py` with `__version__ = "0.1.0"` — commit: `chore: add specforge package init`
- [x] T003 [P] Create `src/specforge/__main__.py` with `from specforge.cli.main import cli; cli()` — commit: `chore: add __main__.py entry point`
- [x] T004 [P] Create empty `__init__.py` files for all sub-packages: `src/specforge/cli/__init__.py`, `src/specforge/core/__init__.py`, `src/specforge/plugins/__init__.py`, `src/specforge/plugins/agents/__init__.py`, `src/specforge/templates/__init__.py`, `src/specforge/templates/prompts/__init__.py`, `src/specforge/templates/features/__init__.py` — commit: `chore: create sub-package init files`
- [x] T005 [P] Create `.gitignore` for Python project (`.venv/`, `__pycache__/`, `*.egg-info/`, `dist/`, `.coverage`, `.pytest_cache/`) — commit: `chore: add .gitignore`
- [x] T006 [P] Create `ruff.toml` with line-length 88, target Python 3.11, `src/` as source, and selected rules — commit: `chore: add ruff configuration`

**Checkpoint**: `uv sync` succeeds; `uv run python -c "import specforge"` succeeds

---

## Phase 2: Foundational (Core Domain — Blocks All Stories)

**Purpose**: Build `Result[T]`, `config.py` constants, and data model types — all in `core/` with zero external dependencies

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests first

- [x] T007 [P] Write unit tests for `Result[T]` in `tests/unit/test_result.py` — Ok/Err creation, `.ok` property, `.map()`, `.bind()`, `.unwrap_or()` — commit: `test: add Result[T] unit tests`
- [x] T008 [P] Write unit tests for config constants in `tests/unit/test_config.py` — verify `AGENT_PRIORITY` order, `SUPPORTED_STACKS` membership, `AgentName`/`StackName` literal values, `AGENT_EXECUTABLES` keys — commit: `test: add config constants unit tests`
- [x] T009 [P] Write unit tests for `ProjectConfig` validation in `tests/unit/test_project_config.py` — valid names, invalid names rejected, mutual exclusion of `name`+`here` — commit: `test: add ProjectConfig validation tests`

### Implementation

- [x] T010 Implement `Result[T, E]` with `Ok` and `Err` dataclasses in `src/specforge/core/result.py` — commit: `feat: implement Result[T] Ok/Err pattern`
- [x] T011 [P] Implement constants and type literals in `src/specforge/core/config.py` — `AgentName`, `StackName`, `AGENT_PRIORITY`, `SUPPORTED_STACKS`, `AGENT_EXECUTABLES`, `PREREQUISITES`, scaffold directory names — commit: `feat: add config constants and type literals`
- [x] T012 [P] Implement domain dataclasses in `src/specforge/core/project.py` — `ProjectConfig`, `ScaffoldFile`, `ScaffoldPlan`, `ScaffoldResult` (frozen dataclasses, validation on `ProjectConfig.name`) — commit: `feat: add core domain dataclasses`

**Checkpoint**: `uv run pytest tests/unit/` — all T007–T009 tests pass

---

## Phase 3: User Story 1 — Scaffold New Project from Scratch (Priority: P1) 🎯 MVP

**Goal**: `specforge init myapp` creates a complete `.specforge/` directory tree with Jinja2-rendered templates, auto-detected agent, git init + commit, Rich summary output, and `--dry-run` preview

**Independent Test**: Run `specforge init myapp` in a tmp dir → verify file tree, git state, Rich output

### Tests first

- [x] T013 [P] [US1] Write unit tests for agent detection in `tests/unit/test_agent_detector.py` — monkeypatch `shutil.which`: single agent → detected, no agents → agnostic, multiple → first in priority, explicit override skips detection — commit: `test: add agent detection unit tests`
- [x] T014 [P] [US1] Write unit tests for scaffold plan builder in `tests/unit/test_scaffold_plan.py` — given `ProjectConfig` → verify `ScaffoldPlan.files` contains expected relative paths, directories list is correct, file ordering is deterministic — commit: `test: add scaffold plan builder unit tests`
- [x] T015 [P] [US1] Write unit tests for scaffold file writer in `tests/unit/test_scaffold_writer.py` — mock filesystem: files written to correct paths, skipped when existing + force, no writes on dry_run — commit: `test: add scaffold writer unit tests`
- [x] T016 [P] [US1] Write integration tests for `specforge init` in `tests/integration/test_init_cmd.py` — CliRunner + tmp_path: happy path creates dir + `.specforge/` + git commit; `--dry-run` writes nothing; missing name without `--here` exits 2; invalid name exits 1 with message matching `"Error: Invalid project name"`; existing dir without `--force` exits 1 with message matching `"already exists"`; `--force` adds missing files without overwriting existing; `--agent claude` uses explicit agent; `--stack python` applies stack; `--no-git` skips git; git not installed without `--no-git` exits 1 with message matching `"git is not installed"`; permission denied exits 1 with message matching `"Permission denied"` — commit: `test: add specforge init integration tests`
- [x] T017 [P] [US1] Create placeholder Jinja2 templates for scaffold output: `src/specforge/templates/constitution.md.j2`, `src/specforge/templates/gitignore.j2` (scaffolded project `.gitignore` content), one representative prompt template `src/specforge/templates/prompts/app-analyzer.md.j2`, and one feature template `src/specforge/templates/features/spec-template.md.j2` — commit: `test: add placeholder Jinja2 templates for scaffold`
- [x] T018 [P] [US1] Write snapshot tests for template rendering in `tests/snapshots/test_template_rendering.py` — render `constitution.md.j2` with sample context, assert against syrupy snapshot — commit: `test: add template rendering snapshot tests`

### Implementation

- [x] T019 [P] [US1] Implement `detect_agent()` and `agent_is_available()` in `src/specforge/core/agent_detector.py` — iterate `AGENT_PRIORITY`, call `shutil.which()`, return `DetectionResult` — commit: `feat: implement PATH-based agent detection`
- [x] T020 [US1] Implement `build_scaffold_plan()` in `src/specforge/core/project.py` — accept `ProjectConfig`, return `Result[ScaffoldPlan, str]` with all `.specforge/` directories and files (constitution, prompts, features, memory, scripts) — commit: `feat: implement scaffold plan builder`
- [x] T021 [US1] Implement `write_scaffold()` in `src/specforge/core/project.py` — accept `ScaffoldPlan`, create directories with `pathlib.Path.mkdir(parents=True)`, render each `ScaffoldFile` via Jinja2, write only if not existing or force=True, return `ScaffoldResult` — commit: `feat: implement scaffold file writer`
- [x] T022 [US1] Implement `render_template()` in `src/specforge/core/template_loader.py` — use `importlib.resources.files("specforge.templates")` to load `.md.j2`, render with Jinja2, return string — commit: `feat: implement Jinja2 template loader`
- [x] T023 [P] [US1] Implement `init_repo()` and `is_inside_existing_repo()` in `src/specforge/core/git_ops.py` — `Repo.init()`, `repo.index.add(["."])`, `repo.index.commit("chore: init specforge scaffold")`, handle existing repo case (skip init, still commit), handle git-not-installed case (return Err), return `Result[str, str]` — commit: `feat: implement git init and commit operations`
- [x] T024 [US1] Implement `render_dry_run_tree()` in `src/specforge/cli/output.py` — accept `ScaffoldPlan`, return `rich.tree.Tree` showing file tree that would be created — commit: `feat: implement dry-run tree preview`
- [x] T025 [US1] Implement `render_summary()` in `src/specforge/cli/output.py` — accept `ScaffoldResult`, return Rich-formatted summary: files created count, agent + source, stack, git state, next steps — commit: `feat: implement Rich summary renderer`
- [x] T026 [US1] Implement Click group root in `src/specforge/cli/main.py` — `@click.group()` with `--version`, `AppContext` dataclass on `ctx.obj`, register subcommands — commit: `feat: implement CLI root group with --version`
- [x] T027 [US1] Implement `specforge init` command in `src/specforge/cli/init_cmd.py` — wire all options (`NAME`, `--here`, `--agent`, `--stack`, `--force`, `--no-git`, `--dry-run`), call `build_scaffold_plan()` → `write_scaffold()` → `init_repo()`, translate `Result` errors to `click.ClickException`, output via Rich — commit: `feat: implement specforge init command`

**Checkpoint**: `uv run pytest tests/unit/ tests/integration/test_init_cmd.py tests/snapshots/` — US1 is fully functional; `uv run specforge init testproj --dry-run` shows tree

---

## Phase 4: User Story 2 — Initialize in Existing Project (Priority: P2)

**Goal**: `specforge init --here` scaffolds `.specforge/` into CWD without creating a subdirectory; `--here --force` adds missing files to an existing `.specforge/`

**Independent Test**: Run `specforge init --here` in a non-empty tmp dir → verify `.specforge/` created, existing files untouched

### Tests first

- [x] T028 [P] [US2] Write integration tests for `--here` workflow in `tests/integration/test_init_here_cmd.py` — CliRunner + tmp_path: `--here` in empty dir creates `.specforge/`; `--here` in dir with existing files preserves them; `--here` when `.specforge/` exists without `--force` exits 1; `--here --force` adds missing files, preserves existing — commit: `test: add --here integration tests`

### Implementation

- [x] T029 [US2] Extend `build_scaffold_plan()` in `src/specforge/core/project.py` to handle `here=True` — set `target_dir = CWD`, derive `name` from directory name — commit: `feat: support --here mode in scaffold plan builder`
- [x] T030 [US2] Extend `write_scaffold()` in `src/specforge/core/project.py` — when `force=True`, check each file existence before writing; skip existing; track in `ScaffoldResult.skipped` — commit: `feat: support --force merge-write in scaffold writer`

**Checkpoint**: `uv run pytest tests/integration/test_init_here_cmd.py` — US2 passes independently

---

## Phase 5: User Story 3 — Verify Prerequisites with `specforge check` (Priority: P3)

**Goal**: `specforge check` lists git, python, uv, and optionally the agent CLI with pass/fail status and install hints

**Independent Test**: Run `specforge check` → verify Rich table output with correct tool statuses

### Tests first

- [x] T031 [P] [US3] Write unit tests for prerequisite checker in `tests/unit/test_check.py` — monkeypatch `shutil.which` and version detection: all present → all pass, one missing → that tool fails, `--agent claude` adds claude to check list — commit: `test: add prerequisite checker unit tests`
- [x] T032 [P] [US3] Write integration tests for `specforge check` in `tests/integration/test_check_cmd.py` — CliRunner: exit 0 when all present (monkeypatched), exit 1 when missing, `--agent` flag adds agent check — commit: `test: add specforge check integration tests`

### Implementation

- [x] T033 [US3] Implement `check_prerequisites()` in `src/specforge/core/checker.py` — iterate `PREREQUISITES` + optional agent, call `shutil.which()`, attempt version detection via subprocess, return `list[CheckResult]` — commit: `feat: implement prerequisite checker`
- [x] T034 [US3] Implement `specforge check` command in `src/specforge/cli/check_cmd.py` — wire `--agent` option, call `check_prerequisites()`, render `rich.table.Table` with pass/fail symbols and install hints, exit 0/1 — commit: `feat: implement specforge check command`

**Checkpoint**: `uv run pytest tests/unit/test_check.py tests/integration/test_check_cmd.py` — US3 passes independently

---

## Phase 6: User Story 4 — Auto-Detect Installed AI Agent (Priority: P3)

**Goal**: When `--agent` is omitted, `specforge init` auto-detects the first agent CLI in PATH by priority order and configures the project accordingly

**Independent Test**: Monkeypatch PATH with a single agent, run `specforge init myapp` without `--agent`, verify agent-specific config in output

### Tests first

- [x] T035 [P] [US4] Write integration tests for agent auto-detection in `tests/integration/test_init_agent_detection.py` — CliRunner + monkeypatched `shutil.which`: claude only → detects claude; none → agnostic with warning; multiple → first in priority; explicit `--agent` overrides detection — commit: `test: add agent auto-detection integration tests`

### Implementation

- [x] T036 [US4] Wire agent detection into `init_cmd.py` in `src/specforge/cli/init_cmd.py` — if `--agent` not provided, call `detect_agent()` from `agent_detector.py`; include detection source in summary output (`auto-detected`, `explicit`, `agnostic`) — commit: `feat: wire agent auto-detection into init command`

**Checkpoint**: `uv run pytest tests/integration/test_init_agent_detection.py` — US4 passes independently

---

## Phase 7: User Story 5 — Decompose App Description (Priority: P4)

**Goal**: `specforge decompose "description"` accepts an app description and displays a stub feature list (App Analyzer integration deferred to Feature 004)

**Independent Test**: Run `specforge decompose "A task manager"` → verify command accepts input, prints placeholder output, exits 0

### Tests first

- [x] T037 [P] [US5] Write integration tests for `specforge decompose` in `tests/integration/test_decompose_cmd.py` — CliRunner: with description → exits 0 with stub output; without description → exits 2 with usage error — commit: `test: add specforge decompose integration tests`

### Implementation

- [x] T038 [US5] Implement `specforge decompose` command in `src/specforge/cli/decompose_cmd.py` — accept `DESCRIPTION` positional arg, print stub message indicating App Analyzer (Feature 004) integration pending, exit 0 — commit: `feat: implement specforge decompose stub command`

**Checkpoint**: `uv run pytest tests/integration/test_decompose_cmd.py` — US5 passes independently

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Template content, remaining Jinja2 templates, full snapshot coverage, quality gates

- [x] T039 [P] Create remaining Jinja2 prompt templates in `src/specforge/templates/prompts/` — `feature-specifier.md.j2`, `implementation-planner.md.j2`, `task-decomposer.md.j2`, `code-reviewer.md.j2`, `test-writer.md.j2`, `debugger.md.j2` — commit: `feat: add all agent prompt Jinja2 templates`
- [x] T040 [P] Create remaining Jinja2 feature templates in `src/specforge/templates/features/` — `plan-template.md.j2`, `tasks-template.md.j2`, `research-template.md.j2`, `data-model-template.md.j2`, `quickstart-template.md.j2`, `contracts-template.md.j2` — commit: `feat: add all feature Jinja2 templates`
- [x] T041 [P] Write snapshot tests for all new templates in `tests/snapshots/test_template_rendering.py` — one snapshot per `.md.j2` file with representative context — commit: `test: add snapshot tests for all templates`
- [x] T042 [P] Implement `AgentPlugin` ABC in `src/specforge/plugins/agents/base.py` — abstract methods for config file generation per agent. Note: concrete agent plugin modules (`claude.py`, `copilot.py`, etc.) are deferred to Feature 003 (plan.md D-02) — commit: `feat: add AgentPlugin abstract base class`
- [x] T043 Run `uv run ruff check src/ tests/` and fix any lint issues — commit: `chore: fix ruff lint issues`
- [x] T044 Run `uv run pytest --cov=specforge --cov-report=term-missing` and verify 100% core coverage — commit: `test: verify full test coverage`
- [x] T045 Run quickstart.md validation: execute each command from `quickstart.md` against a tmp directory, verify documented behavior matches — commit: `test: validate quickstart.md scenarios`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–7)**: All depend on Foundational phase completion
  - US1 (Phase 3) MUST complete before US2 (Phase 4) — US2 extends US1's scaffold logic
  - US3 (Phase 5), US4 (Phase 6), US5 (Phase 7) can start after Phase 2 completes
  - US4 (Phase 6) is best done after US1 (Phase 3) since it wires into the init command
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no other story dependencies — **MVP**
- **US2 (P2)**: After US1 — extends `build_scaffold_plan()` and `write_scaffold()`
- **US3 (P3)**: After Foundational — independent of US1/US2
- **US4 (P3)**: After US1 — wires detection into `init_cmd.py`
- **US5 (P4)**: After Foundational — independent stub command

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Core domain modules before CLI wiring
- Each story complete before moving to next priority

### Parallel Opportunities

- T002, T003, T004, T005, T006 in Setup are all [P]
- T007, T008, T009 in Foundational tests are all [P]
- T011, T012 in Foundational impl are [P] (after T010)
- T013–T018 in US1 tests are all [P]
- T019–T025 in US1 impl: T019 [P] with T022 [P] and T023 [P]; T020 → T021 → T024/T025 sequential
- US3 (Phase 5) and US5 (Phase 7) can run in parallel after Phase 2

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests in parallel (T013–T018):
T013: tests/unit/test_agent_detector.py
T014: tests/unit/test_scaffold_plan.py
T015: tests/unit/test_scaffold_writer.py
T016: tests/integration/test_init_cmd.py
T017: src/specforge/templates/ (placeholder templates)
T018: tests/snapshots/test_template_rendering.py

# Then launch independent impl tasks in parallel:
T019: src/specforge/core/agent_detector.py  ‖  T022: src/specforge/core/template_loader.py  ‖  T023: src/specforge/core/git_ops.py

# Sequential impl:
T020 → T021 → T024 → T025 → T026 → T027
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T006)
2. Complete Phase 2: Foundational (T007–T012)
3. Complete Phase 3: User Story 1 (T013–T027)
4. **STOP and VALIDATE**: `specforge init myapp --dry-run` works; all tests pass
5. This is a deployable MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test → **MVP: `specforge init` works** ✅
3. Add US2 → Test → `--here` workflow works
4. Add US3 → Test → `specforge check` works
5. Add US4 → Test → Agent auto-detection works
6. Add US5 → Test → `specforge decompose` stub ready
7. Polish → Full template set + coverage

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Every task gets a conventional commit (`feat:`, `test:`, `chore:`)
- TDD enforced: test tasks are sequenced BEFORE their implementation tasks
- Constitution Principle III: functions ≤ 30 lines, classes ≤ 200 lines — enforced at review
- Constitution Principle III: `Result[T]` for all recoverable errors in `core/`
