# Tasks: Agent Instruction Prompt File System

**Branch**: `003-agent-prompt-governance`
**Input**: `specs/003-agent-prompt-governance/` — spec.md, plan.md, data-model.md, contracts/, research.md
**Approach**: TDD — every implementation task is preceded by its test task. PromptLoader and PromptValidator are the critical paths and are built before PromptFileManager so the parser is proven against fixture files before generated files depend on it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable with other [P] tasks in the same phase (different files, no shared state)
- **[Story]**: User story label (US1–US4)
- TDD rule: test task MUST be committed before its paired implementation task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Domain types, constants, and config additions that every subsequent task depends on.

- [X] T001 Add `GOVERNANCE_DOMAINS`, `PRECEDENCE_ORDER`, `EQUAL_PRIORITY_DOMAINS`, `AGNOSTIC_GOVERNANCE_DOMAINS`, `GOVERNANCE_FILE_PATTERN`, `SPECFORGE_CONFIG_FILE` constants to `src/specforge/core/config.py`
- [X] T002 Add `TemplateType.governance` variant to the `TemplateType` enum in `src/specforge/core/template_models.py`
- [X] T003 [P] Add `PromptThreshold`, `PromptRule`, `PromptFileMeta`, `PromptFile`, `PromptSet` frozen dataclasses to `src/specforge/core/prompt_models.py` (new file)
- [X] T004 [P] Add `ConflictEntry`, `ConflictReport`, `ProjectMeta` frozen dataclasses to `src/specforge/core/prompt_models.py`
- [X] T005 Write unit tests for all dataclass invariants (rule_id pattern, severity enum, empty thresholds) in `tests/unit/test_prompt_models.py`

**Checkpoint**: All domain types importable; `TemplateType.governance` registered; constants accessible from `config.py`

---

## Phase 2: Foundational (Governance Templates + Project Config)

**Purpose**: The Jinja2 governance templates and `.specforge/config.json` writer that all subsequent phases depend on. Placeholder rule content is sufficient — real content is filled in during US1.

- [X] T006 Create `src/specforge/templates/base/governance/` directory with `__init__.py`; add `"governance": TemplateType.governance` to `_TYPE_MAP` in `src/specforge/core/template_registry.py` — MUST be under `base/` for `_discover_built_in()` to scan it
- [X] T008 Create base governance template `src/specforge/templates/base/governance/_base_governance.md.j2` with the canonical `## Meta` / `## Precedence` / `## Rules` structure and one placeholder rule block
- [X] T009 [P] Create the 7 agnostic/base governance templates: `architecture.md.j2`, `backend.md.j2`, `frontend.md.j2`, `database.md.j2`, `security.md.j2`, `testing.md.j2`, `cicd.md.j2` in `src/specforge/templates/base/governance/` — each with domain-namespaced rule IDs (e.g., `ARCH-001`, `BACK-001`), 2 placeholder rules, correct `precedence:` value in `## Meta`, and at least one `MUST` verb per rule
- [X] T010 [P] Create stack-specific overrides for dotnet: `backend.dotnet.md.j2`, `testing.dotnet.md.j2` in `src/specforge/templates/base/governance/` — placeholder C#/xUnit content
- [X] T011 [P] Create stack-specific overrides for nodejs, python, go, java: `backend.nodejs.md.j2`, `testing.nodejs.md.j2`, `backend.python.md.j2`, `testing.python.md.j2`, `backend.go.md.j2`, `testing.go.md.j2`, `backend.java.md.j2`, `testing.java.md.j2` in `src/specforge/templates/base/governance/` — covers all 5 stacks per FR-001
- [X] T007 Write snapshot test for registry discovery of governance templates in `tests/snapshots/test_governance_registry.py` — assert all 7 base domains discoverable, all 5 stack variants present, zero templates from non-`base/governance/` path
- [X] T012 Write unit tests for `StackDetector` covering all 5 stack markers, ambiguous case (two markers → first-match wins per `SUPPORTED_STACKS` order), and no-marker fallback in `tests/unit/test_stack_detector.py`
- [X] T013 Implement `StackDetector.detect(project_root: Path) -> str` in `src/specforge/core/stack_detector.py` — scans for `.csproj`→dotnet, `package.json`→nodejs, `pyproject.toml`→python, `go.mod`→go, `pom.xml`→java; returns `"agnostic"` if no markers found

**Checkpoint**: Governance templates renderable by Jinja2; `StackDetector` fully tested; registry discovers governance type

---

## Phase 3: User Story 3 — PromptLoader (Critical Path)

**Goal**: `PromptLoader.load_for_feature(feature_id)` returns a fully populated `PromptSet` from fixture files on disk within 500 ms.

**Independent Test**: In a `tmp_path` with 7 hand-crafted governance fixture files and a `config.json`, `PromptLoader("feature-001").load_for_feature("feature-001")` returns `Ok(PromptSet)` with all 7 domains, correct `precedence` list, and parsed `PromptRule` objects.

- [X] T014 [US3] Write fixture factory `tests/unit/conftest.py::make_governance_fixtures(tmp_path, stack, domains)` — writes minimal but structurally valid governance files + `config.json` to `tmp_path` for use across all PromptLoader tests
- [X] T015 [US3] Write unit test: `PromptLoader` returns `Ok(PromptSet)` with 7 domain entries when all files present — assert `result.value.files.keys() == set(GOVERNANCE_DOMAINS)` and `result.value.precedence == PRECEDENCE_ORDER` in `tests/unit/test_prompt_loader.py`
- [X] T016 [US3] Write unit test: `PromptLoader` returns `Err` listing ALL missing files (by name and full path) when any governance file is absent — test with 3 missing files in one call in `tests/unit/test_prompt_loader.py`
- [X] T017 [US3] Write unit test: `PromptLoader` correctly parses `## Meta` fields (domain, stack, version, precedence, checksum) from fixture file in `tests/unit/test_prompt_loader.py`
- [X] T018 [US3] Write unit test: `PromptLoader` correctly parses `## Rules` section — assert rule_id, severity, scope, description, threshold key/value pairs, example_correct, example_incorrect are extracted in `tests/unit/test_prompt_loader.py`
- [X] T019 [US3] Write unit test: `PromptLoader` performs 2-step file resolution — finds `backend.dotnet.prompts.md` before `backend.prompts.md`; and falls back to `backend.prompts.md` when stack-specific file is absent in `tests/unit/test_prompt_loader.py`
- [X] T020 [US3] Write unit test: `PromptLoader` reads `config.json` to determine stack; returns `Err` with clear message when `config.json` is missing or malformed in `tests/unit/test_prompt_loader.py`
- [X] T021 [US3] Implement `PromptLoader.__init__(project_root: Path)` and `_read_project_meta() -> Result[ProjectMeta, str]` in `src/specforge/core/prompt_loader.py`
- [X] T022 [US3] Implement `PromptLoader._resolve_file_path(domain: str, stack: str) -> Path | None` — 2-step resolution logic in `src/specforge/core/prompt_loader.py`
- [X] T023 [US3] Implement `PromptLoader._parse_meta_section(meta_text: str) -> Result[PromptFileMeta, str]` — regex-based key-value extraction in `src/specforge/core/prompt_loader.py`
- [X] T024 [US3] Implement `PromptLoader._parse_rules_section(rules_text: str) -> Result[tuple[PromptRule, ...], str]` — split on `\n### `, parse each block in `src/specforge/core/prompt_loader.py`
- [X] T025 [US3] Implement `PromptLoader._parse_prompt_file(path: Path, content: str) -> Result[PromptFile, str]` — orchestrates meta + rules parsing in `src/specforge/core/prompt_loader.py`
- [X] T026 [US3] Implement `PromptLoader.load_for_feature(feature_id: str) -> Result[PromptSet, str]` — full pipeline: read config → resolve 7 paths → parse each → assemble PromptSet in `src/specforge/core/prompt_loader.py`
- [X] T027 [US3] Write performance assertion test: `load_for_feature()` completes in ≤500 ms on 7 files of 300 lines each using `time.perf_counter()` in `tests/unit/test_prompt_loader.py`

**Checkpoint**: All T015–T020 tests pass; `PromptLoader` is fully tested against fixture files; no dependency on PromptFileManager

---

## Phase 4: User Story 4 — PromptValidator + CLI Command (Critical Path)

**Goal**: `specforge validate-prompts` exits 0 with "No conflicts" or exits 1 reporting every threshold conflict with source files, winning value, and suggested resolution.

**Independent Test**: Run `specforge validate-prompts` via `CliRunner` in a `tmp_path` project with 2 intentionally conflicting governance files — assert exit code 1 and conflict reported with correct winner, loser, and suggested resolution.

- [X] T028 [US4] Write unit test: `PromptValidator.detect_conflicts()` returns empty `ConflictReport` when all 7 fixture files have non-overlapping threshold keys in `tests/unit/test_prompt_validator.py`
- [X] T029 [US4] Write unit test: `PromptValidator.detect_conflicts()` detects cross-priority conflict (`architecture` max_class_lines=50 vs `backend` max_class_lines=200) — assert `winning_domain="architecture"`, `is_ambiguous=False` in `tests/unit/test_prompt_validator.py`
- [X] T030 [US4] Write unit test: `PromptValidator.detect_conflicts()` detects intra-priority ambiguous conflict (`backend` vs `database` same threshold, different values) — assert `winning_domain="AMBIGUOUS"`, `is_ambiguous=True` in `tests/unit/test_prompt_validator.py`
- [X] T031 [US4] Write unit test: `PromptValidator.detect_conflicts()` reports ALL conflicts in one pass (3 conflicts → ConflictReport with 3 entries, not just first) in `tests/unit/test_prompt_validator.py`
- [X] T032 [US4] Implement `PromptValidator._build_threshold_index()`, `_find_conflicts()`, `_build_suggestion()` and `detect_conflicts(prompt_set: PromptSet) -> ConflictReport` in `src/specforge/core/prompt_validator.py`
- [X] T033 [US4] Write integration test for `specforge validate-prompts` via `CliRunner` in a `tmp_path` project with no conflicts — assert exit code 0 and "No conflicts detected" in stdout in `tests/integration/test_validate_prompts_cmd.py`
- [X] T034 [US4] Write integration test for `specforge validate-prompts` with 2 threshold conflicts — assert exit code 1, both conflicts in stdout with rule IDs, domain names, values, and suggestion in `tests/integration/test_validate_prompts_cmd.py`
- [X] T035 [US4] Write integration test for `specforge validate-prompts` in a directory with no `.specforge/` — assert exit code 2 and error message "Run 'specforge init'" in `tests/integration/test_validate_prompts_cmd.py`
- [X] T036 [US4] Implement `validate_prompts_cmd.py` Click command: read `config.json`, call `PromptLoader.load_for_feature("validate")`, call `PromptValidator.detect_conflicts()`, print Rich table output, exit with correct code in `src/specforge/cli/validate_prompts_cmd.py`
- [X] T037 [US4] Register `validate_prompts` command in `src/specforge/cli/main.py`

**Checkpoint**: `specforge validate-prompts` fully functional; all T028–T035 tests pass; 100% exit code correctness verified

---

## Phase 5: User Story 1 — PromptFileManager + Init Integration

**Goal**: `specforge init myapp --stack dotnet` generates 7 governance files in `.specforge/prompts/` and writes `.specforge/config.json`. Files are parseable by the already-proven `PromptLoader`.

**Independent Test**: Run `specforge init myapp --stack dotnet` in a `tmp_path`; then call `PromptLoader.load_for_feature("any")` on the result — assert `Ok(PromptSet)` with all 7 domains, dotnet-specific filenames, and non-empty rules in each file.

- [X] T038 [US1] Write unit test: `PromptFileManager.resolve_path(domain, stack)` returns `backend.dotnet.prompts.md` for dotnet and `architecture.prompts.md` for agnostic domains in `tests/unit/test_prompt_manager.py`
- [X] T039 [US1] Write unit test: `PromptFileManager.generate()` writes exactly 7 files to `tmp_path/.specforge/prompts/` and writes `config.json` with correct stack in `tests/unit/test_prompt_manager.py`
- [X] T040 [US1] Write unit test: each generated file is immediately parseable by `PromptLoader._parse_prompt_file()` — assert no parse errors for all 7 generated files in `tests/unit/test_prompt_manager.py`
- [X] T041 [US1] Write snapshot tests for all governance template variants (dotnet, nodejs, python, go, java, agnostic) in `tests/snapshots/test_governance_templates.py` using syrupy — for each snapshot assert: (a) FR-002 stack-specific content differs between stacks, (b) FR-003 every rule description contains `MUST`, `MUST NOT`, or `is prohibited`, (c) FR-017 all rule IDs use the correct domain namespace prefix (e.g., `BACK-` for backend)
- [X] T042 [US1] Implement `PromptFileManager.__init__(project_root, registry)`, `resolve_path()`, and `generate_one(domain, config) -> Result[Path, str]` in `src/specforge/core/prompt_manager.py`
- [X] T043 [US1] Implement `PromptFileManager.generate(config) -> Result[list[Path], str]` — iterates all 7 domains, calls `generate_one`, writes `config.json`, returns list of written paths in `src/specforge/core/prompt_manager.py`
- [X] T044 [US1] Implement `StackDetector` integration in `src/specforge/cli/init_cmd.py`: when `--stack` is omitted, call `StackDetector.detect(target_dir)` before calling `ProjectConfig.create()`
- [X] T045 [US1] Integrate `PromptFileManager.generate()` call into `src/specforge/core/scaffold_builder.py` — called after core scaffold files are planned; governance file paths added to `ScaffoldPlan.files`
- [X] T046 [US1] Write integration test: `specforge init myapp --stack dotnet` in `tmp_path` produces all 7 governance files; subsequent `PromptLoader.load_for_feature("x")` returns `Ok(PromptSet)`; assert wall-clock time of init command is <5 seconds (SC-001) in `tests/integration/test_init_cmd_governance.py`
- [X] T047 [US1] Write integration test: `specforge init myapp` (no `--stack`, `package.json` present in cwd) auto-detects nodejs and generates `backend.nodejs.prompts.md` in `tests/integration/test_init_cmd_governance.py`
- [X] T048 [US1] Write integration test: `specforge init myapp --stack ruby` exits code 1 with error listing all supported stacks in `tests/integration/test_init_cmd_governance.py`

**Checkpoint**: Full round-trip proven — init generates files, PromptLoader parses them correctly; snapshot tests lock in template rendering

---

## Phase 6: User Story 2 — Customization + `--force` Preservation

**Goal**: Editing a governance file on disk is reflected in the next `load_for_feature()` call; `--force` on a project with customized files preserves those files.

**Independent Test**: In `tmp_path`, generate files, edit `backend.dotnet.prompts.md` to change a threshold value, call `PromptLoader.load_for_feature()` — assert the new value is present. Then run `--force` — assert the edited file is unchanged.

- [X] T049 [US2] Write unit test: `PromptFileManager.is_customized(file_path, stack)` returns `False` for a freshly generated file and `True` after any byte is changed in `tests/unit/test_prompt_manager.py`
- [X] T050 [US2] Implement `PromptFileManager.is_customized(file_path: Path, stack: str) -> Result[bool, str]` using SHA-256 re-render comparison via `hashlib.sha256` in `src/specforge/core/prompt_manager.py`
- [X] T051 [US2] Write integration test: `load_for_feature()` returns edited threshold value after in-place edit of governance file with no CLI command between edit and load in `tests/integration/test_prompt_customization.py`
- [X] T052 [US2] Write integration test: `specforge init --force` in a project with one customized governance file skips that file and regenerates only the default-state files; assert customized content preserved in `tests/integration/test_prompt_customization.py`
- [X] T053 [US2] Update `src/specforge/core/scaffold_builder.py` `--force` path to call `PromptFileManager.is_customized()` per governance file and skip customized files; add `skipped` entries to `ScaffoldResult`

**Checkpoint**: US2 fully verified; no-cache behavior proven; `--force` safety net for customized files works

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T054 Run `uv run ruff check src/ tests/` and fix all lint errors introduced in this feature
- [X] T055 Run `uv run pytest --cov=specforge --cov-report=term-missing` and achieve 100% unit test coverage for `prompt_loader.py`, `prompt_validator.py`, `prompt_manager.py`, `prompt_context.py`, `stack_detector.py`
- [X] T056 Write unit test for `PromptContextBuilder.build()` — assert all 7 domains present in output, task_domain content appears first when specified, total output length ≤500 lines × 7 files in `tests/unit/test_prompt_context.py`
- [X] T057 Implement `PromptContextBuilder.build(prompt_set, task_domain=None) -> str` in `src/specforge/core/prompt_context.py` — concatenates all 7 `raw_content` values in `PRECEDENCE_ORDER`; if `task_domain` given, moves that domain's content first
- [X] T058 Update `CLAUDE.md` `## Project Structure` to reflect new modules (`prompt_manager.py`, `prompt_loader.py`, `prompt_validator.py`, `prompt_context.py`, `stack_detector.py`, `templates/governance/`)

---

## Dependency Graph

```text
Phase 1 (T001–T005)
    │
    ├─► Phase 2 (T006–T013)  ← must complete before Phases 3, 4, 5
    │       │
    │       ├─► Phase 3: PromptLoader (T014–T027)   ─┐
    │       │                                         ├─► Phase 5: PromptFileManager (T038–T048)
    │       └─► Phase 4: PromptValidator (T028–T037) ─┘
    │                                                       │
    │                                                       └─► Phase 6: Customization (T049–T053)
    │                                                                           │
    └──────────────────────────────────────────────────────────────────────────┴─► Final (T054–T058)
```

**Phases 3 and 4 are independent** — PromptLoader and PromptValidator can be built in parallel after Phase 2.

---

## Parallel Execution Opportunities

**Within Phase 2**: T009, T010, T011 are parallelizable (separate template files, no shared state)

**Phases 3 and 4**: Entire Phase 3 (PromptLoader) and Phase 4 (PromptValidator) can be developed in parallel by two contributors after Phase 2 completes, since PromptValidator depends on `PromptSet` type (defined in Phase 1) not on PromptLoader's implementation.

**Within Phase 5**: T041 (snapshot tests) and T042 (PromptFileManager impl) are parallelizable.

---

## Implementation Strategy

**MVP** (minimum to prove the critical path): Phases 1–4 (T001–T037)
- PromptLoader + PromptValidator fully working against fixture files
- `specforge validate-prompts` command operational
- No dependency on generated prompt files — uses hand-crafted test fixtures

**Full delivery**: Add Phases 5–6 (T038–T053) — connects the parser to the generator, proves the round-trip

**Defer to later**: T056–T057 (PromptContextBuilder) — only needed when sub-agent executor (Feature 009) integrates

---

## Summary

| Phase | Story | Tasks | Parallelizable |
|-------|-------|-------|----------------|
| 1 — Setup | — | T001–T005 | T003, T004 |
| 2 — Foundational | — | T006–T013 | T009, T010, T011 |
| 3 — PromptLoader | US3 | T014–T027 | — (sequential TDD pairs) |
| 4 — PromptValidator + CLI | US4 | T028–T037 | Phases 3 & 4 in parallel |
| 5 — PromptFileManager + Init | US1 | T038–T048 | T041, T042 |
| 6 — Customization | US2 | T049–T053 | — |
| Final — Polish | — | T054–T058 | T054, T055, T056 |
| **Total** | | **58 tasks** | |
