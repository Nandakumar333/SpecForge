# Feature Specification: Quality Validation System

**Feature Branch**: `010-quality-validation-system`  
**Created**: 2026-03-17  
**Status**: Draft  
**Input**: User description: "Build the quality validation system. Replaces the thin wrappers in Feature 009."

## Clarifications

### Session 2026-03-17

- Q: Should AST analysis for function/class line count support multiple languages or just Python initially? → A: Python-only initially via the `ast` module, with a pluggable language analyzer interface so additional parsers (e.g., Roslyn for .NET, Tree-sitter for polyglot) can be added later without changing the check framework. Other languages are unsupported (skipped with a warning) until a parser plugin is registered.
- Q: How should contract test failures be categorized when the error is in the provider (other service) not the consumer? → A: Always categorize as "contract". Include a sub-attribution field: "consumer" (our code is wrong — auto-fixable) vs "provider" (external service changed — not auto-fixable, escalate immediately with diagnostic report noting the external dependency change). Auto-fix attempts are only made for consumer-attributed failures.
- Q: Should the quality gate run Docker/container checks after every task or only after tasks that modify container-relevant files? → A: Only after tasks whose changed files intersect container-relevant paths (Dockerfile, docker-compose.yml, .dockerignore, and dependency manifests referenced in the Dockerfile). A final full verification (health check, compose start, contract tests) runs once after ALL tasks for a service complete, not after each individual task.
- Q: How should prompt rule compliance checking work concretely? → A: Two-tier approach. Tier 1 (automated): Load PromptSet via Feature 003's PromptLoader, extract all PromptThreshold entries (e.g., max_function_lines=30, min_coverage_percent=80), and map each threshold key to a concrete automated check. Tier 2 (delegated): Rules without machine-parseable thresholds (e.g., "all public functions must have docstrings") are included as context in the AI agent's fix prompt for self-checking but are NOT enforced by automated tooling.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Architecture-Aware Quality Gate (Priority: P1)

As the executor (Feature 009), after every completed task I need a comprehensive quality gate that automatically runs the right set of checks based on the project's architecture type. Today the quality checker only runs build, lint, and test — but microservice projects also need Docker build verification, health check validation, contract test execution, and service discovery compliance. Monolith projects need module boundary enforcement. The quality gate must detect the architecture from the project manifest and run all applicable checks without any manual configuration.

**Why this priority**: This is the core value proposition — without architecture-aware checks, quality validation misses entire categories of defects specific to the deployment model. Every other story depends on rich, categorized check results.

**Independent Test**: Can be fully tested by running the quality gate against a completed task in both a microservice project and a monolith project, and verifying that architecture-specific checks execute in addition to standard checks.

**Acceptance Scenarios**:

1. **Given** a task completes in a microservice project (e.g., ledger-service), **When** the quality gate runs, **Then** it executes all standard checks (build, lint, tests, coverage, code complexity, secrets scan, TODO scan, prompt rule compliance) AND all microservice-specific checks (Docker image builds, health endpoint responds, contract tests pass, service starts in compose, no hardcoded service URLs, proto files compile, event schema validation).
2. **Given** a task completes in a modular monolith project, **When** the quality gate runs, **Then** it executes all standard checks AND monolith-specific checks (no cross-module direct data access, module interface compliance, shared migration safety).
3. **Given** a task completes in a standard monolithic project, **When** the quality gate runs, **Then** it executes only the standard checks (no architecture-specific checks apply).
4. **Given** the project manifest declares architecture type "microservice", **When** the quality gate initializes, **Then** it automatically loads the microservice check suite without requiring any user configuration.
5. **Given** a standard check fails (e.g., lint errors), **When** the quality gate reports results, **Then** each failure includes the check name, category, full output, and a structured error message suitable for automated fix prompt generation.

---

### User Story 2 - Targeted Auto-Fix with Error Categorization (Priority: P1)

As a developer, when a quality check fails I want the auto-fix loop to understand *what kind* of failure occurred and generate a targeted fix prompt — not a generic "fix the error" message. Today the auto-fix loop sends the entire error output as one undifferentiated blob. The new system must parse the error, categorize it (syntax, logic, type, lint, coverage, docker, contract, boundary), and craft a specific remediation prompt that tells the AI agent exactly what to fix and where.

**Why this priority**: Targeted fix prompts dramatically improve first-attempt fix success rate. Generic prompts waste retry attempts on unfocused changes that may introduce new issues.

**Independent Test**: Can be fully tested by feeding known error outputs (e.g., a Docker build failure mentioning a missing system library) to the auto-fix system and verifying the generated fix prompt contains specific, actionable instructions rather than generic guidance.

**Acceptance Scenarios**:

1. **Given** a Docker build fails with "missing dependency libpq", **When** the auto-fix categorizes the error, **Then** it classifies it as "docker" category and generates a fix prompt saying "Add libpq-dev to the Dockerfile apt-get install line" — NOT a generic "fix the Docker error".
2. **Given** a lint check fails with specific rule violations on specific lines, **When** the auto-fix generates a prompt, **Then** the prompt references the exact file paths, line numbers, and rule IDs that need correction.
3. **Given** a contract test fails because a response schema doesn't match the published contract, **When** the auto-fix categorizes the error, **Then** it classifies it as "contract" category and the fix prompt references the specific schema field mismatch and the contract file.
4. **Given** a module boundary violation is detected (direct cross-module data access), **When** the auto-fix categorizes it, **Then** it classifies it as "boundary" category and the prompt specifies which module boundary was crossed and suggests routing through the defined interface.
5. **Given** a coverage check fails because a new function lacks tests, **When** the auto-fix categorizes it, **Then** it classifies it as "coverage" category and the prompt identifies the uncovered function and file.
6. **Given** a fix is applied and re-checked, **When** the same check passes but a different check now fails (regression), **Then** the system detects the regression, reverts the fix, and generates a new prompt addressing both the original failure and the regression risk.

---

### User Story 3 - Auto-Fix Retry with Attempt Budget (Priority: P2)

As the executor, I need the auto-fix loop to make up to 3 targeted fix attempts per failing task before giving up. Each attempt should learn from previous failures — if attempt 1 didn't work, attempt 2's prompt should include what was tried and why it failed, so the AI agent doesn't repeat the same unsuccessful approach.

**Why this priority**: The retry budget prevents infinite loops while giving enough room for iterative fixes. Progressive context (learning from prior attempts) is what separates effective auto-fix from brute-force retries.

**Independent Test**: Can be fully tested by providing a task with a deliberately complex failure requiring multiple fix iterations, and verifying that each successive attempt prompt includes context from prior attempts.

**Acceptance Scenarios**:

1. **Given** a quality check fails after task completion, **When** auto-fix attempt 1 is generated, **Then** the fix prompt includes the categorized error, affected files, and specific remediation instructions.
2. **Given** auto-fix attempt 1 was applied but the check still fails, **When** attempt 2 is generated, **Then** the prompt includes: the original error, what attempt 1 changed, why it didn't fully resolve the issue, and refined instructions.
3. **Given** auto-fix attempt 2 was applied but the check still fails, **When** attempt 3 is generated, **Then** the prompt includes full history of all prior attempts, their changes, and remaining failures — giving the AI agent maximum context for a final resolution.
4. **Given** all 3 auto-fix attempts have been exhausted and the check still fails, **When** the system escalates, **Then** it halts execution of the current task and produces a diagnostic report.

---

### User Story 4 - Diagnostic Report on Escalation (Priority: P2)

As a developer, when auto-fix exhausts all 3 attempts and still cannot resolve a quality failure, I need a detailed diagnostic report that helps me understand what happened, what was tried, and what to do next. This report should be structured so I can quickly identify the root cause and take manual action.

**Why this priority**: When automation fails, developer time is the most expensive resource. A good diagnostic report reduces manual investigation time from hours to minutes.

**Independent Test**: Can be fully tested by triggering a 3-attempt auto-fix exhaustion and verifying the generated report contains all required sections with accurate information.

**Acceptance Scenarios**:

1. **Given** auto-fix has exhausted 3 attempts for a failing task, **When** the diagnostic report is generated, **Then** it includes: the original error with full output, all 3 fix attempts (what was changed in each), what checks passed and failed after each attempt, what is still failing, and suggested manual remediation steps.
2. **Given** a diagnostic report is generated, **When** a developer reads it, **Then** they can identify which specific check is still failing, see a timeline of what was tried, and follow the suggested steps without needing to re-run any checks manually.
3. **Given** the diagnostic report includes suggested manual steps, **When** a developer follows them, **Then** the suggestions are specific to the error category (e.g., "docker" failures suggest Dockerfile changes, "boundary" failures suggest interface refactoring).

---

### User Story 5 - Prompt Rule Compliance Checking (Priority: P3)

As a developer who has configured governance rules (Feature 003), I want the quality gate to verify that generated code satisfies all applicable prompt file rules — including coding standards, testing requirements, and architecture constraints defined in the project's governance files.

**Why this priority**: Prompt rules encode project-specific quality standards that go beyond generic lint/test checks. Without compliance checking, the governance system is advisory-only rather than enforced.

**Independent Test**: Can be fully tested by configuring prompt rules (e.g., "all public functions must have docstrings") and verifying the quality gate detects violations.

**Acceptance Scenarios**:

1. **Given** the project's testing.prompts.md defines a minimum coverage threshold, **When** the quality gate runs, **Then** it verifies code coverage meets that threshold and reports the actual vs. required percentage if it fails.
2. **Given** the project's coding.prompts.md defines maximum function length as 30 lines, **When** the quality gate analyzes changed files, **Then** it flags any function exceeding 30 lines with the function name, file, and actual line count.
3. **Given** the project's coding.prompts.md defines maximum class length as 200 lines, **When** the quality gate analyzes changed files, **Then** it flags any class exceeding 200 lines.

---

### Edge Cases

- What happens when the project manifest does not specify an architecture type? The system defaults to standard monolithic checks only (no architecture-specific checks).
- What happens when a microservice-specific check tool is not available (e.g., Docker is not installed)? The check is skipped with a warning, and the quality report notes which checks were skipped and why.
- What happens when auto-fix attempt 1 introduces a regression (new test failures)? The system reverts the fix, notes the regression in the attempt history, and generates attempt 2's prompt with anti-regression guidance.
- What happens when the same error appears in multiple categories (e.g., a type error that also causes a test failure)? The system categorizes by root cause — the type error is the primary category, the test failure is a secondary symptom noted in the report.
- What happens when all 3 fix attempts succeed on the original failure but each introduces a different regression? The report highlights the pattern and suggests the original task implementation may need fundamental rethinking.
- What happens when quality checks run on a task that changed no files? The system skips file-specific checks (lint, complexity, secrets) but still runs project-level checks (build, full test suite).
- What happens when the coverage threshold is not specified in any prompt file? The coverage check is skipped (not enforced) rather than using a hardcoded default.
- What happens when changed files include non-Python files and AST analysis is requested? Non-Python files are skipped for function/class length checks with a warning noting no parser plugin is registered for that language.
- What happens when a contract test failure is attributed to a provider (external service)? The system categorizes it as "contract/provider", skips auto-fix attempts entirely, and escalates immediately with a diagnostic report noting the external dependency change.
- What happens when a task modifies only test files but not the Dockerfile? Docker build checks are skipped for that task. Full container verification runs after all service tasks complete.
- What happens when a governance prompt file has rules without thresholds (descriptive-only rules)? Those rules are included as Tier 2 context for the AI agent but not enforced by automated quality gate checks.

## Requirements *(mandatory)*

### Functional Requirements

#### Standard Quality Checks (All Architectures)

- **FR-001**: System MUST run a build check that verifies the project builds successfully without errors after each task completion.
- **FR-002**: System MUST run a lint check on all changed files using the project's configured linter and report specific violations with file paths, line numbers, and rule IDs.
- **FR-003**: System MUST run the project's full test suite and report pass/fail results with failure details.
- **FR-004**: System MUST verify code coverage meets the threshold defined in the project's testing governance file, reporting actual coverage vs. required threshold on failure.
- **FR-005**: System MUST analyze changed Python files for function length violations (functions exceeding 30 lines) using Python `ast` module analysis, reporting function name, file, and line count. Non-Python files are skipped with a warning until a language-specific parser plugin is registered.
- **FR-005a**: System MUST provide a pluggable language analyzer interface so additional language parsers (e.g., Roslyn for .NET, Tree-sitter for polyglot projects) can be registered without modifying the core check framework.
- **FR-006**: System MUST analyze changed Python files for class length violations (classes exceeding 200 lines) using Python `ast` module analysis, reporting class name, file, and line count. Same language plugin extensibility as FR-005a applies.
- **FR-007**: System MUST scan changed files for secrets, credentials, API keys, and tokens, reporting the file and line where a potential secret was detected.
- **FR-008**: System MUST scan changed files for remaining TODO, FIXME, and HACK comments and report their locations.
- **FR-009**: System MUST verify prompt rule compliance using a two-tier approach: **Tier 1 (automated)** — Load the project's PromptSet via Feature 003's PromptLoader, extract all PromptThreshold entries (e.g., `max_function_lines=30`, `min_coverage_percent=80`), and map each threshold key to a concrete automated check that runs as part of the quality gate. **Tier 2 (delegated)** — Rules without machine-parseable thresholds (e.g., "all public functions must have docstrings") are included as context in the AI agent's fix prompt for self-checking but are NOT enforced by automated tooling in the quality gate.

#### Microservice-Specific Checks

- **FR-010**: System MUST verify that the service's container image builds successfully when the project architecture is "microservice" AND the task's changed files intersect container-relevant paths (Dockerfile, docker-compose.yml, .dockerignore, dependency manifests referenced in Dockerfile). Tasks that do not modify container-relevant files skip this check.
- **FR-010a**: System MUST run a full container verification (image build, health check, compose start, contract tests) once after ALL tasks for a service complete, regardless of individual task file changes.
- **FR-011**: System MUST verify that the service's health check endpoint returns a successful response as part of full service verification (FR-010a) when the project architecture is "microservice".
- **FR-012**: System MUST verify that consumer contract tests pass when the project architecture is "microservice". Contract test failures MUST include a sub-attribution of "consumer" (our service's code is incorrect — eligible for auto-fix) or "provider" (external service changed its contract — escalate immediately without auto-fix attempts, include external dependency change notice in diagnostic report).
- **FR-013**: System MUST verify that the service starts in the composition environment and responds to requests when the project architecture is "microservice".
- **FR-014**: System MUST detect hardcoded URLs to other services (services must use service discovery or configuration) when the project architecture is "microservice".
- **FR-015**: System MUST verify that interface definition files (e.g., protocol buffer definitions) compile successfully when the project architecture is "microservice" and such files exist.
- **FR-016**: System MUST validate event schemas against published contracts when the project architecture is "microservice" and event-driven communication is used.

#### Modular Monolith-Specific Checks

- **FR-017**: System MUST detect cross-module direct data access violations (one module accessing another module's data store directly) when the project architecture is "modular-monolith".
- **FR-018**: System MUST verify module interface compliance (all external access to a module goes through its defined public interfaces) when the project architecture is "modular-monolith".
- **FR-019**: System MUST verify that shared data migration changes do not break other modules when the project architecture is "modular-monolith".

#### Error Categorization

- **FR-020**: System MUST categorize every quality check failure into exactly one of these categories: syntax, logic, type, lint, coverage, docker, contract, boundary, security.
- **FR-021**: System MUST parse error messages to extract actionable details: affected file paths, line numbers, error codes, specific violation descriptions, and any referenced external resources (contract files, schema files, interface definitions).

#### Targeted Auto-Fix

- **FR-022**: System MUST generate a targeted fix prompt for each categorized error that includes: the specific error category, affected files and locations, what exactly needs to change, and why — rather than a generic "fix the error" instruction.
- **FR-023**: System MUST limit auto-fix to a maximum of 3 attempts per failing task before escalating.
- **FR-024**: System MUST include in each successive fix attempt the full history of prior attempts: what was changed, what the outcome was, and what still needs fixing.
- **FR-025**: System MUST detect regressions introduced by a fix attempt (new failures that did not exist before the fix) and revert the fix when a regression is detected.
- **FR-026**: System MUST re-run only the previously-failed checks after applying a fix (not the entire check suite), plus a regression check on previously-passing checks.

#### Diagnostic Report

- **FR-027**: System MUST generate a structured diagnostic report when auto-fix exhausts all attempts, containing: the original error with full output, a summary of each fix attempt (changes made, check results), what is still failing, and suggested manual remediation steps specific to the error category.
- **FR-028**: System MUST include in the diagnostic report a timeline showing the progression from original failure through each fix attempt.

#### Integration & Compatibility

- **FR-029**: System MUST maintain backward compatibility with the existing executor interface (Feature 009) — specifically the quality check result structure and the auto-fix loop invocation pattern.
- **FR-030**: System MUST read architecture type from the project manifest and automatically select the appropriate check suite without user configuration.
- **FR-031**: System MUST gracefully handle missing tools (e.g., container runtime not installed) by skipping the affected check with a warning rather than failing the entire quality gate.

### Key Entities

- **Quality Check**: A single validation step (e.g., "lint check", "Docker build check") with a name, category, applicability rules (which architectures it applies to), and execution logic. Produces a check result with pass/fail status, output, and structured error details.
- **Check Result**: The outcome of a single quality check, including pass/fail status, full output, error category, affected files/lines, and parsed error details suitable for fix prompt generation.
- **Quality Gate Result**: The aggregate outcome of running all applicable quality checks for a given architecture, containing all individual check results, overall pass/fail, a list of failed checks, and regression detection status. Replaces the "check suite" concept — the QualityGate itself orchestrates check selection and execution.
- **Fix Attempt**: A single auto-fix iteration, containing the generated fix prompt, the changes made, the re-check results, and whether a regression was detected.
- **Diagnostic Report**: A structured escalation document produced after auto-fix exhaustion, containing the full timeline of the original failure and all fix attempts, with suggested manual remediation.
- **Error Category**: A classification label (syntax, logic, type, lint, coverage, docker, contract, boundary, security) assigned to each failure to drive targeted fix prompt generation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of architecture-specific quality checks execute automatically based on manifest configuration — no manual check selection required.
- **SC-002**: Auto-fix resolves at least 70% of quality failures within the 3-attempt budget, compared to the current baseline (measured across a representative set of common failure types).
- **SC-003**: Targeted fix prompts achieve a higher first-attempt resolution rate than generic fix prompts — at least 50% of failures resolved on the first auto-fix attempt.
- **SC-004**: Diagnostic reports reduce manual investigation time — developers can identify the root cause and next steps within 5 minutes of reading the report.
- **SC-005**: The quality gate completes all standard checks within 2 minutes for a typical project, ensuring the feedback loop remains fast enough for iterative development.
- **SC-006**: Zero false negatives on secrets detection — no committed code contains credentials, API keys, or tokens that the quality gate should have caught.
- **SC-007**: Regressions introduced by auto-fix attempts are detected and reverted 100% of the time, preventing fix attempts from making the codebase worse.

## Assumptions

- The project manifest (`.specforge/manifest.json`) always contains an `architecture` field or defaults to `"monolithic"` when absent.
- Feature 009's executor interface (QualityCheckResult dataclass, auto-fix invocation pattern) is the integration contract this feature must honor.
- The existing governance prompt files (Feature 003) provide machine-readable rule IDs and PromptThreshold entries that can be programmatically loaded via PromptLoader and mapped to automated checks.
- Descriptive governance rules (no thresholds) are advisory context for the AI agent, not automated enforcement targets.
- Container runtime availability is an environment concern — the system adapts to what's installed rather than requiring all tools.
- Code complexity thresholds (30-line functions, 200-line classes) are applied via Python `ast` module initially; other languages require a registered parser plugin.
- Module boundaries for modular-monolith checks (BoundaryChecker, MigrationChecker) are read from `.specforge/manifest.json` `modules` key; if absent, directory-convention detection is used (top-level dirs under `src/` as modules, `__init__.py`/`api.py`/`interfaces/` as public interfaces).
- The 3-attempt maximum for auto-fix is a fixed limit, not user-configurable, to prevent runaway retry loops.
- Contract test failures attributed to provider-side changes are not auto-fixable and must escalate immediately.
- Docker/container checks are scoped to tasks that modify container-relevant files; a final full verification runs once after all service tasks complete.
