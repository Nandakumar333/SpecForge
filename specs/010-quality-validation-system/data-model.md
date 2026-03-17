# Data Model: Quality Validation System

**Feature**: 010-quality-validation-system
**Date**: 2026-03-17

## Entities

### ErrorCategory (Enum)

Classification label for quality check failures, driving targeted fix prompt generation.

**Values**: `SYNTAX`, `LOGIC`, `TYPE`, `LINT`, `COVERAGE`, `DOCKER`, `CONTRACT`, `BOUNDARY`, `SECURITY`

**Relationships**: Each `CheckResult` carries exactly one `ErrorCategory`. The `AutoFixEngine` maps categories to fix prompt strategies.

**Checker → Category Mapping**:
| Checker | Category | Rationale |
|---------|----------|-----------|
| BuildChecker | SYNTAX | Build failures are typically syntax/compilation errors |
| LintChecker | LINT | Direct lint rule violations |
| TestChecker | LOGIC | Test failures indicate logic errors |
| CoverageChecker | COVERAGE | Insufficient test coverage |
| LineLimitChecker | LINT | Structural lint (complexity) |
| SecretChecker | SECURITY | Credential/secret exposure |
| TodoChecker | LINT | Code hygiene lint |
| PromptRuleChecker | LINT | Governance rule compliance |
| DockerBuildChecker | DOCKER | Container image build failures |
| DockerServiceChecker | DOCKER | Container compose/health failures |
| ContractChecker | CONTRACT | Consumer/provider contract failures |
| UrlChecker | BOUNDARY | Hardcoded service URLs violate service boundaries |
| InterfaceChecker | CONTRACT | Proto/schema validation is contract compliance |
| BoundaryChecker | BOUNDARY | Cross-module boundary violations |
| MigrationChecker | BOUNDARY | Shared migration breaks module boundaries |

### ContractAttribution (Enum)

Sub-classification for contract test failures indicating responsibility.

**Values**: `CONSUMER` (our code — auto-fixable), `PROVIDER` (external service — escalate immediately)

**Relationships**: Only used when `ErrorCategory` is `CONTRACT`. Determines whether `AutoFixEngine` attempts a fix or skips to escalation.

### CheckLevel (Enum)

When a checker should run during the execution lifecycle.

**Values**: `TASK` (run after each task), `SERVICE` (run once after all service tasks complete)

### CheckResult (frozen dataclass)

Outcome of a single quality check execution.

**Fields**:
- `checker_name: str` — identifier of the checker that produced this result (e.g., "lint", "docker-build")
- `passed: bool` — whether the check succeeded
- `category: ErrorCategory` — error classification for auto-fix routing
- `output: str` — full stdout/stderr from the check command
- `error_details: tuple[ErrorDetail, ...]` — structured parse of errors (file, line, message)
- `skipped: bool` — True if check was skipped (missing tool, not applicable)
- `skip_reason: str` — why the check was skipped (empty if not skipped)
- `attribution: ContractAttribution | None` — only set for contract checks

**Validation**: `passed` and `skipped` are mutually exclusive in interpretation — a skipped check is neither pass nor fail.

### ErrorDetail (frozen dataclass)

A single structured error extracted from check output.

**Fields**:
- `file_path: str` — affected file (relative to project root)
- `line_number: int | None` — specific line, if available
- `column: int | None` — specific column, if available
- `code: str` — error code or rule ID (e.g., "E501", "SEC-001")
- `message: str` — human-readable error description
- `context: str` — surrounding code or extra context (empty if not available)

### QualityGateResult (frozen dataclass)

Aggregate outcome of running the full check suite for a task or service.

**Fields**:
- `passed: bool` — True only if all non-skipped checks passed
- `check_results: tuple[CheckResult, ...]` — all individual results
- `failed_checks: tuple[str, ...]` — names of checkers that failed
- `skipped_checks: tuple[str, ...]` — names of checkers that were skipped
- `architecture: str` — which architecture type was used for check selection
- `level: CheckLevel` — TASK or SERVICE

**Derived**:
- `has_regressions` — computed by comparing against a prior `QualityGateResult`

### FixAttempt (frozen dataclass)

Record of a single auto-fix iteration for the diagnostic timeline.

**Fields**:
- `attempt_number: int` — 1, 2, or 3
- `category: ErrorCategory` — what kind of error triggered this attempt
- `fix_prompt: str` — the targeted prompt that was generated
- `files_changed: tuple[str, ...]` — files modified by this fix
- `result: QualityGateResult | None` — re-check result after fix
- `reverted: bool` — True if regression detected and fix was rolled back
- `revert_reason: str` — description of regression, if applicable

### DiagnosticReport (frozen dataclass)

Structured escalation document produced when auto-fix exhausts all attempts.

**Fields**:
- `task_id: str` — which task failed
- `original_error: QualityGateResult` — the initial quality gate failure
- `attempts: tuple[FixAttempt, ...]` — full timeline of fix attempts
- `still_failing: tuple[str, ...]` — checks that remain failed after all attempts
- `suggested_steps: tuple[str, ...]` — category-specific manual remediation suggestions
- `created_at: str` — ISO 8601 timestamp

### QualityReport (frozen dataclass)

Persistent JSON report written after each quality gate execution.

**Fields**:
- `schema_version: str` — report format version (e.g., "1.0"), for Feature 012 dashboard forward-compatibility
- `service_slug: str` — which service was checked
- `architecture: str` — architecture type
- `level: str` — "task" or "service"
- `task_id: str | None` — task ID if task-level
- `gate_result: QualityGateResult` — full gate result
- `fix_attempts: tuple[FixAttempt, ...]` — auto-fix history (empty if passed)
- `diagnostic: DiagnosticReport | None` — escalation report, if generated
- `timestamp: str` — ISO 8601

### FunctionInfo (frozen dataclass)

Result of AST analysis for a single function.

**Fields**:
- `name: str` — function name
- `file_path: str` — source file
- `start_line: int` — first line of function
- `end_line: int` — last line of function
- `line_count: int` — total lines (end - start + 1)

### ClassInfo (frozen dataclass)

Result of AST analysis for a single class.

**Fields**:
- `name: str` — class name
- `file_path: str` — source file
- `start_line: int` — first line of class
- `end_line: int` — last line of class
- `line_count: int` — total lines (end - start + 1)

## Protocols

### CheckerProtocol (typing.Protocol)

Structural interface that all quality checkers implement.

**Methods**:
- `check(changed_files: list[Path], service_context: ServiceContext) -> Result[CheckResult, str]`
- `is_applicable(architecture: str) -> bool`

**Properties**:
- `name: str` — unique checker identifier
- `category: ErrorCategory` — error category this checker produces
- `levels: tuple[CheckLevel, ...]` — which levels this checker runs at (TASK, SERVICE, or both)

**Note**: `levels` is a tuple (not single value) because some checkers run at both levels. For example, DockerBuildChecker runs at TASK level (per-task incremental check) while DockerServiceChecker runs at SERVICE level (full verification). The QualityGate filters checkers by requested level at runtime.

### ModuleBoundaryConfig (frozen dataclass)

Defines module boundaries for BoundaryChecker and MigrationChecker detection.

**Fields**:
- `modules: dict[str, ModuleDefinition]` — map of module name to boundary definition

**ModuleDefinition (frozen dataclass)**:
- `boundary_paths: tuple[str, ...]` — directory paths that constitute this module (e.g., `("src/orders/",)`)
- `public_interfaces: tuple[str, ...]` — files/patterns that define the module's public API (e.g., `("src/orders/api.py", "src/orders/interfaces/")`)
- `data_patterns: tuple[str, ...]` — patterns that indicate data access (e.g., `("**/models.py", "**/repositories/")`)

**Source**: Read from `.specforge/manifest.json` under a `modules` key. If absent, BoundaryChecker falls back to directory-convention-based detection: top-level directories under `src/` are treated as modules, files named `__init__.py`, `api.py`, or in `interfaces/` directories are treated as public interfaces.

### LanguageAnalyzerProtocol (typing.Protocol)

Pluggable interface for language-specific code structure analysis.

**Methods**:
- `analyze_functions(file_path: Path) -> Result[tuple[FunctionInfo, ...], str]`
- `analyze_classes(file_path: Path) -> Result[tuple[ClassInfo, ...], str]`
- `supports_extension(ext: str) -> bool`

## Relationships

```text
QualityGate
  ├── has many → CheckerProtocol implementations
  ├── produces → QualityGateResult
  └── reads → ServiceContext (architecture type)

AutoFixEngine
  ├── consumes → QualityGateResult (categorized failures)
  ├── produces → FixAttempt (per retry)
  ├── produces → DiagnosticReport (on exhaustion)
  └── delegates to → TaskRunner (for fix execution)

QualityGateResult
  ├── contains many → CheckResult
  └── each CheckResult contains many → ErrorDetail

DiagnosticReport
  ├── contains → QualityGateResult (original error)
  └── contains many → FixAttempt (timeline)

QualityReport
  ├── wraps → QualityGateResult
  ├── wraps → tuple[FixAttempt]
  └── wraps → DiagnosticReport | None

LineLimitChecker
  └── delegates to → LanguageAnalyzerProtocol
      └── PythonAnalyzer implements LanguageAnalyzerProtocol
```

## State Transitions

### CheckResult Lifecycle

```
PENDING → RUNNING → PASSED | FAILED | SKIPPED
```

### Auto-Fix Lifecycle

```
QUALITY_FAILED
  → ATTEMPT_1 → (RE_CHECK)
    → PASSED: done
    → REGRESSION: revert → ATTEMPT_2
    → SAME_ERROR: ATTEMPT_2
  → ATTEMPT_2 → (RE_CHECK)
    → PASSED: done
    → REGRESSION: revert → ATTEMPT_3
    → SAME_ERROR: ATTEMPT_3
  → ATTEMPT_3 → (RE_CHECK)
    → PASSED: done
    → FAILED: ESCALATE → DiagnosticReport
```

## Backward Compatibility Mapping

The new `QualityGateResult` must map to the existing `QualityCheckResult`:

| Old Field (QualityCheckResult) | New Source |
|-------------------------------|-----------|
| `passed: bool` | `QualityGateResult.passed` |
| `build_output: str` | `CheckResult` where `checker_name == "build"` → `.output` |
| `lint_output: str` | `CheckResult` where `checker_name == "lint"` → `.output` |
| `test_output: str` | `CheckResult` where `checker_name == "test"` → `.output` |
| `failed_checks: tuple[str, ...]` | `QualityGateResult.failed_checks` |
| `is_regression: bool` | Computed by comparing two `QualityGateResult` objects |
