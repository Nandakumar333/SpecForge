# Implementation Plan: Quality Validation System

**Branch**: `010-quality-validation-system` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-quality-validation-system/spec.md`

## Summary

Replace the thin-wrapper `QualityChecker` (build/lint/test only) and generic `AutoFixLoop` from Feature 009 with a full architecture-aware quality validation system. The new system introduces a pluggable checker protocol (`CheckerProtocol`), an orchestrating `QualityGate` that selects checkers by architecture type, a categorizing `AutoFixEngine` that generates targeted fix prompts per error category, and a `DiagnosticReporter` for structured escalation reports. 11 concrete checker implementations cover standard checks (build, lint, test, coverage, line-limit, secrets, TODO scan, prompt-rule compliance) plus architecture-specific checks (Docker, contract, boundary). All file output flows through Jinja2 templates per constitution.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal output), Jinja2 3.x (template rendering), PyYAML 6.x (pattern files) — all existing
**Storage**: File system — `.specforge/features/<slug>/` for quality reports; `.quality-report.json` per service
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting) — all existing
**Target Platform**: Cross-platform (Windows, macOS, Linux)
**Project Type**: CLI tool (Python package)
**Performance Goals**: Standard quality gate (build + lint + test + analysis) completes within 2 minutes for a typical project
**Constraints**: Functions ≤30 lines, classes ≤200 lines, 100% unit test coverage for core domain, `Result[T, E]` for recoverable errors, constructor injection, no global state
**Scale/Scope**: 11 checker implementations, 1 orchestrator, 1 auto-fix engine, 1 diagnostic reporter, ~15 new source files, ~15 new test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First | ✅ PASS | spec.md complete with clarifications; plan.md in progress |
| II. Architecture | ✅ PASS | All new code in `src/specforge/core/` (domain logic, zero external deps). Jinja2 templates for diagnostic report output. Plugin interface for language analyzers. |
| III. Code Quality | ✅ PASS | Type hints required, ≤30 line functions, ≤200 line classes, `Result[T, E]` returns, constructor injection, constants in `config.py` |
| IV. Testing | ✅ PASS | TDD: tests written before implementations. Unit tests for all checkers. Integration tests for QualityGate + AutoFixEngine orchestration. |
| V. Commit Strategy | ✅ PASS | One commit per task, Conventional Commits format |
| VI. File Structure | ✅ PASS | New `checkers/` subpackage under `core/` — domain logic layer. Tests mirror source structure. |
| VII. Governance | ✅ PASS | No conflicts with constitution. Governance prompt rules are the *target project's* standards, not SpecForge's own. |

## Project Structure

### Documentation (this feature)

```text
specs/010-quality-validation-system/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── quality-gate-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/specforge/core/
├── quality_checker.py           # MODIFY: becomes backward-compat shim → delegates to QualityGate
├── auto_fix_loop.py             # MODIFY: becomes backward-compat shim → delegates to AutoFixEngine
├── quality_gate.py              # NEW: orchestrates checkers per architecture
├── auto_fix_engine.py           # NEW: error categorization + targeted fix prompts
├── diagnostic_reporter.py       # NEW: structured escalation reports
├── quality_models.py            # NEW: CheckResult, QualityGateResult, ErrorCategory, etc.
├── quality_report.py            # NEW: .quality-report.json writer/reader
├── checkers/
│   ├── __init__.py              # NEW: CheckerProtocol + registry
│   ├── build_checker.py         # NEW: project build verification
│   ├── lint_checker.py          # NEW: ruff/eslint with structured output
│   ├── test_checker.py          # NEW: pytest/dotnet test runner
│   ├── coverage_checker.py      # NEW: threshold from testing.prompts.md
│   ├── line_limit_checker.py    # NEW: AST function/class line analysis
│   ├── secret_checker.py        # NEW: regex + entropy secret detection
│   ├── todo_checker.py          # NEW: TODO/FIXME/HACK scanner
│   ├── prompt_rule_checker.py   # NEW: Feature 003 threshold compliance
│   ├── docker_checker.py        # NEW: Docker build check (TASK level, microservice)
│   ├── docker_service_checker.py # NEW: Compose start + health check (SERVICE level, microservice)
│   ├── contract_checker.py      # NEW: Pact consumer tests (microservice)
│   ├── url_checker.py           # NEW: Hardcoded service URL detection (microservice) [FR-014]
│   ├── interface_checker.py     # NEW: Proto compile + event schema validation (microservice) [FR-015, FR-016]
│   ├── boundary_checker.py      # NEW: module boundary (modular-monolith) [FR-017, FR-018]
│   └── migration_checker.py     # NEW: shared migration safety (modular-monolith) [FR-019]
└── analyzers/
    ├── __init__.py              # NEW: LanguageAnalyzerProtocol
    └── python_analyzer.py       # NEW: Python ast module analysis

src/specforge/templates/base/executor/
├── fix-prompt.md.j2             # NEW: targeted fix prompt template
└── diagnostic-report.md.j2      # NEW: escalation report template

tests/unit/
├── test_quality_gate.py         # NEW
├── test_auto_fix_engine.py      # NEW
├── test_diagnostic_reporter.py  # NEW
├── test_quality_models.py       # NEW
├── test_quality_report.py       # NEW
├── checkers/
│   ├── __init__.py
│   ├── test_build_checker.py    # NEW
│   ├── test_lint_checker.py     # NEW
│   ├── test_test_checker.py     # NEW
│   ├── test_coverage_checker.py # NEW
│   ├── test_line_limit_checker.py # NEW
│   ├── test_secret_checker.py   # NEW
│   ├── test_todo_checker.py     # NEW
│   ├── test_prompt_rule_checker.py # NEW
│   ├── test_docker_checker.py   # NEW
│   ├── test_docker_service_checker.py # NEW
│   ├── test_contract_checker.py # NEW
│   ├── test_url_checker.py      # NEW [FR-014]
│   ├── test_interface_checker.py # NEW [FR-015, FR-016]
│   ├── test_boundary_checker.py # NEW [FR-017, FR-018]
│   └── test_migration_checker.py # NEW [FR-019]
└── analyzers/
    ├── __init__.py
    └── test_python_analyzer.py  # NEW

tests/integration/
└── test_quality_gate_integration.py  # NEW: end-to-end gate with mocked subprocess
```

**Structure Decision**: New `checkers/` and `analyzers/` subpackages under `src/specforge/core/` for the pluggable checker system. The existing `quality_checker.py` and `auto_fix_loop.py` become thin shims delegating to the new modules, preserving backward compatibility with Feature 009's `SubAgentExecutor`.

## Complexity Tracking

> No constitution violations identified. All new code fits within existing architectural boundaries.
