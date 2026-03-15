# Feature Specification: Agent Instruction Prompt File System

**Feature Branch**: `003-agent-prompt-governance`
**Created**: 2026-03-15
**Status**: Draft
**Input**: User description: "Build the agent instruction prompt file system — the strict coding governance layer that makes SpecForge unique."

## Clarifications

### Session 2026-03-15

- Q: What is the exact precedence order when prompt files conflict? → A: `security > architecture > {backend = frontend = database} > testing > cicd` — the three domain files are equal priority; intra-group conflicts (e.g., backend vs database on the same rule) are flagged as ambiguous and reported for manual resolution rather than silently resolved.
- Q: How should sub-agents know which prompt files apply to their task? → A: Always load all 7 prompt files regardless of task type — avoids mis-classification bugs; context cost is negligible for Markdown files.
- Q: Should prompt files support variables (e.g., `{{MAX_FUNCTION_LINES}}`))? → A: No — all threshold values are hardcoded directly in prompt file text; teams edit the text to customize thresholds. Variable substitution is deferred to a future phase.
- Q: Should there be a `common.prompts.md` for cross-cutting rules? → A: No — `architecture.prompts.md` serves as the cross-cutting rules file at the highest non-security precedence. No 8th file.
- Q: How should tech-stack detection work when `--stack` is not specified? → A: `--stack` flag takes priority; if omitted, scan existing project files for known markers (e.g., `.csproj` → dotnet, `package.json` → nodejs, `pyproject.toml` → python); if no markers found, default to agnostic.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pre-Built Prompt Files for My Tech Stack (Priority: P1)

A developer runs `specforge init --stack dotnet` and immediately receives 7 fully populated prompt files inside `.specforge/prompts/`. Each file contains .NET-specific rules, code examples showing correct vs incorrect patterns, and measurable thresholds. No additional configuration is needed — sub-agents are governed from the moment the project is created.

**Why this priority**: Prompt files are the core governance mechanism that makes SpecForge unique. Without them, sub-agents have no hard constraints and fall back on generic AI defaults. This is the foundational deliverable — every other feature in this system depends on prompt files existing and being populated.

**Independent Test**: Can be fully tested by running `specforge init myapp --stack dotnet` in an empty directory and verifying that all 7 prompt files exist in `.specforge/prompts/` with .NET-specific content, at least 2 code examples per file, and at least 3 numeric thresholds per file — without any additional setup.

**Acceptance Scenarios**:

1. **Given** an empty directory, **When** `specforge init myapp --stack dotnet` is run, **Then** 7 prompt files are created in `.specforge/prompts/`: `architecture.prompts.md`, `backend.dotnet.prompts.md`, `frontend.prompts.md`, `database.prompts.md`, `security.prompts.md`, `testing.dotnet.prompts.md`, `cicd.prompts.md`. Stack-agnostic domains (`architecture`, `frontend`, `database`, `security`, `cicd`) use flat naming; stack-specific domains (`backend`, `testing`) include the stack suffix.
2. **Given** a project initialized with `--stack dotnet`, **When** any of the 7 prompt files is opened, **Then** it contains .NET-specific language constructs, at least 2 correct (✅) and incorrect (❌) code examples, and at least 3 numeric thresholds (e.g., max function length, min coverage %, max class size).
3. **Given** a project initialized with `--stack python`, **When** `backend.python.prompts.md` is opened, **Then** the rules reference Python-specific constructs and the content is meaningfully different from `backend.dotnet.prompts.md`.
4. **Given** `specforge init myapp` with no `--stack` flag, **When** the prompt files are generated, **Then** they contain language-agnostic rules applicable to any technology stack.
5. **Given** `specforge init myapp --stack nodejs`, **When** `backend.nodejs.prompts.md` is opened, **Then** it contains Node.js/TypeScript-specific rules distinct from `backend.dotnet.prompts.md` and `backend.python.prompts.md`.

---

### User Story 2 - Customize Prompt Rules for Company Standards (Priority: P2)

A team lead opens `.specforge/prompts/backend.dotnet.prompts.md` and edits the function-length threshold from 30 to 20 lines to match their company's stricter standards. They also add a custom rule requiring all service classes to end in `Service`. From that point forward, every sub-agent that generates backend code enforces these customized rules — no rebuild, re-initialization, or CLI command required.

**Why this priority**: Every team has unique coding standards. Pre-built defaults get teams started quickly, but customization is what makes governance production-worthy for real organizations. The mechanism must be as simple as editing a Markdown file.

**Independent Test**: Can be fully tested by editing a threshold value in any prompt file, then calling `PromptLoader.load_for_feature()` and asserting the returned content reflects the edited value — with zero CLI commands between the edit and the load call.

**Acceptance Scenarios**:

1. **Given** an initialized project, **When** a user edits any `.specforge/prompts/*.prompts.md` file directly, **Then** the next `PromptLoader.load_for_feature()` call returns the edited content with no CLI command or restart needed.
2. **Given** a user has added a custom rule to `backend.prompts.md`, **When** `PromptLoader.load_for_feature()` is called, **Then** the returned `PromptSet` includes the custom rule alongside the standard rules.
3. **Given** a user has changed a numeric threshold (e.g., max function length from 30 to 20), **When** the file is loaded, **Then** the new value (20) is present and the old value (30) is absent.
4. **Given** a user deletes an entire rule from a prompt file, **When** the file is loaded, **Then** the deleted rule is absent from the loaded content.
5. **Given** `specforge init --force` is run in a project with customized prompt files, **When** the command completes, **Then** the customized prompt files are preserved and only default-state (unmodified) prompt files are regenerated.

---

### User Story 3 - Load Prompt Files as Structured Constraints for Sub-Agents (Priority: P2)

The sub-agent executor calls `PromptLoader.load_for_feature("003-payments")` before starting any implementation task. It receives a structured `PromptSet` object containing all 7 prompt file contents organized by domain, the full precedence order for conflict resolution, and a combined summary ready for injection into an AI agent context window.

**Why this priority**: Prompt files are only valuable if they are actually loaded into sub-agent context as structured constraints. The `PromptLoader` is the programmatic bridge between the Markdown governance files and the AI agent runtime — without it, the files are documentation, not enforcement.

**Independent Test**: Can be fully tested by calling `PromptLoader.load_for_feature(feature_id)` in a unit test against an initialized project and asserting the returned object has all 7 domains populated, a defined precedence list, and content matching what is on disk — no filesystem side effects, no sub-agent invocation needed.

**Acceptance Scenarios**:

1. **Given** an initialized project with all 7 prompt files present, **When** `PromptLoader.load_for_feature("001-auth")` is called, **Then** a `Result.Ok` is returned containing a `PromptSet` with 7 domain entries (architecture, backend, frontend, database, security, testing, cicd), each with the full text content of its prompt file.
2. **Given** a valid project, **When** `PromptLoader.load_for_feature(feature_id)` is called, **Then** the returned `PromptSet` includes a `precedence` field listing the conflict-resolution order of all 7 domains.
3. **Given** one or more prompt files have been customized, **When** `PromptLoader.load_for_feature()` is called, **Then** the returned content reflects the customized files, not the original defaults.
4. **Given** one or more prompt files are missing from `.specforge/prompts/`, **When** `PromptLoader.load_for_feature()` is called, **Then** a `Result.Err` is returned with a message identifying each missing file by name and full path, with instructions on how to restore it.
5. **Given** any valid project, **When** `PromptLoader.load_for_feature()` completes, **Then** it returns within 500 milliseconds regardless of prompt file size.

---

### User Story 4 - Detect Conflicts Across Prompt Files (Priority: P3)

A developer runs `specforge validate-prompts` after customizing several prompt files. The tool detects that `backend.dotnet.prompts.md` sets a 30-line function limit while `architecture.prompts.md` sets a 50-line limit for the same rule. It reports the conflict, identifies which file wins per the defined precedence order (security > architecture > others), and suggests how to align the losing file.

**Why this priority**: Teams will customize prompt files over time and contradictory rules will emerge. The validator surfaces conflicts before they produce confusing or inconsistent sub-agent behavior. This is a quality-of-life feature that prevents governance drift in long-lived projects.

**Independent Test**: Can be fully tested by intentionally introducing a conflicting threshold (same rule category, different numeric value) into two prompt files and running `specforge validate-prompts`, then asserting the conflict appears in output with the correct winning file identified by precedence — no code generation required.

**Acceptance Scenarios**:

1. **Given** two prompt files contain the same measurable rule with different thresholds, **When** `specforge validate-prompts` is run, **Then** the conflict is reported with both values, both source file names, and the winning value per the defined precedence order.
2. **Given** all 7 prompt files contain no conflicts, **When** `specforge validate-prompts` is run, **Then** the output shows "No conflicts detected" and the command exits with code 0.
3. **Given** multiple conflicts exist across different file pairs, **When** `specforge validate-prompts` is run, **Then** all conflicts are reported in a single output pass — the user does not need to re-run to find additional conflicts.
4. **Given** a conflict exists, **When** the report is displayed, **Then** it includes the winning rule value, the losing rule value, which file wins, which file should be updated, and a one-line suggested resolution.
5. **Given** one or more conflicts are detected, **When** `specforge validate-prompts` completes, **Then** it exits with a non-zero exit code so CI pipelines can automatically block builds with governance drift.

---

### Edge Cases

- What happens when `specforge init --force` is run in a project where prompt files have been manually customized — are customizations overwritten or preserved?
- What happens when a prompt file for one stack accidentally contains rules referencing constructs from a different stack?
- What happens when all 7 prompt files are deleted and `PromptLoader.load_for_feature()` is called?
- What happens when two prompt files contain contradictory thresholds for the same measurable rule — which value is used by sub-agents at runtime? (Resolved: the higher-precedence file wins per `security > architecture > {backend=frontend=database} > testing > cicd`; intra-group conflicts are flagged as ambiguous for manual resolution.)
- What happens when `specforge init --stack ruby` is run (unsupported stack)?
- What happens if a prompt file is malformed (broken Markdown, missing required sections)?
- What happens when `specforge validate-prompts` is run in a directory with no `.specforge/` folder?
- What happens when only a subset of the 7 prompt files exist (some deleted, some present)?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `specforge init` MUST generate all 7 prompt files in `.specforge/prompts/` for every supported stack: `dotnet`, `nodejs`, `python`, `go`, `java`, and `agnostic` (default when no `--stack` is specified). There is no 8th shared file — `architecture.prompts.md` serves as the cross-cutting rules file.
- **FR-002**: Each generated prompt file MUST be stack-specific — content MUST differ meaningfully between stacks (different language constructs, library names, toolchain references, and conventions).
- **FR-003**: Every rule in every prompt file MUST be stated as a hard constraint using `MUST`, `MUST NOT`, or `is prohibited` — descriptive guidelines without an enforceable verb are not permitted.
- **FR-004**: Each prompt file MUST include at least 2 code examples per major rule category — one marked compliant (✅) and one marked non-compliant (❌).
- **FR-005**: Each prompt file MUST define numeric thresholds for all measurable constraints (e.g., maximum function length in lines, minimum test coverage %, maximum class size in lines).
- **FR-006**: The system MUST define and document a fixed conflict-resolution precedence order across the 7 domains: `security > architecture > {backend = frontend = database} > testing > cicd`. The three domain-level files (`backend`, `frontend`, `database`) are equal priority; intra-group conflicts (e.g., `backend` vs `database` on the same rule) MUST be flagged as ambiguous and reported for manual resolution rather than silently resolved.
- **FR-017**: Each governance prompt file MUST use a globally unique rule ID namespace prefix per domain: `ARCH-` for architecture, `BACK-` for backend, `FRONT-` for frontend, `DB-` for database, `SEC-` for security, `TEST-` for testing, `CICD-` for cicd. Rule IDs MUST NOT be reused across domains. Each file MUST NOT exceed 500 lines to ensure compatibility with LLM context windows.
- **FR-016**: When `--stack` is not specified on `specforge init`, the system MUST first scan the target directory for known stack markers (`.csproj` → `dotnet`, `package.json` → `nodejs`, `pyproject.toml` or `requirements.txt` → `python`, `go.mod` → `go`, `pom.xml` or `build.gradle` → `java`) and use the detected stack; if no markers are found, it MUST default to `agnostic`.
- **FR-007**: Each prompt file MUST include a `## Precedence` section declaring its position in the conflict-resolution hierarchy.
- **FR-008**: Editing a prompt file on disk MUST be immediately reflected the next time `PromptLoader.load_for_feature()` is called — no cache invalidation step, CLI command, or restart is required.
- **FR-009**: The system MUST expose `PromptLoader.load_for_feature(feature_id: str) -> Result[PromptSet, str]` returning a `PromptSet` with all 7 domain prompt contents and a `precedence` list.
- **FR-010**: `PromptLoader.load_for_feature()` MUST return `Result.Err` with a human-readable message if any prompt file is missing, identifying the file by name and path.
- **FR-011**: `PromptLoader.load_for_feature()` MUST complete within 500 milliseconds for any supported project.
- **FR-012**: The CLI MUST provide a `validate-prompts` command that scans all 7 prompt files, detects conflicting rules, and reports each conflict with: rule name, both values, both source files, the winning value per precedence, and a suggested resolution.
- **FR-013**: `specforge validate-prompts` MUST exit with code 0 when no conflicts are detected and a non-zero exit code when any conflict is detected.
- **FR-014**: When `specforge init --force` is run in a project with existing prompt files, the system MUST preserve any customized prompt files and only regenerate files that are in their original generated state.
- **FR-015**: `specforge init` MUST reject unsupported `--stack` values with a non-zero exit code and an error message listing all supported stack names.

### Key Entities

- **PromptFile**: A single Markdown governance file for one domain. Has a domain name, stack variant, version, list of rules, numeric thresholds, and code examples. Lives at `.specforge/prompts/<domain>.prompts.md`.
- **PromptRule**: An individual enforceable constraint within a prompt file. Has a rule ID, description, threshold value (if numeric), enforcement verb (`MUST` / `MUST NOT`), and associated compliant/non-compliant code examples.
- **PromptSet**: The complete collection of all 7 `PromptFile` objects for a project, plus the ordered `precedence` list. This is the return value of `PromptLoader.load_for_feature()`.
- **StackProfile**: The mapping from a stack name (`dotnet`, `nodejs`, `python`, `go`, `java`, `agnostic`) to the Jinja2 template files used to render that stack's 7 prompt files.
- **ConflictReport**: The output of `specforge validate-prompts`. Contains a list of detected conflicts; each conflict has the rule name, both values, both source file names, the winning value per precedence, and a suggested resolution.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `specforge init myapp --stack dotnet` produces all 7 prompt files with stack-specific content in under 5 seconds from command invocation to completion.
- **SC-002**: A team member can change a governance rule (edit threshold, add rule, or remove rule) by editing a single Markdown file — the change is effective for the next sub-agent operation with zero additional commands.
- **SC-003**: `PromptLoader.load_for_feature()` returns a fully populated `PromptSet` in under 500 milliseconds for any supported project.
- **SC-004**: `specforge validate-prompts` detects 100% of direct threshold conflicts (same rule category, different numeric value in two files) across all 7 prompt files in a single run.
- **SC-005**: All 5 supported stacks produce prompt files with meaningfully distinct content — no two stacks produce identical files for the same domain.
- **SC-006**: Sub-agents operating under the generated prompt files produce code that satisfies all defined governance rules (function length, class size, coverage thresholds) in at least 80% of tasks on the first generation attempt without manual correction.
