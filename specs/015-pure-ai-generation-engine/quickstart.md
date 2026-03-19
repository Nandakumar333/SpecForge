# Quickstart: Pure AI Content Generation Engine

**Feature**: 015-pure-ai-generation-engine

## What Changed

The `specforge specify` and `specforge decompose` commands now use the configured AI agent to generate all content (spec.md, research.md, data-model.md, edge-cases.md, plan.md, checklist.md, tasks.md) via direct LLM calls. Jinja2 template rendering is preserved as a `--template-mode` fallback and remains the only mechanism for `specforge init` scaffolding.

## Prerequisites

1. A project initialized with `specforge init` and an agent configured in `.specforge/config.json` (e.g., `"agent": "claude"`)
2. The agent's CLI tool installed and on PATH (e.g., `claude` CLI for Claude, `gh` for Copilot)
3. The CLI tool authenticated (e.g., `claude login` or `gh auth login`)

## Usage

### LLM-Powered Specify (default when agent configured)

```bash
# Generates all 7 artifacts using the configured LLM
specforge specify ledger-service

# Output:
# Generating specs for: ledger-service
# [spec] Calling claude... done (12.3s)
# [research] Calling claude... done (18.1s)
# [datamodel] Calling claude... done (8.7s)  ← parallel
# [edgecase] Calling claude... done (9.2s)   ← parallel
# [plan] Calling claude... done (15.4s)
# [checklist] Calling claude... done (7.8s)
# [tasks] Calling claude... done (22.1s)
# Pipeline complete. Output: .specforge/features/ledger-service/
```

### LLM-Powered Decompose

```bash
# LLM analyzes the description and proposes tailored features
specforge decompose "Personal Finance App" --arch microservice

# Output:
# Calling claude for feature decomposition... done (14.2s)
# Decomposed into 8 features across 3 services
# manifest.json written to .specforge/manifest.json
```

### Template Mode (backward-compatible)

```bash
# Force Jinja2 template rendering — no LLM calls
specforge specify --template-mode ledger-service
specforge decompose --template-mode "Personal Finance App"
```

### Prompt Debugging (dry-run)

```bash
# Write assembled prompts to .prompt.md files without calling the LLM
specforge specify --dry-run-prompt ledger-service

# Output:
# [spec] Wrote spec.prompt.md (12,340 chars, ~3,085 tokens)
# [research] Wrote research.prompt.md (18,200 chars, ~4,550 tokens)
# ...
# Dry run complete. No LLM calls made.
```

### Force Regeneration

```bash
# Regenerate all artifacts from scratch
specforge specify --force ledger-service

# Resume from a specific phase (template mode for that phase only)
specforge specify --from plan --template-mode ledger-service
```

## LLM Configuration

Optional `"llm"` block in `.specforge/config.json`:

```json
{
  "agent": "claude",
  "llm": {
    "token_budget": 100000,
    "timeout_seconds": 120,
    "max_retries": 3,
    "model": "claude-sonnet-4-20250514",
    "max_output_chars": 200000
  }
}
```

All fields are optional — defaults from `config.py` are used when absent.

## How to Add a New LLM Provider

1. **Define a command template** in `_AGENT_COMMAND_TEMPLATES` in `core/llm_provider.py`:

```python
_AGENT_COMMAND_TEMPLATES: dict[str, str] = {
    "claude": "claude -p --output-format text --system-prompt {system}",
    "my-agent": "my-agent generate --system {system} --model {model}",
    # ...
}
```

2. **If the new agent needs a custom invocation** (not subprocess-based), implement the `LLMProvider` protocol:

```python
from specforge.core.llm_provider import LLMProvider
from specforge.core.result import Ok, Err, Result

class MyAgentProvider:
    """LLMProvider implementation for MyAgent."""

    def __init__(self, timeout: int = 120, max_retries: int = 3) -> None:
        self._timeout = timeout
        self._max_retries = max_retries

    def call(self, system_prompt: str, user_prompt: str) -> Result[str, str]:
        # Your invocation logic here
        # Must return Ok(generated_text) or Err(error_description)
        ...

    def is_available(self) -> Result[None, str]:
        # Check if the agent's tool is reachable
        ...
```

3. **Register in `ProviderFactory`** — add a case in the factory's agent-to-provider mapping.

4. **Test**: Add unit tests in `tests/unit/test_llm_provider.py` covering:
   - `call()` returns `Ok` with valid output
   - `call()` returns `Err` on timeout
   - `call()` retries on transient errors
   - `is_available()` returns `Err` when CLI tool missing

## How to Customize Phase Prompts

### Override governance domains per phase

Add `"governance_phase_map"` to `config.json`:

```json
{
  "governance_phase_map": {
    "datamodel": ["database", "backend", "security", "api-design"],
    "edgecase": ["security", "testing", "backend", "performance"]
  }
}
```

### Inspect assembled prompts

Use `--dry-run-prompt` to see exactly what the LLM receives:

```bash
specforge specify --dry-run-prompt ledger-service
# Then inspect .specforge/features/ledger-service/spec.prompt.md
```

The `.prompt.md` file contains the full system prompt + user prompt with all context sources clearly delimited.

## Architecture Decision: Why Not a Single Generator Class?

The spec's user direction suggested a `pure_ai_generator.py` monolith. The plan instead extends `BasePhase` with dual-mode execution because:

1. **Each phase stays testable in isolation** — mock the provider, test the prompt construction per phase
2. **Existing parallel execution preserved** — datamodel + edgecase run in `ThreadPoolExecutor` unchanged
3. **Follows existing conventions** — `_build_context()` pattern extended with `_build_prompt()`, not replaced
4. **Clean Architecture maintained** — no god-class with 7 different prompt construction methods

The `PromptAssembler` handles the cross-cutting concern (constitution + governance + budgeting), while each phase owns its specific prompt context via `_build_prompt()`.

## Fallback Behavior

| Condition | Behavior |
|-----------|----------|
| `--template-mode` flag | Jinja2 templates, no LLM calls |
| No agent in config.json | Auto-fallback to template mode + warning |
| Agent is `"generic"` | Auto-fallback to template mode + warning |
| Agent has no provider mapping | Auto-fallback to template mode + warning |
| CLI tool not on PATH | Auto-fallback to template mode + warning with install hint |
| LLM call fails after retries | Phase fails with `Err`; raw output saved as `.draft.md` |
| Decompose LLM fails | Falls back to `DomainAnalyzer` rule-based path + warning |

## Key File Locations

| File | Purpose |
|------|---------|
| `src/specforge/core/llm_provider.py` | `LLMProvider` protocol + `SubprocessProvider` + `ProviderFactory` |
| `src/specforge/core/prompt_assembler.py` | Prompt construction with token budgeting |
| `src/specforge/core/phase_prompts.py` | 8 PhasePrompt definitions with Spec-Kit skeletons |
| `src/specforge/core/output_validator.py` | Per-phase required section validation |
| `src/specforge/core/output_postprocessor.py` | Preamble stripping + continuation + capping |
| `src/specforge/core/config.py` | New constants: `GOVERNANCE_PHASE_MAP`, `PHASE_REQUIRED_SECTIONS`, etc. |
| `src/specforge/core/phases/base_phase.py` | Dual-mode `run()` method |
