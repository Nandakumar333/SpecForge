# Research: Quality Validation System

**Feature**: 010-quality-validation-system
**Date**: 2026-03-17

## R1: Checker Protocol Pattern

**Decision**: Use `typing.Protocol` (structural subtyping) rather than ABC for the checker interface.

**Rationale**: SpecForge already uses ABC for plugin boundaries (AgentPlugin, BasePhase) where registration and explicit inheritance are needed. Checkers are internal domain objects where structural typing is simpler — any class with the right methods qualifies. This avoids requiring explicit inheritance for 15 concrete implementations and is consistent with Python 3.11+ best practices for internal interfaces.

**Alternatives considered**:
- ABC with `@abstractmethod`: Adds import overhead and forces explicit inheritance. Better for public plugin APIs, overkill for internal checkers.
- Plain duck typing: No static type checking support. Protocol gives us the best of both worlds.

## R2: Backward Compatibility Strategy

**Decision**: Keep existing `QualityChecker` and `AutoFixLoop` classes as thin facades delegating to the new `QualityGate` and `AutoFixEngine`. The `SubAgentExecutor` continues calling the same interfaces unchanged.

**Rationale**: Feature 009's executor (`SubAgentExecutor`) instantiates `QualityChecker(project_root, service_slug)` and calls `checker.check(changed_files) → Result[QualityCheckResult, str]`. The auto-fix calls `auto_fix.fix(prompt, error, changed_files, mode) → Result[list[Path], str]`. Both signatures must be preserved. Internally, the shim converts the old `QualityCheckResult` to the new `QualityGateResult` and back.

**Alternatives considered**:
- Modify SubAgentExecutor directly: Higher risk, violates single-feature scope. Feature 009 is complete and tested.
- Create new interface and update executor: Breaking change. Better to do this as a follow-up.

## R3: Error Categorization Approach

**Decision**: Each checker declares its own error category via a class attribute. The `AutoFixEngine` uses the category from the `CheckResult` directly — no separate parsing step needed.

**Rationale**: The error category is inherent to the checker type (lint checker → "lint", docker checker → "docker"). Attempting to categorize by parsing arbitrary error output is fragile and error-prone. Instead, the checker already knows what kind of errors it produces. The `AutoFixEngine` receives `CheckResult` objects that carry their category, making categorization trivial.

**Alternatives considered**:
- Post-hoc error classifier: Parse error text with regex/heuristics to determine category. Fragile, requires maintaining regex patterns for every tool's output format.
- ML-based classifier: Massive complexity for marginal benefit. The checker already knows its own category.

## R4: Secrets Detection Strategy

**Decision**: Regex pattern matching for common credential patterns (AWS keys, API tokens, connection strings, private keys) plus Shannon entropy analysis for high-entropy strings that might be secrets. No external dependency needed.

**Rationale**: External tools (detect-secrets, gitleaks, trufflehog) would add dependencies the constitution prohibits for core domain logic (zero external deps). Python stdlib `re` and `math` (for entropy) are sufficient for the most common patterns. False positive rate is managed by tuning entropy thresholds and exempting test fixtures.

**Alternatives considered**:
- `detect-secrets` library: External dependency, violates core zero-deps constraint.
- `gitleaks` subprocess: Requires external tool installation, unreliable across platforms.
- Only regex patterns: Misses novel credential formats. Entropy adds a safety net.

## R5: AST Analysis for Line Limits (Python-Only)

**Decision**: Use Python's `ast` module to parse changed `.py` files, walk the AST for `FunctionDef`/`AsyncFunctionDef` and `ClassDef` nodes, compute line spans using `node.lineno` and `node.end_lineno`.

**Rationale**: The `ast` module is stdlib, zero dependencies, and gives exact line numbers. Regex-based line counting is fragile for nested definitions and decorators. The spec requires a pluggable `LanguageAnalyzerProtocol` for future language support — Python-first with the interface in place.

**Alternatives considered**:
- Regex line counting: Doesn't handle nested classes, multi-line decorators, or continuations.
- Tree-sitter: External dependency. Better left as a future plugin.
- `tokenize` module: Gives tokens, not structure. More work for the same result.

## R6: Contract Test Runner Attribution

**Decision**: Parse Pact test output for consumer vs provider attribution. Pact consumer tests run locally (our code, auto-fixable). Provider verification failures come from schema mismatches against published contracts (external, not auto-fixable).

**Rationale**: Consumer tests exercise *our* code against *their* contract — failures are our fault. Provider tests verify *their* code against *our* expectations — failures mean they changed. The spec requires immediate escalation (no auto-fix) for provider-attributed failures.

**Detection heuristic**: If the contract test runner produces "Consumer test failed" or Pact broker reports consumer mismatch → `consumer`. If the error references "Provider verification failed" or "unexpected provider response" → `provider`.

## R7: Docker Check Scoping

**Decision**: Maintain a set of container-relevant path patterns: `Dockerfile*`, `docker-compose*.yml`, `.dockerignore`, `requirements.txt` (if referenced in Dockerfile), `package.json` (if referenced), `*.csproj` (for .NET). Compare changed file paths against these patterns to decide whether to run Docker checks per-task. Full verification runs once after all service tasks complete regardless.

**Rationale**: Docker builds are expensive (30-60s). Running after every task wastes time when most tasks don't affect the container. The spec explicitly requires scoping Docker checks to container-relevant file changes. The "final full verification" covers the case where incremental checks miss a cumulative issue.

## R8: Prompt Rule Compliance — Threshold Mapping

**Decision**: Build a static registry mapping `PromptThreshold.key` values to checker classes. Known mappings:
- `max_function_lines` → `LineLimitChecker` (function mode)
- `max_class_lines` → `LineLimitChecker` (class mode)
- `min_coverage_percent` → `CoverageChecker`
- `max_lines` → generic line count check

Unknown threshold keys are logged as warnings and included as Tier 2 context for the AI agent.

**Rationale**: The spec's two-tier approach means only threshold-based rules get automated enforcement. The threshold key namespace is defined by Feature 003's prompt files. A static registry is simpler and more predictable than dynamic dispatch.

## R9: Diagnostic Report Format

**Decision**: Render diagnostic reports via a Jinja2 template (`diagnostic-report.md.j2`) producing Markdown output. The report includes: original error, attempt timeline, per-attempt diffs, remaining failures, and suggested manual remediation keyed by error category.

**Rationale**: Constitution mandates Jinja2 for all file generation. Markdown is human-readable and can be rendered in terminals via Rich. The report is written to `.specforge/features/<slug>/diagnostic-<task-id>.md`.

## R10: Selective Re-Check Strategy

**Decision**: After a fix attempt, re-run only the checkers that failed in the previous round, plus all previously-passing checkers as a regression check. If a regression is detected (a previously-passing checker now fails), revert the fix.

**Rationale**: Running all 15 checkers after every fix attempt is wasteful. The spec requires (FR-026) re-running only failed checks plus regression detection on passing checks. The regression check is lightweight — most checkers complete in seconds for small file sets.

## R11: Quality Report Persistence

**Decision**: Write a `.quality-report.json` file per service after each quality gate run. Contains: timestamp, architecture, all check results (pass/fail, output summary, error category), overall gate status, and any fix attempts. Read by the executor to decide next action.

**Rationale**: Structured JSON enables tooling (CI dashboards, aggregation scripts) to consume quality gate results. The file is ephemeral — overwritten each run, not version-controlled.

## R12: SECURITY Error Category

**Decision**: Add `SECURITY` to the ErrorCategory enum (9 total values). SecretChecker uses `SECURITY` category instead of `SYNTAX`. AutoFixEngine includes a `_security_strategy()` that instructs removal of detected secrets and their replacement with environment variables or config references.

**Rationale**: Secrets detection is fundamentally different from syntax errors. Using SYNTAX would cause the auto-fix engine's `_syntax_strategy()` to produce inappropriate guidance (e.g., "fix the compilation error" when the actual issue is an exposed API key). A dedicated SECURITY category enables targeted fix prompts that say "Remove this hardcoded secret and replace with `os.environ['KEY']`" or "Move this credential to .env and load via config."

## R13: DockerChecker Split (Build vs Service)

**Decision**: Split the original single DockerChecker into two separate checkers: `DockerBuildChecker` (TASK level — runs per-task when changed files intersect container-relevant paths) and `DockerServiceChecker` (SERVICE level — runs once after all tasks, verifies compose start + health check).

**Rationale**: The CheckerProtocol's `levels` property determines when a checker runs. A single checker cannot be both TASK and SERVICE simultaneously without dual-instance complexity. Splitting produces cleaner code: DockerBuildChecker focuses on `docker build` with error parsing, DockerServiceChecker focuses on `docker-compose up` + HTTP health check. Each has clear, testable responsibilities.

## R14: Module Boundary Discovery

**Decision**: Module boundaries for BoundaryChecker and MigrationChecker are defined in `.specforge/manifest.json` under a `modules` key. If absent, fall back to directory-convention detection: top-level directories under `src/` are treated as modules, files named `__init__.py`, `api.py`, or in `interfaces/` directories are treated as public interfaces.

**Rationale**: Explicit manifest-based boundaries are more accurate for real projects. Directory conventions provide a reasonable default for projects that don't configure boundaries. This mirrors how BoundaryChecker works in tools like ArchUnit (Java) and NDepend (.NET) — explicit rules with convention-based fallback.

## R15: Backward-Compat Shim ServiceContext Construction

**Decision**: The `QualityChecker` backward-compat shim constructs a minimal `ServiceContext` by reading architecture type from `.specforge/manifest.json` (defaults to "monolithic" if absent). The shim does NOT require callers to pass a ServiceContext — it builds one internally from `project_root` + `service_slug`.

**Rationale**: The existing `QualityChecker(project_root, service_slug)` constructor has no `ServiceContext` parameter, and Feature 009's `SubAgentExecutor` doesn't pass one. The shim must bridge this gap by constructing the context internally. Reading manifest.json is the same mechanism QualityGate uses, so the shim delegates consistently.
