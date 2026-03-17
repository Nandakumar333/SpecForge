# Quality Gate Contract

**Feature**: 010-quality-validation-system
**Date**: 2026-03-17

## Internal Interfaces

This feature is internal to SpecForge — no external-facing APIs. The contracts below define how the new quality validation modules integrate with the existing executor (Feature 009).

### Contract 1: QualityChecker Backward-Compatible Interface

The existing `SubAgentExecutor` calls `QualityChecker` via:

```text
Instantiation:
  checker = quality_checker_factory(project_root: Path, service_slug: str) → QualityChecker

Check invocation:
  result = checker.check(changed_files: list[Path]) → Result[QualityCheckResult, str]

Regression detection:
  is_regression = QualityChecker.detect_regression(before: QualityCheckResult, after: QualityCheckResult) → bool
```

**Guarantee**: The new implementation preserves this exact interface. `QualityChecker.__init__` and `.check()` signatures remain identical. Internally, `QualityChecker` delegates to `QualityGate` and converts `QualityGateResult` → `QualityCheckResult`.

### Contract 2: AutoFixLoop Backward-Compatible Interface

The existing `SubAgentExecutor` calls `AutoFixLoop` via:

```text
Instantiation:
  auto_fix = AutoFixLoop(task_runner: TaskRunner, quality_checker: QualityChecker, max_attempts: int = 3)

Fix invocation:
  result = auto_fix.fix(
      original_prompt: ImplementPrompt,
      error: QualityCheckResult,
      changed_files: list[Path],
      mode: ExecutionMode,
  ) → Result[list[Path], str]
```

**Guarantee**: The new implementation preserves this exact interface. `AutoFixLoop` delegates to `AutoFixEngine` internally. The `Err` return value on exhaustion now contains a richer diagnostic summary.

### Contract 3: CheckerProtocol (New Internal Interface)

All 15 checker implementations must conform to:

```text
Protocol:
  name: str (property)           — unique checker identifier
  category: ErrorCategory (property) — error type for auto-fix routing
  levels: tuple[CheckLevel, ...] (property) — which levels this checker runs at

  check(
      changed_files: list[Path],
      service_context: ServiceContext,
  ) → Result[CheckResult, str]

  is_applicable(architecture: str) → bool
```

**Applicability rules by architecture**:

| Checker | Category | monolithic | microservice | modular-monolith | Level(s) |
|---------|----------|-----------|-------------|-----------------|----------|
| build | SYNTAX | ✅ | ✅ | ✅ | TASK |
| lint | LINT | ✅ | ✅ | ✅ | TASK |
| test | LOGIC | ✅ | ✅ | ✅ | TASK |
| coverage | COVERAGE | ✅ | ✅ | ✅ | TASK |
| line-limit | LINT | ✅ | ✅ | ✅ | TASK |
| secret | SECURITY | ✅ | ✅ | ✅ | TASK |
| todo | LINT | ✅ | ✅ | ✅ | TASK |
| prompt-rule | LINT | ✅ | ✅ | ✅ | TASK |
| docker-build | DOCKER | ❌ | ✅ | ❌ | TASK |
| docker-service | DOCKER | ❌ | ✅ | ❌ | SERVICE |
| contract | CONTRACT | ❌ | ✅ | ❌ | SERVICE |
| url | BOUNDARY | ❌ | ✅ | ❌ | TASK |
| interface | CONTRACT | ❌ | ✅ | ❌ | SERVICE |
| boundary | BOUNDARY | ❌ | ❌ | ✅ | TASK |
| migration | BOUNDARY | ❌ | ❌ | ✅ | TASK |

### Contract 4: LanguageAnalyzerProtocol (New Plugin Interface)

Language-specific code analyzers for the line-limit checker:

```text
Protocol:
  analyze_functions(file_path: Path) → Result[tuple[FunctionInfo, ...], str]
  analyze_classes(file_path: Path) → Result[tuple[ClassInfo, ...], str]
  supports_extension(ext: str) → bool
```

**Initial implementation**: `PythonAnalyzer` supports `.py` extension only.
**Extension point**: Future analyzers register for other extensions (`.cs`, `.ts`, etc.).

### Contract 5: QualityGate Orchestration Interface

New interface for direct use (bypassing backward-compat shim):

```text
Instantiation:
  gate = QualityGate(
      architecture: str,
      project_root: Path,
      service_slug: str,
      prompt_loader: PromptLoader | None,
      checkers: tuple[CheckerProtocol, ...] | None,  # None = auto-register all
  )

Task-level check:
  result = gate.run_task_checks(
      changed_files: list[Path],
      service_context: ServiceContext,
  ) → Result[QualityGateResult, str]

Service-level check:
  result = gate.run_service_checks(
      service_context: ServiceContext,
  ) → Result[QualityGateResult, str]
```
