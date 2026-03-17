# Quickstart: Quality Validation System

**Feature**: 010-quality-validation-system
**Date**: 2026-03-17

## What This Feature Does

Replaces the thin quality checker (build + lint + test) and generic auto-fix loop from Feature 009 with a full architecture-aware quality validation system. After implementing this feature, the executor automatically runs the right set of quality checks based on the project's architecture type and generates targeted fix prompts when checks fail.

## Key Concepts

1. **CheckerProtocol**: Each quality check is a standalone checker conforming to a common protocol. Checkers declare which architecture types they apply to.
2. **QualityGate**: Orchestrator that selects applicable checkers, runs them, and aggregates results into a `QualityGateResult`.
3. **AutoFixEngine**: Categorizes failures and generates targeted fix prompts (not generic "fix the error").
4. **DiagnosticReporter**: Produces human-readable reports when auto-fix exhausts its 3-attempt budget.

## Development Workflow

### Adding a New Checker

1. Create `src/specforge/core/checkers/my_checker.py`
2. Implement `CheckerProtocol`: `name`, `category`, `level`, `check()`, `is_applicable()`
3. Register in `checkers/__init__.py` → `ALL_CHECKERS` tuple
4. Create `tests/unit/checkers/test_my_checker.py` (TDD: test first)
5. Run: `python -m pytest tests/unit/checkers/test_my_checker.py -v`

### Running the Quality Gate Locally

```bash
# Run all tests (includes quality gate tests)
python -m pytest tests/ -v

# Run only quality gate unit tests
python -m pytest tests/unit/test_quality_gate.py -v

# Run all checker unit tests
python -m pytest tests/unit/checkers/ -v

# Run integration tests
python -m pytest tests/integration/test_quality_gate_integration.py -v

# Lint check
ruff check src/specforge/core/quality_gate.py src/specforge/core/checkers/
```

### Key File Locations

| File | Purpose |
|------|---------|
| `src/specforge/core/quality_models.py` | All data models (CheckResult, QualityGateResult, etc.) |
| `src/specforge/core/quality_gate.py` | Orchestrator — entry point for running checks |
| `src/specforge/core/checkers/__init__.py` | CheckerProtocol definition + registry |
| `src/specforge/core/auto_fix_engine.py` | Error categorization + targeted fix prompts |
| `src/specforge/core/diagnostic_reporter.py` | Escalation report generator |
| `src/specforge/core/quality_checker.py` | Backward-compat shim (delegates to QualityGate) |
| `src/specforge/core/auto_fix_loop.py` | Backward-compat shim (delegates to AutoFixEngine) |

### How It Integrates with Feature 009

The `SubAgentExecutor` continues calling the existing `QualityChecker` and `AutoFixLoop` interfaces. Those classes now internally delegate to the new system:

```text
SubAgentExecutor
  → QualityChecker.check(files)        # same old interface
    → QualityGate.run_task_checks()    # new internal implementation
    → converts QualityGateResult → QualityCheckResult  # backward compat
  → AutoFixLoop.fix(prompt, error, ...)  # same old interface
    → AutoFixEngine.fix(...)             # new internal implementation
```
