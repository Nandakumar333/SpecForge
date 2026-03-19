# Feature Specification: Pure AI Content Generation Engine

**Feature Branch**: `015-pure-ai-generation-engine`
**Created**: 2026-03-19
**Status**: Draft
**Input**: User description: "Replace ALL Jinja2 template rendering with direct calls to the selected AI model (from config.json) so every .md file (spec.md, research.md, data-model.md, plan.md, checklist.md, edge-cases.md, tasks.md) is 100% written by the real LLM."

## Clarifications

### Session 2026-03-19

- Q: Should we add a `--template-fallback` flag for debugging, separate from `--template-mode`? → A: No. Keep `--template-mode` as the sole rendering-mode switch. Add `--dry-run-prompt` flag instead, which dumps the assembled prompt to a file without making LLM calls — this is the prompt debugging tool.
- Q: How to handle very long LLM outputs that exceed output token limits (e.g., tasks.md 5000+ lines)? → A: Multi-call continuation. Detect truncated output (missing required sections, incomplete trailing content), issue up to 3 continuation calls providing partial output as context and asking the LLM to continue. Cap total combined output at a configurable maximum length.
- Q: Should the prompt explicitly instruct "output ONLY Markdown, no explanations"? → A: Yes. All phase system prompts MUST include a clean-markdown-only instruction ("Output ONLY the Markdown document. No preamble, commentary, or conversational text."). FR-030 preamble stripping remains as a post-processing safety net.
- Q: How deep should governance prompts be injected per phase — all 7 domains always, or filtered by relevance? → A: Phase-relevant only. A `GOVERNANCE_PHASE_MAP` constant in `config.py` maps each pipeline phase to its relevant governance domain subset (e.g., spec → all domains; datamodel → database + backend + security; edgecase → security + testing + backend; plan → all domains; checklist → all domains; tasks → architecture + testing + cicd + security). Domain names MUST match `GOVERNANCE_DOMAINS` in `config.py`: architecture, backend, frontend, database, security, testing, cicd.
- Q: Should LLM-generated artifacts follow GitHub Spec-Kit template format exactly? → A: Yes. Each PhasePrompt MUST embed the exact Spec-Kit template skeleton (section headers, formatting conventions, ID formats like FR-001, SC-001, CHK-001, T001) as the target output structure, replacing generic structural guidance with precise format specifications.

## Assumptions

- The AI model is invoked via local CLI tools (e.g., `claude`, `copilot-cli`, `gemini`) or HTTP APIs. SpecForge does not embed model weights — it delegates to an external provider.
- The selected agent is already recorded in `.specforge/config.json` (via Feature 014 `specforge init`). This feature reads that config to determine which LLM provider to use.
- The existing `ContextBuilder` pattern (constitution + governance + architecture prompts + prior artifacts) is the proven context assembly approach and will be reused for prompt construction.
- Token budgets use character-based estimation consistent with the existing `CHARS_PER_TOKEN_ESTIMATE = 4` constant in `config.py`.
- Jinja2 templates remain the rendering mechanism for `specforge init` scaffolding (constitution, governance prompts, commands directory). Only content generation (the 7 pipeline artifacts + decompose feature list) moves to LLM.
- Each LLM provider has different invocation mechanisms; the `LLMProvider` abstraction must accommodate subprocess-based CLI tools, HTTP APIs, and stdin/stdout streaming patterns.
- The `AgentPlugin` base class is intentionally NOT extended with LLM calling capability. A separate `LLMProvider` protocol decouples agent configuration from model invocation.
- Retry and timeout defaults are conservative: 3 retries with exponential backoff, 120-second timeout. These are configurable but sensible for local CLI tool invocation latency.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — LLM-Powered Decompose (Priority: P1)

A developer runs `specforge decompose "Personal Finance App"` on a project initialized with a selected AI agent. Instead of the rule-based `DomainAnalyzer` producing canned feature lists from hardcoded `DOMAIN_PATTERNS`, the selected LLM analyzes the description and proposes a tailored feature list with service boundaries, dependency mappings, and architecture-appropriate groupings.

**Why this priority**: Decompose is the entry point of the entire pipeline. If it produces generic canned features, all downstream artifacts suffer. LLM-powered decomposition is the single highest-value change — it transforms SpecForge from a template filler into an intelligent design tool.

**Independent Test**: Can be fully tested by running `specforge decompose "Personal Finance App"` with a configured AI agent and verifying that the resulting `manifest.json` contains features specific to the description (not just generic domain patterns), with proper service mappings and dependency declarations.

**Acceptance Scenarios**:

1. **Given** a project with `config.json` containing `"agent": "claude"` and a valid LLM provider configured, **When** the user runs `specforge decompose "Personal Finance App"`, **Then** the LLM receives a prompt containing the constitution, governance rules, and the app description, and returns a structured feature decomposition.
2. **Given** the LLM returns a valid feature list, **When** the decompose command processes the response, **Then** `manifest.json` is written with features, service mappings, dependencies, and architecture type derived from the LLM output — not from hardcoded `DOMAIN_PATTERNS`.
3. **Given** `--arch microservice` is provided, **When** the prompt is constructed, **Then** the system prompt includes microservice-specific decomposition guidance (service isolation, bounded contexts, inter-service communication patterns).
4. **Given** `--arch monolithic` is provided, **When** the prompt is constructed, **Then** the system prompt includes monolith-specific guidance (module boundaries, shared infrastructure, no container orchestration).
5. **Given** the LLM is unreachable or returns an error, **When** the decompose command detects the failure, **Then** it falls back to the existing `DomainAnalyzer` rule-based decomposition and warns the user that template mode was used.

---

### User Story 2 — LLM-Powered Specify Pipeline (Priority: P1)

A developer runs `specforge specify ledger-service` and the pipeline generates all 7 artifacts (spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, tasks.md) using the selected LLM instead of Jinja2 template rendering. Each phase's prompt includes all prior artifacts so the LLM builds on its own previous output.

**Why this priority**: This is the core value proposition — every artifact is intelligently written by an LLM instead of being a filled-in template. Equally critical to Story 1 since decompose without specify is incomplete.

**Independent Test**: Can be fully tested by running `specforge specify ledger-service` with a configured AI agent and verifying that all 7 artifacts exist, contain substantive content (not template placeholders), and reference each other coherently.

**Acceptance Scenarios**:

1. **Given** a valid `manifest.json` and configured LLM provider, **When** `specforge specify ledger-service` is run, **Then** each of the 7 phases calls the LLM with a phase-specific prompt and writes the response as the artifact.
2. **Given** the spec phase completes producing `spec.md`, **When** the research phase runs, **Then** its prompt includes the full text of `spec.md` so the LLM can research topics specific to what it just specified.
3. **Given** the research phase completes, **When** data-model and edge-case phases run in parallel, **Then** both prompts include `spec.md` and `research.md` as context.
4. **Given** all prior artifacts exist, **When** `plan.md` is generated, **Then** its prompt includes spec.md, research.md, data-model.md, and edge-cases.md, and the resulting plan references entities and edge cases from those documents.
5. **Given** `--force` is used, **When** the pipeline runs, **Then** all 7 artifacts are regenerated from scratch via LLM calls.
6. **Given** the pipeline was interrupted after phase 2, **When** resumed, **Then** it loads existing artifacts as context and continues from the next incomplete phase.

---

### User Story 3 — Architecture-Aware Prompt Injection (Priority: P1)

A developer working on a microservice project runs the pipeline and receives artifacts that include Docker, gRPC, service mesh, and health check sections — not because of Jinja2 conditionals, but because the prompt explicitly instructs the LLM to include microservice-specific content. Monolith users receive module-boundary and shared-infrastructure guidance instead.

**Why this priority**: Architecture alignment is a core requirement from the user description. Without architecture-aware prompts, LLM output would be generic and miss critical deployment/communication concerns that the existing adapters currently inject.

**Independent Test**: Can be tested by running `specforge specify` for the same service under microservice and monolithic architectures and comparing the generated `plan.md` — microservice output must include containerization sections, monolith must not.

**Acceptance Scenarios**:

1. **Given** `manifest.json` declares `architecture: "microservice"`, **When** the plan phase prompt is constructed, **Then** it includes instructions to generate Docker configuration, health check endpoints, circuit breaker patterns, gRPC/REST inter-service communication, and service discovery sections.
2. **Given** `manifest.json` declares `architecture: "monolithic"`, **When** the plan phase prompt is constructed, **Then** it includes instructions to generate shared database setup, module boundary rules, and shared middleware — with no mention of containers or service mesh.
3. **Given** `manifest.json` declares `architecture: "modular-monolith"`, **When** prompts are constructed, **Then** they include module boundary enforcement AND interface contract definitions.
4. **Given** the existing `ArchitectureAdapter` implementations (Microservice, Monolith, ModularMonolith), **When** prompts are built, **Then** the adapter's context (dependencies, communication patterns, events) is serialized into the prompt text rather than passed as Jinja2 template variables.

---

### User Story 4 — Template Mode Fallback (Priority: P2)

A developer who does not want LLM-generated content (or has no LLM configured) runs `specforge specify --template-mode ledger-service` and the pipeline uses the existing Jinja2 template rendering path, producing the same output as before this feature was introduced.

**Why this priority**: Backward compatibility is essential. Users without LLM access, CI pipelines, and test environments must retain the deterministic template path. However, the primary value is in LLM mode, making this secondary.

**Independent Test**: Can be fully tested by running `specforge specify --template-mode ledger-service` and verifying artifacts are identical to those produced before this feature was implemented.

**Acceptance Scenarios**:

1. **Given** `--template-mode` flag is passed, **When** the pipeline runs, **Then** the existing `TemplateRenderer` + `TemplateRegistry` path is used for all 7 phases and no LLM calls are made.
2. **Given** no agent is configured in `config.json` (field missing or set to `"generic"` without LLM provider), **When** the pipeline runs without `--template-mode`, **Then** the system automatically falls back to template mode and warns the user.
3. **Given** `--template-mode` for decompose, **When** `specforge decompose --template-mode "Finance App"` is run, **Then** the existing `DomainAnalyzer` rule-based path is used.
4. **Given** template mode is active, **When** artifacts are generated, **Then** no behavioral changes occur relative to the pre-Feature-015 pipeline.

---

### User Story 5 — Token Budgeting and Safety (Priority: P2)

A developer specifying a large microservice project (10+ features per service) runs the pipeline and the system intelligently manages prompt size to stay within LLM context windows. Oversized context is prioritized and truncated gracefully, with the most relevant artifacts preserved and less critical sections summarized or omitted.

**Why this priority**: Without token budgeting, large projects will produce failed LLM calls or degraded output. Important for production use but the core generation path works without it for typical-sized projects.

**Independent Test**: Can be tested by creating a project with a very large manifest (20+ features mapped to one service) and verifying the prompt is truncated below the configured token budget while retaining the most critical context.

**Acceptance Scenarios**:

1. **Given** the total prompt (constitution + governance + prior artifacts + phase instructions) exceeds the configured token budget, **When** the prompt is assembled, **Then** it is trimmed according to a priority order: phase instructions (highest) > current service spec > prior phase artifacts > governance > constitution (lowest).
2. **Given** a prior artifact must be truncated, **When** it is included in the prompt, **Then** only the first N characters (within budget) are included, followed by a `[TRUNCATED — full document available in <path>]` marker.
3. **Given** the token budget is configurable in `config.json`, **When** a user sets `"token_budget": 50000`, **Then** all prompt assembly respects this limit.
4. **Given** a default token budget exists, **When** no override is configured, **Then** the system uses the existing `CONTEXT_TOKEN_BUDGET` constant (100,000 tokens).

---

### User Story 6 — Output Validation and Retry (Priority: P2)

A developer runs the pipeline and the LLM returns content missing a required section (e.g., plan.md without a "## File Structure" section). The system detects the structural deficiency, retries with a corrective prompt, and either recovers or reports the specific validation failure.

**Why this priority**: LLM output is non-deterministic. Without validation, malformed artifacts silently propagate through the pipeline, causing downstream phase failures or unusable specs. Essential for reliability but secondary to the core generation path.

**Independent Test**: Can be tested by mocking an LLM that returns incomplete content on first call and valid content on second, verifying the retry triggers and succeeds.

**Acceptance Scenarios**:

1. **Given** the LLM returns content for `spec.md`, **When** the output is validated, **Then** the validator checks for required sections: "## User Scenarios", "## Requirements", "## Success Criteria".
2. **Given** the LLM returns content for `plan.md`, **When** the output is validated, **Then** the validator checks for required sections: "## File Structure", "## Implementation Phases".
3. **Given** validation fails on the first attempt, **When** a retry is triggered, **Then** the retry prompt includes the original prompt plus a correction instruction specifying which sections are missing.
4. **Given** validation fails after the maximum retry count (3), **When** no valid output is produced, **Then** the phase fails with a descriptive error via `Result[T, E]` — the raw LLM output is saved as `<artifact>.draft.md` for manual inspection.
5. **Given** the LLM returns empty content or a connection error, **When** the failure is detected, **Then** the system retries with exponential backoff (1s, 2s, 4s) before reporting failure.

---

### User Story 7 — LLM Provider Abstraction (Priority: P1)

A developer using Claude CLI, Copilot CLI, or any supported agent can run the pipeline without changing code. The `LLMProvider` abstraction routes calls to the correct invocation mechanism based on the configured agent, supporting subprocess-based CLI tools and HTTP API clients.

**Why this priority**: Without a clean provider abstraction, every agent requires custom integration code scattered throughout the pipeline. This is the architectural foundation that enables Stories 1–3 to work across all 24+ agents.

**Independent Test**: Can be tested by configuring different agents in `config.json` and verifying the correct provider is instantiated and invoked via the protocol interface.

**Acceptance Scenarios**:

1. **Given** `config.json` specifies `"agent": "claude"`, **When** the pipeline starts, **Then** a Claude-specific `LLMProvider` implementation is instantiated that invokes the `claude` CLI tool.
2. **Given** `config.json` specifies `"agent": "copilot"`, **When** the pipeline starts, **Then** a Copilot-specific `LLMProvider` implementation is instantiated.
3. **Given** any `LLMProvider` implementation, **When** `call()` is invoked with a system prompt and user prompt, **Then** it returns a `Result[str, str]` containing the generated content or an error description.
4. **Given** the configured agent's CLI tool is not found on `PATH`, **When** the provider is instantiated, **Then** a clear error is returned explaining which tool is missing and how to install it.
5. **Given** `config.json` specifies `"agent": "generic"`, **When** no LLM provider mapping exists for "generic", **Then** the system falls back to template mode and warns the user that generic mode does not support LLM generation.

---

### Edge Cases

- What happens when the LLM returns markdown with different heading levels than expected (e.g., `###` instead of `##`)?
  → The `OutputPostprocessor` normalizes heading levels (e.g., `###` → `##`) to match the expected artifact structure before validation and final write, via a `normalize_headings()` method.
- What happens when the LLM includes preamble text before the actual content (e.g., "Here's the spec:" or "Sure, here is...")?
  → The output post-processor strips common LLM preamble patterns before the first markdown heading.
- What happens when the LLM returns content exceeding reasonable artifact size (e.g., 50,000+ words for a single spec.md)?
  → The validator enforces a configurable maximum output length and truncates with a warning if exceeded.
- What happens when the LLM injects code blocks or implementation details into a spec.md that should be technology-agnostic?
  → The output validator for spec-phase artifacts flags implementation-specific content (code blocks, framework names) as warnings in the pipeline output, but does not block generation.
- What happens when two pipeline runs occur simultaneously for different services that share dependencies?
  → The existing per-service lock file mechanism (`PIPELINE_LOCK_FILENAME`) prevents conflicts. Shared artifacts (e.g., `shared_entities.md`) use atomic writes via `os.replace()`.
- What happens when an LLM provider's CLI tool requires interactive authentication mid-pipeline?
  → The provider pre-validates authentication status before the first call. If authentication is required, the pipeline halts with a clear instruction to authenticate and retry.
- What happens when the LLM returns valid content but in a different language than expected (e.g., Chinese when English was expected)?
  → The system prompt explicitly specifies output language. No automatic language detection is performed — the user's LLM configuration determines language behavior.
- What happens when the pipeline is in AI mode but one specific phase fails repeatedly while others succeed?
  → The pipeline saves successful artifacts and records the failed phase in `.pipeline-state.json`. The user can resume from the failed phase via `--from <name>`. Per-phase template-mode override (e.g., `--from <name> --template-mode`) is not supported in v1 — `--template-mode` applies to the entire pipeline run.
- What happens when the LLM's response is cut off mid-sentence (token limit reached)?
  → The system detects truncation (missing required sections + incomplete trailing content) and issues up to 3 continuation calls (FR-040/FR-041), each providing the partial output and asking the LLM to continue. Total combined output is capped at `max_output_chars` (FR-042). If continuations exhaust without completing all required sections, the standard validation-retry flow (FR-028) takes over.
- What happens when `config.json` exists but has no `"agent"` field?
  → The pipeline defaults to template mode and warns the user to run `specforge init --here` to configure an agent.

## Requirements *(mandatory)*

### Functional Requirements

#### LLM Provider Abstraction

- **FR-001**: The system MUST define an `LLMProvider` protocol in `core/` with a `call(system_prompt: str, user_prompt: str) -> Result[str, str]` method that all provider implementations conform to.
- **FR-002**: The system MUST provide at least one concrete `LLMProvider` implementation that invokes an LLM via subprocess (CLI tool execution), supporting the `claude` CLI as the reference implementation.
- **FR-003**: The system MUST provide a `ProviderFactory` (or equivalent resolver) that reads `config.json`'s `"agent"` field and returns the corresponding `LLMProvider` implementation. If the agent has no registered provider, the factory MUST return an `Err` explaining that the agent does not support LLM generation.
- **FR-004**: Each `LLMProvider` implementation MUST validate that its required CLI tool or API endpoint is reachable before the first call and MUST return a descriptive `Err` if not (e.g., "claude CLI not found on PATH — install via `npm install -g @anthropic-ai/claude-cli`").
- **FR-005**: The `LLMProvider.call()` method MUST enforce a configurable timeout (default: 120 seconds) and MUST return an `Err` on timeout rather than hanging indefinitely.
- **FR-006**: The `LLMProvider.call()` method MUST support a configurable retry policy: maximum retry count (default: 3), exponential backoff base (default: 1 second), and maximum backoff (default: 16 seconds). Retries MUST only trigger on transient errors (timeout, connection failure), not on content validation failures.

#### Prompt Construction

- **FR-007**: The system MUST provide a `PromptAssembler` (or equivalent) in `core/` that constructs system prompts by combining constitution, governance prompts, architecture context, and previous phase artifacts into a single string.
- **FR-008**: The `PromptAssembler` MUST load constitution text from the project's `constitution.md` file via the existing governance loading mechanism.
- **FR-009**: The `PromptAssembler` MUST load governance prompts from `.specforge/prompts/` via the existing `PromptLoader` and `PromptContextBuilder`, filtered to only the domains relevant to the current phase according to the `GOVERNANCE_PHASE_MAP` constant in `config.py`. The spec, plan, and checklist phases include all governance domains; other phases include only their mapped subset to reduce token consumption.
- **FR-010**: The `PromptAssembler` MUST serialize architecture-specific context from the appropriate `ArchitectureAdapter` (Microservice, Monolith, ModularMonolith) into prompt text sections, replacing Jinja2 template conditionals with explicit prose instructions for the LLM.
- **FR-011**: The `PromptAssembler` MUST include the full text of all completed prior-phase artifacts in the system prompt, in pipeline order (spec → research → data-model → edge-cases → plan → checklist), so each phase can reference its predecessors.
- **FR-012**: The `PromptAssembler` MUST include a phase-specific instruction block (PhasePrompt) that tells the LLM exactly what kind of document to generate. Each PhasePrompt MUST embed the exact Spec-Kit template skeleton for its artifact type — including canonical section headers, ID formats (FR-001, SC-001, CHK-001, T001), and structural conventions — so that generated output is format-compatible with GitHub Spec-Kit templates.

#### Token Budgeting

- **FR-013**: The `PromptAssembler` MUST enforce a configurable token budget (default: `CONTEXT_TOKEN_BUDGET` from `config.py`, currently 100,000 tokens) using the existing `CHARS_PER_TOKEN_ESTIMATE` for measurement.
- **FR-014**: When the assembled prompt exceeds the token budget, the `PromptAssembler` MUST trim content in priority order: phase instructions (never trimmed) > current service artifacts > prior phase artifacts (newest first) > governance prompts > constitution (trimmed first).
- **FR-015**: Trimmed content MUST be truncated to the remaining character budget and appended with a `[TRUNCATED]` marker indicating the full document path.
- **FR-016**: The token budget MUST be overridable via a `"token_budget"` field in `.specforge/config.json`.

#### Content Generation — Decompose

- **FR-017**: When LLM mode is active, `specforge decompose` MUST construct a prompt containing the application description, architecture type, constitution, and governance rules, and call the LLM to produce a structured feature decomposition.
- **FR-018**: The LLM's decompose response MUST be parsed into the same data structures used by the existing `ManifestWriter` (features list, service mappings, dependencies, architecture type) so that `manifest.json` is written in the identical schema.
- **FR-019**: The decompose prompt MUST instruct the LLM to output a structured format (JSON or clearly delimited sections) that can be reliably parsed. The parser MUST handle minor formatting deviations (extra whitespace, trailing commas in JSON).
- **FR-020**: If the LLM's decompose response cannot be parsed into a valid feature list, the system MUST retry once with a corrective prompt specifying the exact expected format, then fall back to `DomainAnalyzer` if the retry also fails.

#### Content Generation — Specify Pipeline

- **FR-021**: When LLM mode is active, each of the 7 pipeline phases (spec, research, data-model, edge-cases, plan, checklist, tasks) MUST call the LLM via the `LLMProvider` instead of calling `TemplateRenderer.render()`.
- **FR-022**: The `BasePhase.run()` method MUST be extended (or an alternative AI-mode execution path provided) to support both template rendering and LLM generation, selected by a mode flag.
- **FR-023**: In LLM mode, the phase execution flow MUST be: `_build_prompt()` → `provider.call(system_prompt, user_prompt)` → `_validate_output()` → `_write_artifact()`.
- **FR-024**: Each phase MUST define its own PhasePrompt instructions that embed the corresponding Spec-Kit template skeleton as the expected output format. Specifically:
  - **spec phase**: Feature Branch/Created/Status/Input header → `## User Scenarios & Testing` (User Story N with Priority, Independent Test, Acceptance Scenarios in Given/When/Then) → `### Edge Cases` → `## Requirements` (FR-001 format + Key Entities) → `## Success Criteria` (SC-001 format).
  - **plan phase**: Branch/Date/Spec/Input header → `## Summary` → `## Technical Context` (Language, Dependencies, Storage, Testing, Platform, Project Type, Performance Goals, Constraints, Scale) → `## Constitution Check` (GATE) → `## Project Structure` (Documentation + Source Code) → `## Complexity Tracking`.
  - **tasks phase**: Input prerequisites header → `## Format` with `- [ ] T001 [P1] [US1] Description` checkbox format → `## Path Conventions` → Phase 1–N structure (Setup, Foundational, User Stories by priority, Polish) → `## Dependencies & Execution Order` → `## Implementation Strategy`.
  - **checklist phase**: Purpose/Created/Feature header → `## [Category N]` with CHK-001 format → `## Notes`.
  - **research/data-model/edge-cases phases**: Phase-specific Spec-Kit conventions for section headers and content structure.
- **FR-025**: The parallel execution of data-model and edge-case phases MUST be preserved in LLM mode, with each phase independently calling the LLM.

#### Output Validation

- **FR-026**: Each phase MUST define a set of required section headings for its artifact (e.g., spec.md requires `## User Scenarios`, `## Requirements`, `## Success Criteria`).
- **FR-027**: After receiving LLM output, the phase MUST validate that all required section headings are present in the content.
- **FR-028**: If required sections are missing, the phase MUST retry with a corrective prompt that lists the missing sections, up to the configured retry limit.
- **FR-029**: If validation fails after all retries, the phase MUST save the raw LLM output as `<artifact-name>.draft.md` alongside the expected artifact path for manual review, and return an `Err` result.
- **FR-030**: All phase system prompts MUST include a clean-markdown-only instruction: "Output ONLY the Markdown document content. Do not include any preamble, explanations, commentary, or conversational text before or after the document." Additionally, the output post-processor MUST strip any residual LLM preamble text (conversational prefixes before the first markdown heading) as a safety net, since LLMs may ignore formatting instructions non-deterministically.

#### Backward Compatibility

- **FR-031**: A `--template-mode` flag MUST be added to both `specforge decompose` and `specforge specify` commands that forces the existing Jinja2 template rendering path with no LLM calls.
- **FR-032**: When no LLM provider is available for the configured agent (including `"generic"` without a provider), the system MUST automatically fall back to template mode and emit a warning to stderr.
- **FR-033**: The existing `TemplateRenderer`, `TemplateRegistry`, and all Jinja2 `.md.j2` template files MUST remain in the codebase and fully functional — they are NOT removed or deprecated by this feature.
- **FR-034**: The `specforge init` scaffolding MUST continue to use Jinja2 templates exclusively. This feature does NOT modify the init command's rendering behavior.

#### Configuration

- **FR-035**: LLM mode MUST be the default when a supported agent is configured in `config.json`. Template mode MUST be the default when no agent is configured or the agent is `"generic"`.
- **FR-036**: The `.specforge/config.json` file MUST support an optional `"llm"` object with fields: `"token_budget"` (integer), `"timeout_seconds"` (integer), `"max_retries"` (integer), `"model"` (string, optional model name override for the provider), `"max_output_chars"` (integer, default 200,000 — maximum combined output length from initial call plus continuations).
- **FR-037**: Provider-specific configuration (API keys, custom endpoints, CLI paths) MUST be read from environment variables or the `"llm"` config object — never hardcoded.

#### Prompt Debugging

- **FR-038**: A `--dry-run-prompt` flag MUST be added to both `specforge decompose` and `specforge specify` commands. When set, the system assembles the full prompt for each phase and writes it to `<artifact-name>.prompt.md` in the feature directory, then exits without making any LLM calls. This is the primary prompt debugging tool.
- **FR-039**: The `--dry-run-prompt` flag MUST NOT be combinable with `--template-mode`. If both are passed, the CLI MUST reject the invocation with a clear error message.

#### Output Continuation for Long Responses

- **FR-040**: When the LLM's output is detected as truncated — defined as: (a) a required section heading from the PhasePrompt is missing, AND (b) the output ends mid-sentence or mid-section — the system MUST issue a continuation call. The continuation prompt provides the partial output and instructs the LLM to "continue the document from where it was cut off."
- **FR-041**: The system MUST support up to 3 continuation calls per phase. Each continuation appends to the previous partial output. After 3 continuations, if required sections are still missing, the system falls through to the standard validation-retry flow (FR-028).
- **FR-042**: The total combined output from initial call plus all continuations MUST be capped at a configurable `max_output_chars` (default: 200,000 characters, ~50,000 tokens). If this cap is reached, the system stops issuing continuations and proceeds to validation.

#### Governance Phase Mapping

- **FR-043**: The system MUST define a `GOVERNANCE_PHASE_MAP: dict[str, list[str]]` constant in `core/config.py` that maps each pipeline phase name to the list of governance domain names to include in that phase's prompt. Domain names MUST match the existing `GOVERNANCE_DOMAINS` constant (architecture, backend, frontend, database, security, testing, cicd). Phase keys MUST use non-hyphenated names matching codebase convention. The default mapping MUST be: spec → all domains, research → all domains, datamodel → [database, backend, security], edgecase → [security, testing, backend], plan → all domains, checklist → all domains, tasks → [architecture, testing, cicd, security], decompose → all domains.
- **FR-044**: The `GOVERNANCE_PHASE_MAP` MUST be overridable via a `"governance_phase_map"` field in `.specforge/config.json`, allowing users to customize which governance domains apply to each phase.

#### Spec-Kit Template Alignment

- **FR-045**: Each PhasePrompt instruction block MUST include the full Spec-Kit template skeleton for its artifact type as an explicit "Target Format" section within the system prompt. The skeleton MUST include all required section headers, ID format patterns, and structural conventions verbatim from the Spec-Kit templates.
- **FR-046**: The OutputValidator required-sections list for each phase (FR-026) MUST be derived from the corresponding Spec-Kit template skeleton, ensuring validation enforces Spec-Kit format compliance.
- **FR-047**: For the `constitution.md` template (used by `specforge init`, not LLM-generated), the Jinja2 template MUST be updated to match the Spec-Kit constitution-template format: `## Core Principles` (5 principles), custom sections, `## Governance` with Version/Ratified/Last Amended.
- **FR-048**: For the `agent-file` template (CLAUDE.md / similar), the Jinja2 template MUST be updated to match the Spec-Kit agent-file-template format: `## Active Technologies`, `## Project Structure`, `## Commands`, `## Code Style`, `## Recent Changes`.

### Key Entities

- **LLMProvider**: Protocol defining the interface for calling an LLM. Key method: `call(system_prompt, user_prompt) -> Result[str, str]`. Implementations exist per agent family (subprocess-based for CLI tools, HTTP-based for APIs). Encapsulates retry logic, timeout, and authentication validation.
- **PromptAssembler**: Constructs complete prompts for each pipeline phase by combining constitution, governance, architecture context, prior artifacts, and phase-specific instructions. Owns token budgeting. Replaces the role of Jinja2 context dictionaries for content generation.
- **ProviderFactory**: Resolves the configured agent name to the correct `LLMProvider` implementation. Returns `Err` for agents without LLM support. Reads `.specforge/config.json`.
- **OutputValidator**: Per-phase validation rules defining required sections, maximum length, and structural constraints for LLM-generated artifacts. Returns pass/fail with specific issues listed.
- **PhasePrompt**: Per-phase instruction block embedding the exact Spec-Kit template skeleton for its artifact type, specifying required section headers, ID formats (FR-001, SC-001, CHK-001, T001), and content guidelines. One per pipeline phase (7 total) plus one for decompose (8 total). Includes the clean-markdown-only instruction.
- **GOVERNANCE_PHASE_MAP**: Constant in `core/config.py` mapping each pipeline phase to its relevant governance domain subset. Reduces prompt token consumption by excluding irrelevant governance domains from phases that don't need them. Overridable via `config.json`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When LLM mode is active, 100% of pipeline artifacts (spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, tasks.md) are generated by the configured AI model with zero Jinja2 template rendering in the content path.
- **SC-002**: Generated artifacts for a microservice project contain architecture-specific sections (containerization, health checks, inter-service communication) in at least plan.md and tasks.md — verified by section heading presence.
- **SC-003**: Generated artifacts for a monolithic project contain NO microservice-specific sections (Docker, gRPC, service mesh) — verified by absence of those terms.
- **SC-004**: The `--template-mode` flag produces byte-identical output to the pre-Feature-015 pipeline for the same input, confirming zero regression in the template path.
- **SC-005**: When the LLM provider is unreachable, the system falls back to template mode within 10 seconds (timeout + detection) and completes the pipeline with a user-visible warning.
- **SC-006**: The LLM-powered decompose command produces a valid `manifest.json` with at least 3 distinct features for any non-trivial application description (e.g., "Personal Finance App"), each with service mappings and at least one dependency declaration.
- **SC-007**: Each pipeline phase's prompt successfully includes all prior-phase artifacts, verified by the prompt containing identifiable markers from each artifact.
- **SC-008**: Token budgeting correctly truncates prompts exceeding the budget — verified by prompt character count staying within `token_budget * CHARS_PER_TOKEN_ESTIMATE` for inputs that would otherwise exceed it.
- **SC-009**: Output validation catches missing required sections in LLM output and triggers a retry — verified by a mock LLM that returns incomplete content on first call and valid content on retry.
- **SC-010**: A full pipeline run (all 7 phases) completes in under 10 minutes for a typical service with 3–5 features, including all LLM round-trips.
- **SC-011**: Generated artifacts conform to Spec-Kit template format — verified by checking that spec.md contains `## User Scenarios & Testing`, `## Requirements` (with FR-NNN IDs), and `## Success Criteria` (with SC-NNN IDs); plan.md contains `## Technical Context` and `## Project Structure`; tasks.md contains `- [ ] T001` checkbox format and phase-based grouping.
- **SC-012**: The `--dry-run-prompt` flag writes prompt files for all phases without making LLM calls, and each prompt file contains the Spec-Kit template skeleton, governance context, and prior artifacts.
- **SC-013**: For a tasks.md exceeding 4,000 tokens of LLM output, the continuation mechanism successfully assembles the complete document across multiple LLM calls — verified by all required sections being present in the final output.
- **SC-014**: Governance prompts are phase-filtered — verified by confirming that the datamodel phase prompt contains database and backend governance but not frontend or cicd governance, while the plan phase prompt contains all governance domains.
