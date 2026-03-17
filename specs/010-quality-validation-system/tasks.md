# Tasks: Quality Validation System

**Input**: Design documents from `/specs/010-quality-validation-system/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/
**Approach**: TDD — tests written and failing before each implementation. Each checker independently testable.

**Tests**: INCLUDED (TDD requested). All test tasks MUST be completed and verified failing before corresponding implementation tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create directory structure and configuration constants for the quality validation system.

- [x] T001 Create directory structure: `src/specforge/core/checkers/`, `src/specforge/core/analyzers/`, `tests/unit/checkers/`, `tests/unit/analyzers/` with `__init__.py` files
- [x] T002 Add quality validation constants to `src/specforge/core/config.py`: `ERROR_CATEGORIES` tuple, `CONTAINER_RELEVANT_PATTERNS` frozenset, `THRESHOLD_KEY_MAPPING` dict, `SECRET_PATTERNS` tuple, `MAX_FUNCTION_LINES` (30), `MAX_CLASS_LINES` (200), `ENTROPY_THRESHOLD` float

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models, protocols, and templates that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Data Models

- [x] T003 [P] Write tests for all quality data models in `tests/unit/test_quality_models.py`: frozen dataclass validation for ErrorCategory, ContractAttribution, CheckLevel enums; CheckResult, ErrorDetail, QualityGateResult, FixAttempt, DiagnosticReport, QualityReport, FunctionInfo, ClassInfo frozen dataclasses with field defaults and immutability checks
- [x] T004 Implement all quality data models in `src/specforge/core/quality_models.py`: ErrorCategory enum (SYNTAX, LOGIC, TYPE, LINT, COVERAGE, DOCKER, CONTRACT, BOUNDARY, SECURITY), ContractAttribution enum (CONSUMER, PROVIDER), CheckLevel enum (TASK, SERVICE), and all frozen dataclasses per data-model.md; QualityReport includes `schema_version: str` field (initial value "1.0")

### Protocols & Registry

- [x] T005 [P] Write tests for CheckerProtocol conformance and checker registry in `tests/unit/checkers/test_checker_registry.py`: verify protocol structural typing works, test `ALL_CHECKERS` registry tuple, test `get_applicable_checkers(architecture)` filtering returns correct checkers per architecture type (monolithic, microservice, modular-monolith) per Contract §3 applicability table
- [x] T006 Implement CheckerProtocol and checker registry in `src/specforge/core/checkers/__init__.py`: `CheckerProtocol` using `typing.Protocol` with `name`, `category`, `levels` (tuple of CheckLevel) properties and `check()`, `is_applicable()` methods; `ALL_CHECKERS` tuple; `get_applicable_checkers(architecture: str, level: CheckLevel) -> tuple[CheckerProtocol, ...]` filters by both architecture and level

### Language Analyzer Protocol

- [x] T007 [P] Write tests for LanguageAnalyzerProtocol and PythonAnalyzer in `tests/unit/analyzers/test_python_analyzer.py`: test `supports_extension(".py")` returns True, `supports_extension(".cs")` returns False; test `analyze_functions()` on a sample .py file with functions of varying lengths returns correct FunctionInfo tuples; test `analyze_classes()` returns correct ClassInfo tuples; test nested functions/classes; test async functions; test files with syntax errors return Err
- [x] T008 Implement LanguageAnalyzerProtocol in `src/specforge/core/analyzers/__init__.py` and PythonAnalyzer in `src/specforge/core/analyzers/python_analyzer.py`: Protocol with `analyze_functions()`, `analyze_classes()`, `supports_extension()` methods; PythonAnalyzer using `ast.parse()`, walking `FunctionDef`/`AsyncFunctionDef`/`ClassDef` nodes, computing line spans via `node.lineno`/`node.end_lineno`

### Jinja2 Templates

- [x] T009 [P] Create targeted fix prompt template in `src/specforge/templates/base/executor/fix-prompt.md.j2`: template accepts `error_category`, `checker_name`, `error_details` (list of ErrorDetail), `affected_files`, `original_task`, `attempt_number`, `prior_attempts` (list of FixAttempt), `specific_instructions`; renders category-specific fix guidance
- [x] T009a [P] Create quality report JSON template in `src/specforge/templates/base/executor/quality-report.json.j2`: template accepts QualityReport fields, renders valid JSON with `schema_version`, all check results, fix attempts, and diagnostic report sections
- [x] T010 [P] Create diagnostic report template in `src/specforge/templates/base/executor/diagnostic-report.md.j2`: template accepts `task_id`, `original_error` (QualityGateResult), `attempts` (list of FixAttempt), `still_failing`, `suggested_steps`; renders timeline with per-attempt details, remaining failures, and category-specific remediation suggestions
- [x] T010a [P] Write snapshot tests for all executor templates in `tests/snapshots/test_executor_templates.py`: snapshot test fix-prompt.md.j2 with sample SYNTAX/DOCKER/CONTRACT errors; snapshot test diagnostic-report.md.j2 with 3-attempt exhaustion scenario; snapshot test quality-report.json.j2 with sample gate result

**Checkpoint**: Foundation ready — all models, protocols, templates in place. Checker implementation can begin.

---

## Phase 3: User Story 1 — Architecture-Aware Quality Gate (Priority: P1) 🎯 MVP

**Goal**: Comprehensive quality gate that automatically runs the right set of checks based on project architecture type (monolithic, microservice, modular-monolith).

**Independent Test**: Run quality gate against a completed task in both microservice and monolith projects; verify architecture-specific checks execute alongside standard checks.

### Tests for Standard Checkers ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US1] Write tests for BuildChecker in `tests/unit/checkers/test_build_checker.py`: test passing build returns CheckResult(passed=True), test failing build returns CheckResult(passed=False, category=SYNTAX) with captured output, test `is_applicable()` returns True for all architectures, test subprocess timeout handling, test `name` is "build" and `level` is TASK
- [x] T012 [P] [US1] Write tests for LintChecker in `tests/unit/checkers/test_lint_checker.py`: test passing lint returns CheckResult(passed=True), test failing lint parses ruff output into ErrorDetail tuples with file paths and line numbers and rule IDs, test only .py files are linted, test empty file list skips check, test `category` is LINT, test `is_applicable()` returns True for all architectures
- [x] T013 [P] [US1] Write tests for TestChecker in `tests/unit/checkers/test_test_checker.py`: test passing tests returns CheckResult(passed=True), test failing tests parses pytest output into ErrorDetail with test names, test `category` is LOGIC, test `is_applicable()` returns True for all architectures
- [x] T014 [P] [US1] Write tests for CoverageChecker in `tests/unit/checkers/test_coverage_checker.py`: test coverage above threshold passes, test coverage below threshold fails with actual vs required in output, test missing threshold in governance skips check (CheckResult with skipped=True), test threshold loaded from PromptLoader, test `category` is COVERAGE
- [x] T015 [P] [US1] Write tests for LineLimitChecker in `tests/unit/checkers/test_line_limit_checker.py`: test function under 30 lines passes, test function over 30 lines fails with FunctionInfo in ErrorDetail, test class under 200 lines passes, test class over 200 lines fails with ClassInfo in ErrorDetail, test non-.py files are skipped with warning, test delegates to LanguageAnalyzerProtocol, test `category` is LINT
- [x] T016 [P] [US1] Write tests for SecretChecker in `tests/unit/checkers/test_secret_checker.py`: test file with AWS key pattern detected (AKIA...), test file with API token pattern detected, test file with high-entropy string detected, test normal code passes, test test fixture files are exempted, test `category` is SYNTAX, test `is_applicable()` returns True for all architectures
- [x] T017 [P] [US1] Write tests for TodoChecker in `tests/unit/checkers/test_todo_checker.py`: test file with TODO comment detected with line number, test file with FIXME detected, test file with HACK detected, test clean file passes, test case-insensitive matching, test `category` is LINT
- [x] T018 [P] [US1] Write tests for PromptRuleChecker in `tests/unit/checkers/test_prompt_rule_checker.py`: test Tier 1 threshold `max_function_lines=30` delegates to LineLimitChecker, test Tier 1 threshold `min_coverage_percent=80` delegates to CoverageChecker, test Tier 2 descriptive rules collected for AI context but not enforced, test missing PromptLoader skips check, test `category` is LINT

### Implementation for Standard Checkers

- [x] T019 [P] [US1] Implement BuildChecker in `src/specforge/core/checkers/build_checker.py`: run project build command via subprocess, capture stdout/stderr, parse exit code, return CheckResult with category=SYNTAX on failure; `is_applicable()` returns True for all architectures; `level` = TASK
- [x] T020 [P] [US1] Implement LintChecker in `src/specforge/core/checkers/lint_checker.py`: run `ruff check --output-format=json` on changed .py files, parse JSON output into ErrorDetail tuples with file/line/column/code/message, return CheckResult with category=LINT; `is_applicable()` returns True for all architectures; `level` = TASK
- [x] T021 [P] [US1] Implement TestChecker in `src/specforge/core/checkers/test_checker.py`: run `python -m pytest -x --tb=short -q`, parse FAILED lines into ErrorDetail with test names, return CheckResult with category=LOGIC; `is_applicable()` returns True for all architectures; `level` = TASK
- [x] T022 [P] [US1] Implement CoverageChecker in `src/specforge/core/checkers/coverage_checker.py`: load `min_coverage_percent` threshold from PromptLoader, run `python -m pytest --cov --cov-report=json`, parse coverage percentage, compare to threshold, return CheckResult with category=COVERAGE; skip if no threshold defined; `level` = TASK
- [x] T023 [P] [US1] Implement LineLimitChecker in `src/specforge/core/checkers/line_limit_checker.py`: delegate to registered LanguageAnalyzerProtocol implementations, check functions >30 lines and classes >200 lines, return CheckResult with ErrorDetail per violation; skip non-supported extensions with warning; `category` = LINT; `level` = TASK
- [x] T024 [P] [US1] Implement SecretChecker in `src/specforge/core/checkers/secret_checker.py`: scan changed files with regex patterns from `SECRET_PATTERNS` config + Shannon entropy analysis for high-entropy strings, exempt test fixtures, return CheckResult with category=SECURITY and ErrorDetail per detection; `levels` = (TASK,)
- [x] T025 [P] [US1] Implement TodoChecker in `src/specforge/core/checkers/todo_checker.py`: scan changed files for TODO/FIXME/HACK comments (case-insensitive regex), return CheckResult with category=LINT and ErrorDetail with file/line/message; `level` = TASK
- [x] T026 [P] [US1] Implement PromptRuleChecker in `src/specforge/core/checkers/prompt_rule_checker.py`: load PromptSet via PromptLoader, extract PromptThreshold entries, map known threshold keys to checker delegations via `THRESHOLD_KEY_MAPPING`, collect Tier 2 descriptive rules as context string, return CheckResult; `level` = TASK

### Tests for Architecture-Specific Checkers ⚠️

- [x] T027 [P] [US1] Write tests for DockerBuildChecker in `tests/unit/checkers/test_docker_checker.py`: test `is_applicable("microservice")` returns True, test `is_applicable("monolithic")` returns False, test Docker build success returns passed, test Docker build failure with "missing dependency" returns CheckResult(category=DOCKER) with parsed error, test changed files not intersecting container-relevant paths skips check, test `levels` = (TASK,), test missing Docker CLI skips with warning
- [x] T027a [P] [US1] Write tests for DockerServiceChecker in `tests/unit/checkers/test_docker_service_checker.py`: test `is_applicable("microservice")` returns True, test `levels` = (SERVICE,), test compose start success, test compose start failure returns CheckResult(category=DOCKER), test health check endpoint returns 200 after compose start, test health check failure, test missing docker-compose CLI skips with warning
- [x] T028 [P] [US1] Write tests for ContractChecker in `tests/unit/checkers/test_contract_checker.py`: test `is_applicable("microservice")` returns True, test `is_applicable("monolithic")` returns False, test consumer test failure returns CheckResult(category=CONTRACT, attribution=CONSUMER), test provider verification failure returns CheckResult(category=CONTRACT, attribution=PROVIDER), test passing contract tests, test `level` is SERVICE
- [x] T029 [P] [US1] Write tests for BoundaryChecker in `tests/unit/checkers/test_boundary_checker.py`: test `is_applicable("modular-monolith")` returns True, test `is_applicable("monolithic")` returns False, test `is_applicable("microservice")` returns False, test cross-module direct data access detected returns CheckResult(category=BOUNDARY), test module interface compliance violation detected, test clean code passes, test `level` is TASK

### Implementation for Architecture-Specific Checkers

- [x] T030 [P] [US1] Implement DockerBuildChecker in `src/specforge/core/checkers/docker_checker.py`: check changed files against `CONTAINER_RELEVANT_PATTERNS`, run `docker build` via subprocess, parse error output into ErrorDetail, handle missing Docker CLI gracefully (skip with warning); `is_applicable()` True only for "microservice"; `category` = DOCKER; `levels` = (TASK,)
- [x] T030a [P] [US1] Implement DockerServiceChecker in `src/specforge/core/checkers/docker_service_checker.py`: run `docker-compose up -d` via subprocess, wait for health check endpoint (HTTP GET), verify 200 response; handle missing docker-compose CLI gracefully (skip with warning); `is_applicable()` True only for "microservice"; `category` = DOCKER; `levels` = (SERVICE,)
- [x] T031 [P] [US1] Implement ContractChecker in `src/specforge/core/checkers/contract_checker.py`: run Pact consumer tests via subprocess, parse output for consumer vs provider attribution using heuristics from Research §R6, set `ContractAttribution` on CheckResult; `is_applicable()` True only for "microservice"; `category` = CONTRACT; `level` = SERVICE
- [x] T032 [P] [US1] Implement BoundaryChecker in `src/specforge/core/checkers/boundary_checker.py`: read module boundaries from `.specforge/manifest.json` `modules` key (fallback: directory-convention detection — top-level dirs under `src/` as modules, `__init__.py`/`api.py`/`interfaces/` as public API); analyze changed files for cross-module data access patterns (import analysis, database model/repository references outside module boundary), return CheckResult with ErrorDetail; `is_applicable()` True only for "modular-monolith"; `category` = BOUNDARY; `levels` = (TASK,)

### Missing Requirement Checkers (FR-014, FR-015, FR-016, FR-019)

- [x] T032a [P] [US1] Write tests for UrlChecker in `tests/unit/checkers/test_url_checker.py`: test `is_applicable("microservice")` returns True, test `is_applicable("monolithic")` returns False, test detects hardcoded `http://service-name:port` URLs in Python/config files, test ignores localhost/test URLs, test ignores URLs in test fixtures, test CheckResult has category=BOUNDARY, test `levels` = (TASK,)
- [x] T032b [P] [US1] Implement UrlChecker in `src/specforge/core/checkers/url_checker.py`: scan changed files for hardcoded service URLs using regex patterns (HTTP/HTTPS URLs excluding localhost, 127.0.0.1, test domains), flag hardcoded service endpoints that should use service discovery or config; `is_applicable()` True only for "microservice"; `category` = BOUNDARY; `levels` = (TASK,)
- [x] T032c [P] [US1] Write tests for InterfaceChecker in `tests/unit/checkers/test_interface_checker.py`: test `is_applicable("microservice")` returns True, test `is_applicable("monolithic")` returns False, test proto file compilation success, test proto file with syntax error returns CheckResult(category=CONTRACT), test event schema validation against published contract, test invalid event schema detected, test no proto/schema files gracefully skipped, test `levels` = (SERVICE,)
- [x] T032d [P] [US1] Implement InterfaceChecker in `src/specforge/core/checkers/interface_checker.py`: find `.proto` files in project, run `protoc --dry_run` (or equivalent) via subprocess for compilation check; find event schema files and validate against published contracts; handle missing protoc CLI gracefully (skip with warning); `is_applicable()` True only for "microservice"; `category` = CONTRACT; `levels` = (SERVICE,)
- [x] T032e [P] [US1] Write tests for MigrationChecker in `tests/unit/checkers/test_migration_checker.py`: test `is_applicable("modular-monolith")` returns True, test `is_applicable("monolithic")` returns False, test shared migration file modifying tables owned by another module detected, test migration within own module passes, test CheckResult has category=BOUNDARY, test `levels` = (TASK,)
- [x] T032f [P] [US1] Implement MigrationChecker in `src/specforge/core/checkers/migration_checker.py`: scan changed migration files, cross-reference table names against module boundary definitions from manifest (same source as BoundaryChecker), flag migrations that modify tables owned by other modules; `is_applicable()` True only for "modular-monolith"; `category` = BOUNDARY; `levels` = (TASK,)

### QualityGate Orchestrator

- [x] T033 [US1] Write tests for QualityGate in `tests/unit/test_quality_gate.py`: test gate with monolithic architecture runs only standard checkers (8), test gate with microservice architecture runs standard + docker-build + docker-service + contract + url + interface (13 at TASK level, additional at SERVICE level), test gate with modular-monolith runs standard + boundary + migration (10), test `run_task_checks()` filters to TASK-level checkers only, test `run_service_checks()` filters to SERVICE-level checkers only, test skipped checkers included in QualityGateResult.skipped_checks, test all checker results aggregated into QualityGateResult, test gate fails if any non-skipped checker fails
- [x] T034 [US1] Implement QualityGate in `src/specforge/core/quality_gate.py`: constructor accepts architecture, project_root, service_slug, prompt_loader, optional checkers tuple; `run_task_checks()` filters applicable TASK-level checkers and runs them sequentially, aggregates into QualityGateResult; `run_service_checks()` filters SERVICE-level checkers; handles checker errors gracefully (skip with warning)

### Quality Report Persistence

- [x] T035 [P] [US1] Write tests for QualityReport writer/reader in `tests/unit/test_quality_report.py`: test write creates valid JSON at `.quality-report.json`, test read parses JSON back into QualityReport dataclass, test report overwrites on subsequent writes, test JSON schema includes all QualityReport fields
- [x] T036 [P] [US1] Implement QualityReport writer/reader in `src/specforge/core/quality_report.py`: `write_report(report: QualityReport, output_dir: Path)` serializes to JSON via Jinja2 template (`quality-report.json.j2`); `read_report(path: Path) -> Result[QualityReport, str]` deserializes; report includes `schema_version` field for forward-compatibility

**Checkpoint**: Quality gate fully functional with all 15 checkers (8 standard + 4 microservice + 3 modular-monolith). Can run `run_task_checks()` and `run_service_checks()` for any architecture. Architecture filtering verified. This is the MVP.

---

## Phase 4: User Story 2 — Targeted Auto-Fix with Error Categorization (Priority: P1)

**Goal**: Auto-fix engine that categorizes failures and generates targeted fix prompts per error category — not generic "fix the error" messages.

**Independent Test**: Feed known error outputs (Docker build failure, lint violation, contract mismatch, secret detection) and verify generated fix prompts contain specific, actionable instructions.

### Tests for Auto-Fix Engine ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T037 [US2] Write tests for AutoFixEngine error categorization in `tests/unit/test_auto_fix_engine.py`: test SYNTAX error (build failure) generates prompt referencing specific compilation error and file; test LINT error generates prompt with exact file/line/rule ID; test DOCKER error "missing dependency libpq" generates prompt saying "Add libpq-dev to Dockerfile apt-get install" not generic "fix Docker error"; test CONTRACT/CONSUMER error generates prompt referencing schema field mismatch and contract file; test CONTRACT/PROVIDER error skips auto-fix and returns immediate escalation; test COVERAGE error generates prompt identifying uncovered function and file; test BOUNDARY error generates prompt specifying which module boundary was crossed; test LOGIC error (test failure) generates prompt analyzing test assertion vs actual behavior; test TYPE error generates prompt with type annotation fix; test SECURITY error generates prompt instructing secret removal/externalization to env vars

### Implementation for Auto-Fix Engine

- [x] T038 [US2] Implement AutoFixEngine core in `src/specforge/core/auto_fix_engine.py`: constructor accepts TaskRunner, QualityGate, TemplateRenderer, max_attempts=3; `categorize_failures(gate_result: QualityGateResult) -> tuple[CheckResult, ...]` extracts failed checks; `generate_fix_prompt(original: ImplementPrompt, failure: CheckResult, attempt: int, prior_attempts: tuple[FixAttempt, ...]) -> ImplementPrompt` renders fix-prompt.md.j2 template with category-specific instructions per error category mapping; handles CONTRACT/PROVIDER attribution by returning immediate escalation signal

### Fix Prompt Strategy per Category

- [x] T039 [P] [US2] Write tests for category-specific fix prompt strategies in `tests/unit/test_fix_strategies.py`: test SYNTAX strategy includes compilation error text and affected file path; test LINT strategy includes "run ruff --fix first, then manually fix remaining" with specific rule IDs; test DOCKER strategy parses Dockerfile error and suggests specific layer fix; test CONTRACT strategy references Pact failure details and contract file; test COVERAGE strategy identifies uncovered lines and suggests test file; test BOUNDARY strategy suggests interface refactoring for the crossed module boundary
- [x] T040 [P] [US2] Implement category-specific fix prompt strategies as methods in `src/specforge/core/auto_fix_engine.py`: `_syntax_strategy()`, `_lint_strategy()`, `_docker_strategy()`, `_contract_strategy()`, `_coverage_strategy()`, `_boundary_strategy()`, `_logic_strategy()`, `_type_strategy()`, `_security_strategy()` — each returns a `specific_instructions` string used in the fix-prompt.md.j2 template context; SECURITY strategy instructs removal/externalization of detected secrets

**Checkpoint**: AutoFixEngine generates targeted, category-specific fix prompts for all 9 error categories (SYNTAX, LOGIC, TYPE, LINT, COVERAGE, DOCKER, CONTRACT, BOUNDARY, SECURITY). Provider-attributed contract failures escalate immediately.

---

## Phase 5: User Story 3 — Auto-Fix Retry with Attempt Budget (Priority: P2)

**Goal**: Retry loop making up to 3 targeted fix attempts per task, with progressive context and regression detection.

**Independent Test**: Provide a task with a complex failure requiring multiple iterations; verify each successive prompt includes prior attempt history.

### Tests for Retry Loop ⚠️

- [x] T041 [US3] Write tests for auto-fix retry loop in `tests/unit/test_auto_fix_engine.py` (extend): test attempt 1 generates fix prompt with categorized error and specific instructions; test attempt 2 prompt includes what attempt 1 changed and why it failed; test attempt 3 prompt includes full history of attempts 1 and 2; test successful fix on attempt 1 returns Ok with changed files; test successful fix on attempt 2 returns Ok with all cumulative changed files; test all 3 attempts exhausted returns Err with diagnostic summary

### Tests for Regression Detection ⚠️

- [x] T042 [P] [US3] Write tests for regression detection and revert in `tests/unit/test_auto_fix_engine.py` (extend): test fix that introduces new failure (previously-passing checker now fails) is detected as regression; test regression triggers git checkout of fix files; test reverted attempt recorded in FixAttempt with `reverted=True` and `revert_reason`; test next attempt prompt includes anti-regression guidance; test selective re-check runs only failed checkers plus regression check on passing checkers

### Implementation for Retry Loop

- [x] T043 [US3] Implement retry loop in `src/specforge/core/auto_fix_engine.py`: `fix(original_prompt: ImplementPrompt, gate_result: QualityGateResult, changed_files: list[Path], mode: ExecutionMode) -> Result[list[Path], str]` method — loop 1..max_attempts: generate targeted fix prompt with progressive context → execute via TaskRunner → selective re-check (only failed checkers + regression check) → detect regression (compare against prior QualityGateResult) → revert if regression → record FixAttempt → continue or return Ok/Err

### Implementation for Selective Re-Check

- [x] T044 [P] [US3] Implement selective re-check in `src/specforge/core/quality_gate.py`: add `run_selective_checks(failed_checkers: tuple[str, ...], changed_files: list[Path], service_context: ServiceContext) -> Result[QualityGateResult, str]` — runs only the named failed checkers plus all other checkers as regression detectors; returns QualityGateResult with regression flag if a previously-passing checker now fails

**Checkpoint**: Full retry loop with 3-attempt budget, progressive context, regression detection, selective re-check, and git revert on regression.

---

## Phase 6: User Story 4 — Diagnostic Report on Escalation (Priority: P2)

**Goal**: Structured diagnostic report when auto-fix exhausts all 3 attempts, helping developers quickly identify root cause and manual next steps.

**Independent Test**: Trigger 3-attempt exhaustion and verify generated report contains all required sections with accurate per-attempt timeline.

### Tests for Diagnostic Reporter ⚠️

- [x] T045 [US4] Write tests for DiagnosticReporter in `tests/unit/test_diagnostic_reporter.py`: test report includes original error with full output; test report includes all 3 FixAttempt records with changes and results; test report includes still-failing check names; test suggested steps are category-specific (DOCKER → "Check Dockerfile layer order", BOUNDARY → "Refactor through module interface"); test report rendered via diagnostic-report.md.j2 template; test report written to `.specforge/features/<slug>/diagnostic-<task-id>.md`

### Implementation for Diagnostic Reporter

- [x] T046 [US4] Implement DiagnosticReporter in `src/specforge/core/diagnostic_reporter.py`: constructor accepts TemplateRenderer; `generate(task_id: str, original_error: QualityGateResult, attempts: tuple[FixAttempt, ...]) -> Result[DiagnosticReport, str]` builds DiagnosticReport dataclass with category-specific suggested steps; `render(report: DiagnosticReport, output_dir: Path) -> Result[Path, str]` renders via Jinja2 template and writes to output directory

### Integration with AutoFixEngine

- [x] T047 [US4] Integrate DiagnosticReporter into AutoFixEngine in `src/specforge/core/auto_fix_engine.py`: when retry loop exhausts all attempts, call `DiagnosticReporter.generate()` and `DiagnosticReporter.render()`, include rendered report path in the Err return value so the executor can surface it to the developer

**Checkpoint**: Diagnostic reports generated on auto-fix exhaustion with full timeline, category-specific suggestions, and rendered Markdown output.

---

## Phase 7: User Story 5 — Prompt Rule Compliance Checking (Priority: P3)

**Goal**: Quality gate verifies generated code satisfies governance prompt file rules using the two-tier approach (automated threshold checks + delegated descriptive rules).

**Independent Test**: Configure prompt rules with specific thresholds and verify the quality gate enforces them.

### Tests for Prompt Rule Compliance ⚠️

- [x] T048 [P] [US5] Write tests for threshold mapping registry in `tests/unit/checkers/test_prompt_rule_checker.py` (extend): test `max_function_lines` threshold maps to LineLimitChecker with correct limit; test `min_coverage_percent` threshold maps to CoverageChecker with correct threshold; test `max_class_lines` threshold maps to LineLimitChecker class mode; test unknown threshold key logged as warning and added to Tier 2 context; test multiple thresholds from different governance domains resolved by precedence order

### Implementation for Threshold Mapping

- [x] T049 [P] [US5] Implement threshold mapping registry in `src/specforge/core/checkers/prompt_rule_checker.py` (extend): `THRESHOLD_KEY_MAPPING` maps known threshold keys to checker factory functions; `_apply_thresholds()` iterates all PromptThreshold entries, invokes mapped checker or collects as Tier 2; Tier 2 rules returned as `tier2_context: str` field on CheckResult for inclusion in AI agent prompts

### Tier 2 Context Integration

- [x] T050 [US5] Write tests for Tier 2 context integration in `tests/unit/test_auto_fix_engine.py` (extend): test fix prompt includes Tier 2 descriptive rules as additional context when PromptRuleChecker provides them; test Tier 2 rules not enforced (check passes even if descriptive rules might be violated)
- [x] T051 [US5] Implement Tier 2 context integration in `src/specforge/core/auto_fix_engine.py` (extend): when generating fix prompts, extract Tier 2 context from PromptRuleChecker's CheckResult and append to the fix prompt template context as `governance_context` variable

**Checkpoint**: Prompt rule compliance fully operational — Tier 1 thresholds automated, Tier 2 rules included as AI context.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Backward compatibility shims, integration tests, and final validation.

### Backward Compatibility Shims

- [x] T052 Write tests for QualityChecker backward-compat shim in `tests/unit/test_quality_checker.py` (extend existing): test `QualityChecker(project_root, service_slug)` constructor still works; test `check(changed_files)` returns `Result[QualityCheckResult, str]` with correct field mapping (build_output, lint_output, test_output, failed_checks, is_regression); test `detect_regression(before, after)` static method still works; test existing Feature 009 test assertions still pass without modification
- [x] T053 Modify `src/specforge/core/quality_checker.py` to delegate to QualityGate: constructor creates internal QualityGate instance by building a minimal ServiceContext from project_root + service_slug (reads architecture from `.specforge/manifest.json`, defaults to "monolithic" if absent); `check()` calls `gate.run_task_checks()` and converts `QualityGateResult` → `QualityCheckResult` using backward-compat mapping from data-model.md; `detect_regression()` delegates to QualityGateResult comparison
- [x] T054 Write tests for AutoFixLoop backward-compat shim in `tests/unit/test_auto_fix_loop.py` (extend existing): test `AutoFixLoop(task_runner, quality_checker, max_attempts)` constructor still works; test `fix(original_prompt, error, changed_files, mode)` returns `Result[list[Path], str]` with same interface; test Err return contains richer diagnostic info than before; test existing Feature 009 test assertions still pass
- [x] T055 Modify `src/specforge/core/auto_fix_loop.py` to delegate to AutoFixEngine: constructor creates internal AutoFixEngine with QualityGate from quality_checker; `fix()` converts QualityCheckResult → QualityGateResult, calls engine.fix(), returns Result with diagnostic path on Err

### Integration Tests

- [x] T056 Write integration test for full quality gate pipeline in `tests/integration/test_quality_gate_integration.py`: test end-to-end with intentionally broken Python file (syntax error) → BuildChecker catches it → AutoFixEngine generates targeted SYNTAX prompt; test with lint violation → LintChecker catches → targeted LINT prompt with rule ID; test with microservice architecture → DockerChecker runs; test with monolithic architecture → DockerChecker skipped; test with modular-monolith → BoundaryChecker runs
- [x] T057 Write integration test for auto-fix retry loop in `tests/integration/test_quality_gate_integration.py` (extend): test 3-attempt exhaustion produces DiagnosticReport with all sections; test regression detection reverts and retries; test successful fix on attempt 2 returns all changed files
- [x] T058 Write integration test for SubAgentExecutor compatibility in `tests/integration/test_quality_gate_integration.py` (extend): test SubAgentExecutor with new QualityChecker shim produces same behavior as old; test auto-fix loop integration via AutoFixLoop shim; verify existing executor tests continue to pass

### Final Validation

- [x] T059 Run full test suite (`python -m pytest tests/ -v --tb=short`) and verify all existing Feature 009 tests pass alongside new Feature 010 tests
- [x] T060 Run ruff lint check on all new files (`ruff check src/specforge/core/quality_gate.py src/specforge/core/auto_fix_engine.py src/specforge/core/diagnostic_reporter.py src/specforge/core/quality_models.py src/specforge/core/quality_report.py src/specforge/core/checkers/ src/specforge/core/analyzers/`) and fix any violations
- [x] T061 Verify code coverage for all new modules meets 100% (`python -m pytest --cov=src/specforge/core/quality_gate --cov=src/specforge/core/auto_fix_engine --cov=src/specforge/core/diagnostic_reporter --cov=src/specforge/core/quality_models --cov=src/specforge/core/checkers --cov=src/specforge/core/analyzers --cov-report=term-missing`)
- [x] T062 [P] Write performance benchmark test in `tests/integration/test_quality_gate_performance.py`: run full standard-checker quality gate against a representative test project, assert wall-clock time < 120 seconds (SC-005); use `time.monotonic()` and `@pytest.mark.slow` marker

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — 11 checkers + QualityGate orchestrator
- **US2 (Phase 4)**: Depends on Phase 3 (needs CheckResult with categories from checkers)
- **US3 (Phase 5)**: Depends on Phase 4 (extends AutoFixEngine with retry loop)
- **US4 (Phase 6)**: Depends on Phase 5 (integrates with retry loop exhaustion)
- **US5 (Phase 7)**: Depends on Phase 2 only — can run in PARALLEL with US3/US4
- **Polish (Phase 8)**: Depends on all user stories

### User Story Dependencies

```text
Phase 1 (Setup)
  → Phase 2 (Foundational)
    → Phase 3 (US1: Quality Gate) ──→ Phase 4 (US2: Auto-Fix) ──→ Phase 5 (US3: Retry) ──→ Phase 6 (US4: Diagnostic)
    → Phase 7 (US5: Prompt Rules) — PARALLEL with US3/US4
      → Phase 8 (Polish: Shims + Integration)
```

### Within Each User Story

1. Tests MUST be written and verified FAILING before implementation
2. Models/protocols before checkers
3. Individual checkers before orchestrator
4. Orchestrator before auto-fix engine
5. Core before integration

### Parallel Opportunities

**Phase 2 — Foundational**: T003, T005, T007, T009, T010 all [P] — different files
**Phase 3 — All 11 Checker test+impl pairs**: T011–T032 all [P] — each checker is an independent file pair
**Phase 3 — QualityGate + Report**: T033–T036 after checkers complete
**Phase 4 — Fix strategies**: T039–T040 [P] with T037–T038
**Phase 5 — Selective re-check**: T044 [P] with T041–T043
**Phase 7 — Prompt rules**: T048–T049 [P], can run alongside Phase 5/6

---

## Parallel Example: Phase 3 Standard Checkers

```bash
# Launch ALL standard checker test+impl pairs in parallel (8 independent files):
T011+T019: BuildChecker (test_build_checker.py → build_checker.py)
T012+T020: LintChecker (test_lint_checker.py → lint_checker.py)
T013+T021: TestChecker (test_test_checker.py → test_checker.py)
T014+T022: CoverageChecker (test_coverage_checker.py → coverage_checker.py)
T015+T023: LineLimitChecker (test_line_limit_checker.py → line_limit_checker.py)
T016+T024: SecretChecker (test_secret_checker.py → secret_checker.py) [category=SECURITY]
T017+T025: TodoChecker (test_todo_checker.py → todo_checker.py)
T018+T026: PromptRuleChecker (test_prompt_rule_checker.py → prompt_rule_checker.py)

# Then in parallel, the architecture-specific checkers:
T027+T030: DockerBuildChecker (microservice, TASK level)
T027a+T030a: DockerServiceChecker (microservice, SERVICE level)
T028+T031: ContractChecker (microservice only)
T032a+T032b: UrlChecker (microservice only) [FR-014]
T032c+T032d: InterfaceChecker (microservice only) [FR-015, FR-016]
T029+T032: BoundaryChecker (modular-monolith only) [FR-017, FR-018]
T032e+T032f: MigrationChecker (modular-monolith only) [FR-019]
```

---

## Implementation Strategy

### MVP First (US1 Only — Phase 1 + 2 + 3)

1. Complete Phase 1: Setup directories and config constants
2. Complete Phase 2: Data models, protocols, templates
3. Complete Phase 3: All 15 checkers + QualityGate orchestrator
4. **STOP and VALIDATE**: Run quality gate against test projects for all 3 architectures
5. MVP delivers: architecture-aware quality checking with structured results

### Critical Path (US2 — AutoFixEngine)

1. After MVP, immediately tackle Phase 4: AutoFixEngine with error categorization
2. This is the highest-value addition — targeted prompts vs generic "fix the error"
3. Validate with intentionally broken code: syntax errors, lint violations, Docker failures, contract mismatches

### Incremental Delivery

1. **Setup + Foundational** → Framework ready
2. **US1 (Quality Gate)** → Architecture-aware checking (MVP)
3. **US2 (Auto-Fix Categorization)** → Targeted fix prompts
4. **US3 (Retry Budget)** → Progressive 3-attempt loop
5. **US4 (Diagnostic Report)** → Escalation reports
6. **US5 (Prompt Rules)** → Governance compliance (parallel with US3/US4)
7. **Polish** → Backward compat shims + integration tests

---

## Notes

- TDD enforced: Every test task (odd-numbered in phases 3-7) must be completed and verified failing before its paired implementation task
- [P] tasks = different files, no state dependencies — safe to parallelize
- Each checker is independently testable — can verify in isolation before QualityGate integration
- AutoFixEngine error categorization (Phase 4) is the critical path after MVP
- Test with intentionally broken code: create sample .py files with syntax errors, lint violations; mock Docker build failures; mock Pact test output for contract failures
- Backward compat shims (Phase 8) ensure SubAgentExecutor integration is seamless
- All new code must satisfy constitution: ≤30 line functions, ≤200 line classes, type hints, Result[T, E] returns
