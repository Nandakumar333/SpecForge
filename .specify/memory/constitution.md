<!--
## Sync Impact Report
**Version change**: 1.0.0 → 1.1.0

### Principles Modified
- (none renamed)

### Principles Added
- V. Commit Strategy (promoted from standalone section to Core Principle)
- VI. File Structure Convention (promoted from standalone section to
  Core Principle)
- VII. Governance (promoted from standalone section to Core Principle;
  procedural details retained in Governance Procedures section)

### Sections Removed
- "Commit Strategy" (standalone) — now Principle V
- "File Structure Convention" (standalone) — now Principle VI
- "Governance" (standalone heading) — split into Principle VII +
  Governance Procedures section

### Templates Requiring Updates
- ✅ `.specify/templates/plan-template.md` — no changes required;
  Constitution Check references the constitution file dynamically
- ✅ `.specify/templates/spec-template.md` — no changes required;
  edge-case mandate already embedded in template structure
- ✅ `.specify/templates/tasks-template.md` — no changes required;
  path conventions are generic examples replaced per feature
- ✅ `.specify/templates/checklist-template.md` — no constitution refs
- ✅ `.specify/templates/agent-file-template.md` — no constitution refs

### Deferred TODOs
- None — all placeholders resolved.
-->

# SpecForge Constitution

SpecForge is an AI-powered spec-driven development engine that takes a
single natural-language prompt and produces a fully decomposed,
spec-driven, production-ready web application.

## Core Principles

### I. Spec-First Development

No code MUST be written until `spec.md`, `plan.md`, and `tasks.md`
exist for the feature. Specifications are the primary artifact; code
is the output. Edge cases are first-class citizens and MUST be
addressed in the spec before implementation begins.

**Rationale**: Late specification leads to rework and misaligned
implementations. Front-loading clarity is cheaper than back-loading
correctness. Every task in `tasks.md` must be traceable to a
requirement in `spec.md`.

### II. Architecture

SpecForge is a Python CLI tool. Core domain logic MUST have zero
external dependencies (Clean Architecture). A plugin system provides
multi-agent support and tech-stack adapters. All file generation MUST
use Jinja2 templates — string concatenation for output files is
prohibited.

**Rationale**: Clean Architecture boundaries ensure the core is
testable in isolation. Plugin boundaries allow the tool to evolve
without coupling the domain to any specific AI provider or framework.
Templates make generation output auditable and consistent.

### III. Code Quality

- Python 3.11+ with strict type hints on every function signature.
- Functions MUST NOT exceed 30 lines. Classes MUST NOT exceed
  200 lines.
- 100% unit test coverage is required for all core domain logic.
- Toolchain: `pytest`, `pytest-cov`, `ruff` (linting). No exceptions.
- Magic strings are prohibited; all paths and constants MUST live in
  `config.py` or enums.
- Functions MUST return `Result[T]` instead of raising exceptions for
  recoverable errors.
- Dependencies MUST be injected via constructor injection. Global
  state is prohibited.

**Rationale**: Size limits enforce single-responsibility. The Result
pattern makes error paths explicit and composable. Eliminating global
state makes the codebase trivially testable and thread-safe by
construction.

### IV. Testing

Test files MUST be created before implementation files (TDD enforced,
non-negotiable). Unit tests are required for all domain logic and
services. Integration tests MUST cover CLI commands using temporary
file systems. Snapshot tests MUST cover template rendering output.

**Rationale**: Tests written after the fact verify existing behavior
rather than specifying intended behavior. Writing tests first surfaces
design problems before code is committed and prevents coverage gaps in
the core domain.

### V. Commit Strategy

- Commit messages MUST follow Conventional Commits: `feat:`, `fix:`,
  `chore:`, `docs:`, `test:`.
- One commit per completed task from `tasks.md`.
- Every PR MUST reference the feature spec and pass all quality gates
  before merge.

**Rationale**: Atomic, traceable commits make bisecting regressions
fast and keep the git history meaningful as project documentation. PR
linkage to specs ensures traceability from requirement to merge.

### VI. File Structure Convention

```text
src/specforge/cli/       # Click-based commands
src/specforge/core/      # Domain logic — zero external dependencies
src/specforge/templates/ # Jinja2 .md.j2 files
src/specforge/plugins/   # Agent adapters, stack adapters
tests/unit/              # Unit tests for domain logic and services
tests/integration/       # CLI command tests with temporary file systems
tests/snapshots/         # Template rendering snapshot tests
```

All new modules MUST be placed in the directory that matches their
architectural layer. Cross-layer imports (e.g., `core` importing from
`cli`) are prohibited.

**Rationale**: Predictable structure lets contributors locate code by
concern. Hard module boundaries prevent dependency creep from core
into infrastructure layers.

### VII. Governance

This constitution supersedes all prompt files, agent instructions, and
per-feature conventions. **Scope clarification**: governance prompt files
in `.specforge/prompts/` govern the *target application's* coding
standards, not SpecForge's own implementation — they are excluded from
this supersession clause and do not inherit SpecForge's own code quality
thresholds (e.g., the 30-line function limit applies to SpecForge source
only). When conflicts arise within SpecForge's own codebase, the
resolution priority order is:

1. Security concerns
2. This constitution
3. Feature specifications (`spec.md`)
4. Implementation plans (`plan.md`)

**Guiding axioms**: Explicit > implicit. Verbose > clever.
Readable > concise.

**Rationale**: A single authoritative source of truth prevents
conflicting guidance across agents and documents. The priority ladder
makes conflict resolution deterministic rather than subjective.

## Governance Procedures

### Amendment Procedure

Amendments require: (1) a written rationale, (2) a version bump per
the Versioning Policy below, and (3) propagation to all affected
templates and command files via `/speckit.constitution`.

### Versioning Policy

`CONSTITUTION_VERSION` follows Semantic Versioning:

- **MAJOR**: Backward-incompatible governance changes, principle
  removals, or redefinitions.
- **MINOR**: New principles added or guidance materially expanded.
- **PATCH**: Clarifications, wording fixes, or non-semantic
  refinements.

### Compliance Review

All PRs and spec reviews MUST verify compliance with this
constitution. Violations that cannot be avoided MUST be documented in
the `plan.md` Complexity Tracking table with justification. No PR may
be merged with undocumented constitution violations.

**Version**: 1.1.0 | **Ratified**: 2026-03-14 | **Last Amended**: 2026-03-14
