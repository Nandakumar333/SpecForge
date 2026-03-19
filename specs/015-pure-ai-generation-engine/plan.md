# Implementation Plan: Pure AI Content Generation Engine

**Branch**: `015-pure-ai-generation-engine` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-pure-ai-generation-engine/spec.md`

## Summary

Replace Jinja2 template rendering in the content generation path (specify pipeline + decompose) with direct LLM calls via a provider abstraction. Each pipeline phase constructs a prompt from constitution + governance + architecture context + prior artifacts + Spec-Kit skeleton, calls the configured LLM, validates the output for required sections, and writes the artifact. Template rendering is preserved as a `--template-mode` fallback and remains the sole mechanism for `specforge init` scaffolding. The design extends `BasePhase` with dual-mode execution rather than introducing a monolithic generator class, keeping each phase testable in isolation.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click 8.x (CLI), Rich 13.x (terminal output), Jinja2 3.x (retained for init scaffolding + template-mode fallback), `subprocess` stdlib (LLM CLI invocation)
**Storage**: File system — `.specforge/config.json` (LLM config), `.specforge/features/<slug>/` (artifacts + `.draft.md` + `.prompt.md`), `.specforge/manifest.json` (read)
**Testing**: pytest + pytest-cov + syrupy (snapshots) + ruff (linting)
**Target Platform**: Cross-platform CLI (Windows, macOS, Linux)
**Project Type**: CLI tool (extension of existing SpecForge)
**Performance Goals**: Full 7-phase pipeline completes in <10 minutes including LLM round-trips (SC-010)
**Constraints**: No new PyPI dependencies — `subprocess`, `json`, `re`, `time` are all stdlib; LLM providers invoked via CLI subprocess or future HTTP
**Scale/Scope**: 5 new modules, 13 modified files (2 CLI + 1 config + 1 adapter + 1 pipeline + 1 base_phase + 7 phase subclasses), 8 PhasePrompt definitions, 3 architecture adapters updated

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-Design Status | Post-Design Status |
|-----------|------|--------------------|--------------------|
| I. Spec-First | spec.md complete before implementation | PASS — spec exists with 48 FRs, 14 SCs, 7 user stories, 10 edge cases | PASS |
| II. Architecture | Core logic zero external deps; Jinja2 templates for file generation; plugin system for agents | PASS — `LLMProvider` is a Protocol in `core/`; subprocess invocation uses stdlib only; Jinja2 retained for init scaffolding; plugins NOT extended with LLM calls | PASS — `LLMProvider` protocol + `SubprocessProvider` use only stdlib; clean separation from plugin layer |
| III. Code Quality | Functions ≤30 lines; classes ≤200 lines; strict types; no magic strings; `Result` returns; constructor injection | PASS — all new modules follow existing patterns; constants in `config.py`; all public methods return `Result` | PASS — `PromptAssembler` ~120 lines, `OutputValidator` ~80 lines, `SubprocessProvider` ~60 lines |
| IV. Testing | TDD: test files before implementation; unit + integration + snapshot | PASS — test plan: unit tests for all 5 new modules, integration tests for CLI with `--template-mode` + `--dry-run-prompt`, snapshot tests for assembled prompts | PASS |
| V. Commit Strategy | Conventional Commits; one commit per task | PASS | PASS |
| VI. File Structure | Modules in correct architectural layer; no cross-layer imports | PASS — all new modules in `core/`; CLI flags in `cli/`; no `core` → `cli` imports | PASS |
| VII. Governance | Constitution supersedes all other docs | PASS — Jinja2 mandate applies to init scaffolding, not to LLM-generated content (Principle II says "All **file generation** MUST use Jinja2 templates"; LLM output is content, not file generation scaffolding) | PASS — see Complexity Tracking for justification |

**All gates PASS. Proceeding to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/015-pure-ai-generation-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (LLMProvider protocol contract)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/specforge/
├── cli/
│   ├── specify_cmd.py           # MODIFIED — add --template-mode, --dry-run-prompt flags; resolve LLMProvider
│   └── decompose_cmd.py         # MODIFIED — add --template-mode, --dry-run-prompt; LLM decompose path
├── core/
│   ├── config.py                # MODIFIED — add GOVERNANCE_PHASE_MAP, LLM_DEFAULT_TIMEOUT, LLM_DEFAULT_MAX_RETRIES,
│   │                            #   LLM_DEFAULT_BACKOFF_BASE, LLM_DEFAULT_MAX_BACKOFF, MAX_OUTPUT_CHARS,
│   │                            #   MAX_CONTINUATIONS, PHASE_REQUIRED_SECTIONS, PREAMBLE_PATTERNS
│   ├── llm_provider.py          # NEW — LLMProvider protocol + SubprocessProvider + ProviderFactory
│   ├── prompt_assembler.py      # NEW — PromptAssembler: constitution + governance + arch + artifacts + PhasePrompt
│   ├── output_validator.py      # NEW — OutputValidator: per-phase required section checking
│   ├── phase_prompts.py         # NEW — PhasePrompt dataclass + 8 definitions (7 pipeline + 1 decompose) with Spec-Kit skeletons
│   ├── output_postprocessor.py  # NEW — preamble stripping + continuation logic + output capping
│   ├── architecture_adapter.py  # MODIFIED — add serialize_for_prompt() to Protocol + 3 implementations
│   ├── spec_pipeline.py         # MODIFIED — PipelineOrchestrator accepts optional LLMProvider, passes to phases
│   └── phases/
│       ├── base_phase.py        # MODIFIED — extend run() with dual-mode (template vs LLM); add _build_prompt() hook
│       ├── specify_phase.py     # MODIFIED — add _build_prompt() returning phase-specific prompt context
│       ├── research_phase.py    # MODIFIED — add _build_prompt()
│       ├── datamodel_phase.py   # MODIFIED — add _build_prompt()
│       ├── edgecase_phase.py    # MODIFIED — add _build_prompt()
│       ├── plan_phase.py        # MODIFIED — add _build_prompt()
│       ├── checklist_phase.py   # MODIFIED — add _build_prompt()
│       └── tasks_phase.py       # MODIFIED — add _build_prompt()
└── templates/
    └── base/
        └── features/            # UNCHANGED — retained for --template-mode fallback

tests/
├── unit/
│   ├── test_llm_provider.py        # NEW — SubprocessProvider, ProviderFactory, timeout, retry
│   ├── test_prompt_assembler.py     # NEW — token budgeting, governance filtering, artifact inclusion
│   ├── test_output_validator.py     # NEW — required sections, per-phase rules
│   ├── test_phase_prompts.py        # NEW — PhasePrompt skeleton content, all 8 definitions
│   ├── test_output_postprocessor.py # NEW — preamble stripping, continuation, capping
│   └── test_base_phase_dual.py      # NEW — dual-mode run(), LLM path, template path
├── integration/
│   ├── test_specify_llm_mode.py     # NEW — full pipeline with mock provider
│   ├── test_decompose_llm_mode.py   # NEW — LLM decompose + fallback
│   ├── test_template_mode_flag.py   # NEW — --template-mode backward compat
│   └── test_dry_run_prompt.py       # NEW — --dry-run-prompt writes .prompt.md files
└── snapshots/
    └── test_prompt_assembly/        # NEW — snapshot tests for assembled prompts per phase + arch
```

**Structure Decision**: Existing single-project layout. Five new domain modules in `core/`, modifications to existing pipeline and CLI layers. No new directories beyond test subdirectories. The `LLMProvider` protocol lives in `core/` (zero external deps — subprocess is stdlib). `PromptAssembler` is the central new coordination point, replacing `TemplateRenderer` in the LLM path.

## Implementation Phases

### Phase 1: Foundation — LLM Provider + Config Constants

**Files**: `core/llm_provider.py`, `core/config.py` (modified)

1. Define `LLMProvider` protocol with `call(system_prompt: str, user_prompt: str) -> Result[str, str]`
2. Implement `SubprocessProvider` — invokes CLI tool via `subprocess.run()` with configurable timeout
3. Implement `ProviderFactory.create(config_path: Path) -> Result[LLMProvider, str]` — reads `config.json` `"agent"` field, maps to provider, validates CLI availability via `shutil.which()`
4. Add constants to `config.py`: `GOVERNANCE_PHASE_MAP`, `LLM_DEFAULT_TIMEOUT`, `LLM_DEFAULT_MAX_RETRIES`, `LLM_DEFAULT_BACKOFF_BASE`, `LLM_DEFAULT_MAX_BACKOFF`, `MAX_OUTPUT_CHARS`, `MAX_CONTINUATIONS`, `PHASE_REQUIRED_SECTIONS`, `PREAMBLE_PATTERNS`

### Phase 2: Prompt Construction — Assembler + PhasePrompts

**Files**: `core/prompt_assembler.py`, `core/phase_prompts.py`, `core/architecture_adapter.py` (modified)

1. Define `PhasePrompt` dataclass with `phase_name`, `system_instructions`, `skeleton` (the Spec-Kit template), `clean_markdown_instruction`
2. Create 8 `PhasePrompt` instances (7 pipeline phases + decompose) with exact Spec-Kit skeletons
3. Add `serialize_for_prompt() -> str` to `ArchitectureAdapter` protocol + 3 implementations — converts dict context into prose prompt sections
4. Implement `PromptAssembler.assemble(phase: str, service_ctx: ServiceContext, adapter: ArchitectureAdapter, prior_artifacts: dict[str, str], prompt_loader: PromptLoader | None) -> Result[tuple[str, str], str]` — returns `(system_prompt, user_prompt)` with token budget enforcement

### Phase 3: Output Validation + Post-Processing

**Files**: `core/output_validator.py`, `core/output_postprocessor.py`

1. Implement `OutputValidator.validate(phase: str, content: str) -> Result[str, list[str]]` — checks required sections from `PHASE_REQUIRED_SECTIONS`
2. Implement `OutputPostprocessor.strip_preamble(content: str) -> str` — removes LLM conversational prefixes before first `#` heading
3. Implement `OutputPostprocessor.detect_truncation(phase: str, content: str) -> bool` — checks for missing required sections + incomplete trailing content
4. Implement `OutputPostprocessor.build_continuation_prompt(partial: str) -> str` — constructs continuation instruction

### Phase 4: Pipeline Integration — Dual-Mode BasePhase

**Files**: `core/phases/base_phase.py` (modified), all 7 phase files (modified), `core/spec_pipeline.py` (modified)

1. Extend `BasePhase.run()` with `mode` parameter and `provider`/`assembler` optional params
2. Add abstract `_build_prompt(service_ctx, adapter, input_artifacts) -> dict[str, str]` hook to `BasePhase` (returns `{"feature_description": ..., "service_name": ...}` for user prompt context)
3. Implement LLM execution path in `BasePhase.run()`: `_build_prompt()` → `assembler.assemble()` → `provider.call()` → `postprocessor.strip_preamble()` → `validator.validate()` → retry loop → `_write_artifact()`
4. Implement `_build_prompt()` in all 7 phase subclasses
5. Modify `PipelineOrchestrator.__init__()` to accept optional `LLMProvider`, `PromptAssembler`, `OutputValidator`, `OutputPostprocessor`
6. Modify `PipelineOrchestrator._run_phases()` to pass mode + LLM dependencies to `phase.run()`
7. Preserve parallel datamodel+edgecase execution in LLM mode

### Phase 5: Decompose Integration

**Files**: `cli/decompose_cmd.py` (modified)

1. Add `--template-mode` and `--dry-run-prompt` flags to `decompose` command
2. Implement LLM decompose path: construct prompt → call provider → parse JSON response → feed to `ManifestWriter`
3. Implement fallback: on LLM failure, fall back to `DomainAnalyzer` with warning
4. Implement `--dry-run-prompt`: write `.prompt.md` and exit

### Phase 6: CLI Integration — Specify Command

**Files**: `cli/specify_cmd.py` (modified)

1. Add `--template-mode` and `--dry-run-prompt` flags to `specify` command
2. Resolve `LLMProvider` from config; auto-fallback to template mode if unavailable
3. Validate `--dry-run-prompt` + `--template-mode` mutual exclusion
4. Wire `PromptAssembler`, `OutputValidator`, `OutputPostprocessor` into `PipelineOrchestrator`

### Phase 7: Polish — Continuation, Governance Overrides, Template Updates

1. Implement continuation loop in `BasePhase.run()` LLM path (FR-040 to FR-042)
2. Implement `config.json` `"governance_phase_map"` override loading (FR-044)
3. Implement `config.json` `"llm"` object parsing (FR-036)
4. Update `constitution.md` Jinja2 template to match Spec-Kit format (FR-047)
5. Update `agent-file` Jinja2 template to match Spec-Kit format (FR-048)

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution Principle II says "All file generation MUST use Jinja2 templates" — LLM-generated content bypasses Jinja2 | The entire purpose of Feature 015 is to replace template-based content with LLM-generated content. Principle II's intent is to prevent string concatenation for _scaffolding_ output; LLM content is a fundamentally different generation mechanism. Jinja2 remains for init scaffolding. `--template-mode` preserves the original path. | Wrapping LLM output in a Jinja2 template pass would add complexity with zero value — the LLM already produces the final markdown. |
| `SubprocessProvider.call()` may exceed 30-line function limit due to retry loop + timeout handling | The retry loop with exponential backoff, timeout enforcement, and error classification is a single cohesive responsibility. Splitting into sub-functions would scatter the retry state machine across methods. | Extracting retry into a decorator was considered but rejected — the retry decision depends on error classification (transient vs content), which is provider-specific. A `_call_once()` + `_with_retries()` split is used to stay within limits. |
