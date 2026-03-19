# Data Model: Pure AI Content Generation Engine

**Feature**: 015-pure-ai-generation-engine
**Date**: 2026-03-19

## Entity Diagram

```text
┌──────────────────────────┐       ┌──────────────────────────┐
│   LLMProvider (Protocol) │       │   ProviderFactory        │
├──────────────────────────┤       ├──────────────────────────┤
│ + call(system, user)     │◄──────│ + create(config_path)    │
│   -> Result[str, str]    │       │   -> Result[LLMProvider] │
└──────────┬───────────────┘       └──────┬───────────────────┘
           │                              │ reads
           │ implements                   ▼
           │                     ┌──────────────────────────┐
┌──────────▼───────────────┐     │   config.json            │
│   SubprocessProvider     │     │   (.specforge/)          │
├──────────────────────────┤     ├──────────────────────────┤
│ - _command_template: str │     │   agent: str             │
│ - _timeout: int          │     │   llm:                   │
│ - _max_retries: int      │     │     token_budget: int?   │
│ - _backoff_base: float   │     │     timeout_seconds: int?│
│ + call(system, user)     │     │     max_retries: int?    │
│ - _call_once(sys, usr)   │     │     model: str?          │
│ - _classify_error(exc)   │     │     max_output_chars: int│
│ - _is_available() -> bool│     │   governance_phase_map:  │
└──────────────────────────┘     │     dict[str, list[str]]?│
                                 └──────────────────────────┘
           │
           │ used by
           ▼
┌──────────────────────────┐     ┌──────────────────────────┐
│   PromptAssembler        │────▶│   PhasePrompt            │
├──────────────────────────┤     ├──────────────────────────┤
│ - _constitution: str     │     │ + phase_name: str        │
│ - _prompt_loader: ...    │     │ + system_instructions: str│
│ - _token_budget: int     │     │ + skeleton: str          │
│ + assemble(phase, ctx,   │     │ + required_sections:     │
│   adapter, artifacts,    │     │     list[str]            │
│   governance_map)        │     │ + clean_markdown_instr: str│
│   -> Result[tuple, str]  │     └──────────────────────────┘
│ - _load_constitution()   │              │
│ - _load_governance(phase)│              │ 8 instances
│ - _serialize_artifacts() │              │ (7 pipeline + decompose)
│ - _apply_budget(sections)│              ▼
└──────────┬───────────────┘     ┌──────────────────────────┐
           │                     │   PHASE_PROMPTS: dict    │
           │ produces            │   (phase_prompts.py)     │
           ▼                     └──────────────────────────┘
┌──────────────────────────┐
│   (system_prompt: str,   │
│    user_prompt: str)     │
└──────────┬───────────────┘
           │ sent to LLMProvider
           ▼
┌──────────────────────────┐     ┌──────────────────────────┐
│   OutputPostprocessor    │────▶│   OutputValidator        │
├──────────────────────────┤     ├──────────────────────────┤
│ + strip_preamble(content)│     │ + validate(phase, text)  │
│ + detect_truncation(     │     │   -> Result[str, list]   │
│     phase, content)      │     │ - _check_sections(phase, │
│ + build_continuation(    │     │     content) -> list[str] │
│     partial) -> str      │     └──────────────────────────┘
│ + cap_output(content,    │
│     max_chars) -> str    │
└──────────────────────────┘

           │
           │ validated content written by
           ▼
┌──────────────────────────┐
│   BasePhase (modified)   │
├──────────────────────────┤
│ + run(service_ctx,       │
│   adapter, renderer,     │
│   registry, artifacts,   │
│   provider?, assembler?, │
│   validator?,            │
│   postprocessor?,        │
│   mode?)                 │
│ + _build_context(...)    │  ← existing (template mode)
│ + _build_prompt(...)     │  ← NEW (LLM mode)
│ + _write_artifact(...)   │  ← existing (shared)
└──────────────────────────┘
```

## Entities

### LLMProvider (new — `core/llm_provider.py`)

Protocol defining the interface for calling an LLM. All implementations conform to this protocol.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `call` | `(system_prompt: str, user_prompt: str) -> Result[str, str]` | `Ok(generated_text)` or `Err(error_description)` | Send prompts to the LLM and return generated content |

**Protocol definition** (runtime-checkable):
```python
@runtime_checkable
class LLMProvider(Protocol):
    def call(self, system_prompt: str, user_prompt: str) -> Result[str, str]: ...
```

### SubprocessProvider (new — `core/llm_provider.py`)

Concrete `LLMProvider` implementation that invokes an LLM CLI tool via `subprocess.run()`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `_command_template` | `str` | Per-agent | CLI command template with `{system}`, `{model}` placeholders |
| `_agent_name` | `str` | Required | Agent identifier (e.g., `"claude"`) |
| `_timeout` | `int` | `120` | Subprocess timeout in seconds (FR-005) |
| `_max_retries` | `int` | `3` | Maximum retry count for transient errors (FR-006) |
| `_backoff_base` | `float` | `1.0` | Exponential backoff base in seconds |
| `_max_backoff` | `float` | `16.0` | Maximum backoff delay in seconds |
| `_model` | `str \| None` | `None` | Optional model name override |

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `call` | `(system_prompt: str, user_prompt: str) -> Result[str, str]` | `Ok(stdout_text)` or `Err(error_msg)` | Execute CLI tool with retry and timeout |
| `_call_once` | `(system_prompt: str, user_prompt: str) -> Result[str, str]` | Same | Single subprocess invocation (no retry) |
| `_classify_error` | `(returncode: int, stderr: str) -> str` | `"transient"` / `"permanent"` / `"unknown"` | Classify error for retry decision |
| `is_available` | `() -> Result[None, str]` | `Ok(None)` or `Err(install_hint)` | Check CLI tool on PATH via `shutil.which()` |

**Constructor injection**: All fields passed via `__init__()`. No global state. No config file reading in the provider — `ProviderFactory` handles config resolution.

### ProviderFactory (new — `core/llm_provider.py`)

Factory that resolves the configured agent to an `LLMProvider` instance.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `create` | `(config_path: Path) -> Result[LLMProvider, str]` | `Ok(provider)` or `Err(reason)` | Read config.json, map agent → provider, validate availability |

**Resolution logic**:
1. Read `config_path` → parse JSON → extract `"agent"` field
2. Look up agent name in `_AGENT_COMMAND_TEMPLATES` mapping
3. If no mapping exists → `Err("Agent '{name}' does not support LLM generation")`
4. Extract `"llm"` config overrides (timeout, retries, model, etc.)
5. Construct `SubprocessProvider` with resolved config
6. Call `provider.is_available()` → return `Err` with install hint if unavailable
7. Return `Ok(provider)`

### PromptAssembler (new — `core/prompt_assembler.py`)

Constructs complete prompts for each pipeline phase by combining all context sources with token budget enforcement.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `_constitution_path` | `Path` | Required | Path to project's `constitution.md` |
| `_prompt_loader` | `PromptLoader \| None` | `None` | Loads governance prompts from `.specforge/prompts/` |
| `_token_budget` | `int` | `CONTEXT_TOKEN_BUDGET` | Maximum token budget (chars / `CHARS_PER_TOKEN_ESTIMATE`) |
| `_governance_phase_map` | `dict[str, list[str]]` | `GOVERNANCE_PHASE_MAP` | Phase-to-governance-domain mapping |

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `assemble` | `(phase: str, service_ctx: ServiceContext, adapter: ArchitectureAdapter, prior_artifacts: dict[str, str], phase_prompt: PhasePrompt) -> Result[tuple[str, str], str]` | `Ok((system_prompt, user_prompt))` or `Err(reason)` | Build full prompt pair with budget enforcement |
| `_load_constitution` | `() -> str` | constitution text | Read constitution.md |
| `_load_governance` | `(phase: str) -> str` | concatenated governance text | Load and filter governance by `GOVERNANCE_PHASE_MAP[phase]` |
| `_serialize_artifacts` | `(prior_artifacts: dict[str, str]) -> str` | serialized artifacts text | Concatenate prior artifacts with section markers |
| `_apply_budget` | `(sections: list[tuple[int, str]], max_chars: int) -> list[str]` | trimmed section texts | Priority-based trimming (highest priority index = never trimmed) |

**System prompt assembly order**:
```
1. PhasePrompt.clean_markdown_instruction
2. PhasePrompt.system_instructions
3. PhasePrompt.skeleton (target format)
4. Architecture context (adapter.serialize_for_prompt())
5. Governance prompts (filtered by phase)
6. Constitution
```

**User prompt assembly**:
```
1. "Generate {artifact_filename} for service: {service_name}"
2. Service description + feature list
3. Prior artifacts (full text, newest first)
```

### PhasePrompt (new — `core/phase_prompts.py`)

Frozen dataclass defining per-phase LLM instructions with Spec-Kit template skeletons.

| Field | Type | Description |
|-------|------|-------------|
| `phase_name` | `str` | Phase identifier (e.g., `"spec"`, `"plan"`, `"decompose"`) |
| `system_instructions` | `str` | Phase-specific instructions for the LLM |
| `skeleton` | `str` | Exact Spec-Kit template skeleton with section headers |
| `required_sections` | `tuple[str, ...]` | Heading strings that must appear in output |
| `clean_markdown_instruction` | `str` | Shared instruction: "Output ONLY the Markdown document..." |

**Instances**: 8 total — one per pipeline phase (`spec`, `research`, `datamodel`, `edgecase`, `plan`, `checklist`, `tasks`) + `decompose`.

**Skeleton example (spec phase)**:
```markdown
# Feature Specification: {feature_name}

**Feature Branch**: `{slug}`
**Created**: {date}
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story N — [Title] (Priority: P[0-3])

[story description]

**Acceptance Scenarios**:
1. **Given** ... **When** ... **Then** ...

### Edge Cases

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: [requirement]

### Key Entities

## Success Criteria *(mandatory)*
- **SC-001**: [criterion]
```

### OutputValidator (new — `core/output_validator.py`)

Validates LLM-generated content against per-phase structural requirements.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `validate` | `(phase: str, content: str) -> Result[str, list[str]]` | `Ok(content)` or `Err(missing_sections_list)` | Check required sections present |
| `build_correction_prompt` | `(phase: str, missing: list[str], original_output: str) -> str` | correction prompt text | Construct retry prompt listing missing sections |

**Validation rules**: Derived from `PhasePrompt.required_sections` — each entry is checked via case-insensitive heading search (`re.search(r'^#{1,3}\s*' + re.escape(heading), content, re.MULTILINE)`).

### OutputPostprocessor (new — `core/output_postprocessor.py`)

Post-processing pipeline for LLM output: preamble stripping, truncation detection, continuation, and output capping.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `strip_preamble` | `(content: str) -> str` | cleaned content | Remove text before first markdown heading |
| `normalize_headings` | `(content: str, expected_top_level: int) -> str` | normalized content | Normalize heading levels (e.g., `###` → `##`) to match expected artifact structure |
| `detect_truncation` | `(phase: str, content: str, required_sections: tuple[str, ...]) -> bool` | `True` if truncated | Check for missing sections + incomplete trailing content |
| `build_continuation_prompt` | `(partial_output: str) -> tuple[str, str]` | `(system_prompt, user_prompt)` | Construct continuation call prompts |
| `cap_output` | `(content: str, max_chars: int) -> str` | capped content | Enforce `MAX_OUTPUT_CHARS` limit |

### BasePhase (modified — `core/phases/base_phase.py`)

Extended with dual-mode execution. The `run()` method signature adds optional parameters for LLM mode.

**New parameters on `run()`**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | `LLMProvider \| None` | `None` | LLM provider (None = template mode) |
| `assembler` | `PromptAssembler \| None` | `None` | Prompt assembler |
| `validator` | `OutputValidator \| None` | `None` | Output validator |
| `postprocessor` | `OutputPostprocessor \| None` | `None` | Output post-processor |
| `dry_run_prompt` | `bool` | `False` | If True, write `.prompt.md` and return |

**New abstract method**:
| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `_build_prompt` | `(service_ctx, adapter, input_artifacts) -> dict[str, str]` | Context dict for user prompt | Returns service-specific context for prompt assembly |

**Execution flow (LLM mode)**:
```
1. _build_prompt() → user prompt context
2. assembler.assemble() → (system_prompt, user_prompt)
3. if dry_run_prompt: write .prompt.md, return Ok
4. provider.call(system, user) → raw output
5. postprocessor.strip_preamble() → cleaned output
6. while postprocessor.detect_truncation():
     continuation_call() → appended output  (max MAX_CONTINUATIONS)
7. postprocessor.cap_output() → capped output
8. validator.validate() → Ok or retry with correction prompt
9. _write_artifact() → Result
```

## Config Schema Extension

### config.json `"llm"` object (FR-036)

```json
{
  "project_name": "MyApp",
  "stack": "python",
  "agent": "claude",
  "commands_dir": ".claude/commands",
  "llm": {
    "token_budget": 100000,
    "timeout_seconds": 120,
    "max_retries": 3,
    "model": "claude-sonnet-4-20250514",
    "max_output_chars": 200000
  },
  "governance_phase_map": {
    "datamodel": ["database", "backend", "security", "api-design"]
  }
}
```

All `"llm"` fields are optional — defaults from `config.py` constants are used when absent.

## Constants Added to `config.py`

| Constant | Type | Value | Description |
|----------|------|-------|-------------|
| `GOVERNANCE_PHASE_MAP` | `dict[str, list[str]]` | See R6 | Phase → governance domain mapping |
| `LLM_DEFAULT_TIMEOUT` | `int` | `120` | Default subprocess timeout (seconds) |
| `LLM_DEFAULT_MAX_RETRIES` | `int` | `3` | Default max retry count |
| `LLM_DEFAULT_BACKOFF_BASE` | `float` | `1.0` | Default backoff base (seconds) |
| `LLM_DEFAULT_MAX_BACKOFF` | `float` | `16.0` | Default max backoff (seconds) |
| `MAX_OUTPUT_CHARS` | `int` | `200_000` | Default max combined output characters |
| `MAX_CONTINUATIONS` | `int` | `3` | Default max continuation calls |
| `PREAMBLE_PATTERNS` | `tuple[str, ...]` | See R9 | Known LLM preamble prefixes (for logging) |
| `PHASE_REQUIRED_SECTIONS` | `dict[str, tuple[str, ...]]` | See R3 | Per-phase required heading strings |
| `CLEAN_MARKDOWN_INSTRUCTION` | `str` | `"Output ONLY..."` | Shared clean-output instruction text |

## State Transitions

### LLM Call Lifecycle (per phase)

```text
IDLE → ASSEMBLING → CALLING → POSTPROCESSING → VALIDATING → COMPLETE
                        │              │              │
                        ▼              ▼              ▼
                    RETRYING      CONTINUING      RETRYING
                   (transient     (truncated      (missing
                    error)        output)         sections)
                        │              │              │
                        ▼              ▼              ▼
                    FAILED         CAPPED          DRAFT_SAVED
                (max retries)  (max continuations) (max retries)
```

### Mode Selection Logic

```text
--template-mode flag? ──Yes──▶ TEMPLATE MODE
       │ No
       ▼
LLMProvider available? ──No──▶ TEMPLATE MODE + warning
       │ Yes
       ▼
--dry-run-prompt flag? ──Yes──▶ DRY-RUN MODE (write .prompt.md)
       │ No
       ▼
LLM MODE (call provider)
```
