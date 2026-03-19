# Research: Pure AI Content Generation Engine

**Feature**: 015-pure-ai-generation-engine
**Date**: 2026-03-19

## R1: LLM Invocation via Subprocess (CLI Tools)

**Decision**: Use `subprocess.run()` with `capture_output=True`, `text=True`, `timeout`, and `check=False` to invoke LLM CLI tools. System prompt passed via `--system-prompt` (or equivalent flag) and user prompt via stdin.

**Rationale**: All current agent CLI tools (claude, copilot, gemini, codex) accept prompts via stdin or command-line arguments and return generated text on stdout. `subprocess.run()` is synchronous, blocking, and returns a `CompletedProcess` with `stdout`, `stderr`, and `returncode` — ideal for the sequential phase execution model. The existing `agent_detector.py` already uses `shutil.which()` to validate CLI availability, so the pattern is proven.

**Alternatives considered**:
- `subprocess.Popen()` with streaming — rejected for initial implementation; adds complexity for a feature that runs one call per phase. Streaming can be added in a future iteration for real-time output display
- `asyncio.create_subprocess_exec()` — rejected because the pipeline is synchronous (ThreadPoolExecutor for parallel phases); async would require converting the entire pipeline
- HTTP API calls (e.g., Anthropic Python SDK) — rejected because it adds an external dependency; the subprocess approach works for all agents and stays within Clean Architecture's zero-external-deps rule for `core/`

**CLI invocation patterns by agent**:

| Agent | Command | System Prompt | User Prompt | Model Override |
|-------|---------|---------------|-------------|----------------|
| claude | `claude -p --output-format text` | `--system-prompt "<text>"` | stdin | `--model <name>` |
| copilot | `gh copilot suggest` | Not directly supported — embed in user prompt | stdin | N/A |
| gemini | `gemini chat` | `--system "<text>"` | stdin | `--model <name>` |
| codex | `codex --quiet` | System prompt as first message | stdin | `--model <name>` |

**Note**: The `SubprocessProvider` implementation will use a command template per agent stored in a config mapping, not hardcoded if/else chains. The `ProviderFactory` maps agent names to their command templates.

**Key implementation detail**: The `claude` CLI's `-p` flag (print mode) disables interactive features and outputs plain text. The `--output-format text` ensures no JSON wrapping. Combined with stdin piping, this gives clean text output suitable for direct artifact writing.

## R2: Token Budgeting for Multi-Phase Pipelines

**Decision**: Reuse the existing `CONTEXT_TOKEN_BUDGET` (100,000 tokens) and `CHARS_PER_TOKEN_ESTIMATE` (4 chars/token) constants from `config.py`. Apply priority-based trimming with the order: phase instructions (never trimmed) > current service spec > prior artifacts (newest first) > governance > constitution.

**Rationale**: The existing `ContextBuilder` (Feature 009) already implements character-based token estimation with `CHARS_PER_TOKEN_ESTIMATE = 4`. This is a rough approximation but consistent across the codebase. The 100K token budget matches Claude's context window and is conservative for other models. The priority order differs from `ContextBuilder`'s `CONTEXT_PRIORITY` because the specify pipeline has different concerns than the implementation executor.

**Alternatives considered**:
- `tiktoken` library for precise token counting — rejected because it adds an external dependency and is model-specific (OpenAI tokenizer). Character estimation is sufficient for budget enforcement where ±10% accuracy is acceptable
- Per-model token budgets — deferred to future iteration; the configurable `"token_budget"` in config.json allows users to tune per their model's context window
- Summarization of truncated content — rejected for v1; the `[TRUNCATED]` marker with file path is simpler and doesn't require an additional LLM call

**Priority order rationale**:
1. **Phase instructions** (PhasePrompt skeleton + clean-markdown instruction): Never trimmed — without these, the LLM produces unstructured output
2. **Current service spec/artifacts**: The current service's own spec.md and prior artifacts are the primary context
3. **Prior phase artifacts** (newest first): Plan needs edge-cases more than it needs spec.md; trimming oldest first preserves the most recent context chain
4. **Governance prompts** (filtered by `GOVERNANCE_PHASE_MAP`): Relevant domains only; already reduced by phase filtering
5. **Constitution** (trimmed first): The constitution is the most stable and least phase-specific context — the LLM can produce reasonable output even without the full constitution

**Budget calculation**:
```
max_chars = token_budget * CHARS_PER_TOKEN_ESTIMATE  # 100,000 * 4 = 400,000 chars
sections = [phase_instructions, service_spec, prior_artifacts, governance, constitution]
for section in reversed(sections):  # trim lowest-priority first
    if total_chars > max_chars:
        section.content = section.content[:remaining_budget] + "[TRUNCATED]"
```

## R3: Output Validation for LLM-Generated Structured Documents

**Decision**: Per-phase required sections defined in `PHASE_REQUIRED_SECTIONS` constant (dict mapping phase name to list of required heading strings). Validation is heading-level only (check for `## Section Name` presence), not content-level.

**Rationale**: LLM output is non-deterministic. Heading-level validation catches the most critical structural failures (missing Requirements section, missing User Scenarios) without being so strict that valid variations trigger false positives. The Spec-Kit template skeletons provide exact heading text, so matching is straightforward.

**Alternatives considered**:
- Regex-based content validation (e.g., check for `FR-\d+` patterns) — deferred to v2; heading presence is sufficient for structural integrity
- Schema-based validation (JSON Schema for LLM output) — rejected because the output is Markdown, not JSON; heading checks are the Markdown equivalent
- LLM-based validation ("is this a valid spec?") — rejected for circular dependency and cost; structural checks are deterministic and free

**Required sections per phase** (derived from Spec-Kit templates):

| Phase | Required Headings |
|-------|-------------------|
| spec | `## User Scenarios & Testing`, `## Requirements`, `## Success Criteria` |
| research | `## R1:` (at least one research section starting with R-prefix) |
| datamodel | `## Entity Diagram`, `## Entities` |
| edgecase | `## Edge Cases` |
| plan | `## Summary`, `## Technical Context`, `## Constitution Check`, `## Project Structure` |
| checklist | At least one `## ` section with `CHK-` prefixed items |
| tasks | `## Phase 1` (at least one phase heading), task checkbox format `- [ ] T` |

**Retry strategy**: On validation failure, construct a corrective prompt listing the specific missing sections. The retry prompt includes the original system prompt + the failed output + "The following required sections are missing: [list]. Please regenerate the document including all required sections." Maximum 3 retries (configurable via `config.json`).

**Draft fallback**: If all retries fail, save the raw output as `<artifact>.draft.md` and return `Err` with the validation failures listed. This lets the user manually fix the output.

## R4: Output Continuation for Long LLM Responses

**Decision**: Detect truncation by checking (a) missing required sections AND (b) content ending mid-sentence (no terminal punctuation or heading). Issue up to 3 continuation calls providing partial output + "Continue the document from where it was cut off." Cap total output at `MAX_OUTPUT_CHARS` (200,000 chars, ~50K tokens).

**Rationale**: Some phases (especially `tasks.md` for large services) can produce very long output that exceeds an LLM's output token limit. Continuation is more reliable than requesting a condensed version because truncated output is structurally incomplete — the LLM needs to finish what it started.

**Alternatives considered**:
- Splitting the phase into sub-calls (e.g., generate each task phase separately) — rejected for v1 because it changes the phase semantics and requires knowing the output structure in advance
- Streaming with real-time detection — rejected because `subprocess.run()` waits for completion; streaming would require `Popen` with incremental reads, adding significant complexity
- Increasing output token limit via CLI flags — partially applicable (`--max-tokens` on claude CLI) but doesn't solve the fundamental limit; continuation is needed as a safety net

**Continuation algorithm**:
```
output = initial_call()
for i in range(MAX_CONTINUATIONS):  # default: 3
    if len(output) >= MAX_OUTPUT_CHARS:
        break
    if not is_truncated(phase, output):
        break
    continuation = provider.call(
        system_prompt="Continue the document exactly from where it left off.",
        user_prompt=f"Partial document so far:\n\n{output}\n\nContinue from here."
    )
    output += "\n" + continuation
return output
```

**Truncation detection heuristics**:
1. Required section missing from `PHASE_REQUIRED_SECTIONS` → likely truncated
2. Content ends with incomplete line (no newline at end) → truncated mid-output
3. Last line is not a complete sentence (no `.`, `)`, `|`, or heading marker) → truncated mid-sentence
4. Content ends inside a code block (unclosed triple backticks) → truncated inside code

## R5: Subprocess Error Classification (Transient vs. Permanent)

**Decision**: Classify errors into transient (retry-eligible) and permanent (fail immediately) categories based on exit code and stderr content.

**Rationale**: Retrying a permanent error (e.g., "model not found") wastes time and provider resources. Retrying a transient error (e.g., rate limit) is likely to succeed. The retry policy (FR-006) specifies retries "only on transient errors."

**Classification**:
- **Transient** (retry): exit code timeout (124), stderr contains "rate limit", "connection", "timeout", "503", "429", "overloaded"
- **Permanent** (fail immediately): exit code 1 with "not found", "authentication", "invalid model", "permission denied"
- **Unknown** (retry once, then fail): any other exit code > 0

**Backoff schedule**: 1s, 2s, 4s (exponential with base 1, max 16s, configurable). Implemented via `time.sleep()` between subprocess calls.

## R6: Governance Phase Mapping Design

**Decision**: Define `GOVERNANCE_PHASE_MAP` as a `dict[str, list[str]]` in `config.py` mapping phase names to governance domain lists. The map is the single source of truth; `PromptAssembler` reads it to filter governance prompts per phase.

**Rationale**: Including all 7 governance domains in every phase prompt wastes tokens. The spec phase and plan phase need full governance context, but the data-model phase only needs database + API + naming guidance. Filtering reduces prompt size by 40-60% for focused phases.

**Default mapping** (from FR-043):
```python
GOVERNANCE_PHASE_MAP: dict[str, list[str]] = {
    "spec": GOVERNANCE_DOMAINS,          # all 7
    "research": GOVERNANCE_DOMAINS,       # all 7
    "datamodel": ["database", "backend", "security"],
    "edgecase": ["security", "testing", "backend"],
    "plan": GOVERNANCE_DOMAINS,           # all 7
    "checklist": GOVERNANCE_DOMAINS,      # all 7
    "tasks": ["architecture", "testing", "cicd", "security"],
    "decompose": GOVERNANCE_DOMAINS,      # all 7
}
```

**Override mechanism**: `config.json` optional field `"governance_phase_map"` is a dict with the same structure. Values are merged (not replaced) — a user can add domains to a phase but not remove defaults without replacing the entire entry.

## R7: Architecture Adapter Serialization for Prompts

**Decision**: Add `serialize_for_prompt() -> str` to the `ArchitectureAdapter` protocol. Each implementation converts its structured data (dependencies, events, communication patterns) into a prose text block suitable for LLM prompt injection.

**Rationale**: The existing adapter methods (`get_context()`, `get_plan_sections()`, etc.) return dictionaries designed for Jinja2 template variable substitution. LLM prompts need prose instructions, not dict keys. A dedicated serialization method keeps the existing template path untouched while providing the LLM path with proper context.

**Serialization examples**:

**MicroserviceAdapter**:
```text
## Architecture: Microservice

This service is part of a microservice architecture with the following constraints:
- Each service runs in its own Docker container with a Dockerfile
- Inter-service communication: [list dependency patterns — REST, gRPC, async events]
- Dependencies: [list service dependencies with pattern and description]
- Events produced: [list] / Events consumed: [list]
- Required: health check endpoint at /health, readiness probe, container orchestration config
- Service isolation: no shared database; use API contracts for cross-service data access
```

**MonolithAdapter**:
```text
## Architecture: Monolithic

This module is part of a monolithic application with the following constraints:
- Shared database with other modules; define clear schema boundaries
- Module boundaries enforced via interface contracts, not network calls
- No Docker, no service mesh, no container orchestration
- Shared middleware, authentication, and configuration
- Use internal module imports, not HTTP/gRPC for cross-module communication
```

## R8: Provider Configuration and Agent-to-Provider Mapping

**Decision**: The `ProviderFactory` maps agent names to command templates. The mapping is a dict in `llm_provider.py`, not in `config.py`, because it's provider implementation detail, not a domain constant.

**Rationale**: The 24+ agent plugins exist for _configuration generation_ (agent files, commands directories). Only a subset have CLI tools that can be invoked for LLM generation. The provider factory maps agent names to their CLI invocation commands, defaulting to `Err("Agent '{name}' does not have an LLM provider")` for agents without CLI tools.

**Initial provider support**:

| Agent | Provider | CLI Command Template | Notes |
|-------|----------|---------------------|-------|
| claude | `SubprocessProvider` | `claude -p --output-format text --system-prompt "{system}" --model {model}` | stdin for user prompt |
| copilot | `SubprocessProvider` | `gh copilot suggest -t text` | System prompt embedded in user prompt |
| gemini | `SubprocessProvider` | `gemini chat --system "{system}" --model {model}` | stdin for user prompt |
| codex | `SubprocessProvider` | `codex --quiet` | System + user concatenated |
| generic | N/A | N/A | Falls back to template mode |
| *others* | N/A | N/A | Falls back to template mode with warning |

**Config resolution order**:
1. `config.json` → `"llm"` → `"cli_command"` (explicit override)
2. `config.json` → `"agent"` → built-in command template mapping
3. Fallback to template mode if no provider available

## R9: Preamble Stripping Patterns

**Decision**: Strip common LLM conversational prefixes using a regex that matches text before the first markdown heading (`# ` or `## `). Preserve all content from the first heading onward.

**Rationale**: Despite the system prompt instruction "Output ONLY the Markdown document," LLMs frequently prepend conversational text like "Here's the spec:", "Sure, I'll generate...", "Based on the requirements...". This is a safety net (FR-030), not the primary mechanism — the system prompt is the primary mechanism.

**Stripping algorithm**:
```python
import re

def strip_preamble(content: str) -> str:
    match = re.search(r'^#{1,6}\s', content, re.MULTILINE)
    if match:
        return content[match.start():]
    return content  # no heading found — return as-is
```

**Known preamble patterns** (for logging/metrics, not for matching):
- `"Here's the..."`, `"Sure, "`, `"Based on..."`, `"I'll generate..."`, `"Below is..."`, `"Certainly!"`, `"Of course!""`
