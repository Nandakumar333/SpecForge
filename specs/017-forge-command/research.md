# Research: Forge Command — Zero-Interaction Full Spec Generation

**Feature**: 017-forge-command
**Date**: 2026-03-19

## R1: httpx SSE Streaming for Anthropic Messages API

**Decision**: Use `httpx` (sync client) + `httpx-sse` for direct SSE streaming against the Anthropic Messages API (`POST /v1/messages` with `stream: true`). Do NOT use the official `anthropic` SDK — keep the dependency surface minimal.

**Rationale**: httpx does **not** handle SSE natively. Its `stream()` context manager gives `iter_lines()` / `iter_bytes()` / `iter_text()`, but you must parse `event:` and `data:` prefixes yourself. The `httpx-sse` package (by Florimondmanca) is a thin, well-maintained wrapper that adds `connect_sse()` / `aconnect_sse()` helpers. The resulting `EventSource` exposes `.iter_sse()` which yields objects with `.event`, `.data`, `.id`, `.retry` attributes — exactly matching the SSE spec fields. The official Anthropic Python SDK itself uses httpx internally, so using httpx directly matches the transport layer without pulling in the full SDK (which brings pydantic, tokenizers, etc.).

**Usage pattern** (sync):
```python
import httpx, json
from httpx_sse import connect_sse

with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)) as client:
    with connect_sse(
        client, "POST", "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8192,
            "stream": True,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        },
    ) as event_source:
        for sse in event_source.iter_sse():
            if sse.event == "content_block_delta":
                data = json.loads(sse.data)
                if data["delta"]["type"] == "text_delta":
                    text_chunk = data["delta"]["text"]
            elif sse.event == "message_delta":
                data = json.loads(sse.data)
                stop_reason = data["delta"].get("stop_reason")
                output_tokens = data["usage"]["output_tokens"]
            elif sse.event == "message_stop":
                break
            elif sse.event == "error":
                raise ApiError(json.loads(sse.data))
```

**Streaming event sequence** returned by Anthropic (in order):
1. `event: message_start` — contains Message object with empty content, includes `model`, `usage.input_tokens`
2. `event: content_block_start` — `index: 0`, `content_block: {type: "text", text: ""}`
3. `event: ping` — keepalive, safe to ignore
4. `event: content_block_delta` (repeated N times) — `delta: {type: "text_delta", text: "chunk"}` (also `thinking_delta` for extended thinking models)
5. `event: content_block_stop` — marks end of one content block
6. `event: message_delta` — `delta: {stop_reason: "end_turn"}`, `usage: {output_tokens: N}`
7. `event: message_stop` — final event, stream is complete

Each SSE event has the format:
```
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

```
Events are separated by `\r\n\r\n`. The `httpx-sse` library handles this parsing automatically.

**Alternatives considered**:
- Official `anthropic` SDK — full-featured but heavy dependency; pulls in pydantic, tokenizers, etc. Overkill when we only need Messages + streaming.
- Manual SSE parsing with `iter_lines()` — workable (~30 lines) but reinvents what `httpx-sse` already does correctly. Fragile with edge cases (multi-line data, retry fields, empty lines).
- `sseclient-py` — works with `requests` only, not httpx. Does not support POST+SSE pattern.

---

## R2: Anthropic Messages API Contract

**Decision**: Target `POST /v1/messages` with `anthropic-version: 2023-06-01`. This is the stable, current API version.

**Rationale**: Well-documented, stable contract with explicit error codes, rate-limit headers, and retry semantics.

### Request

```
POST https://api.anthropic.com/v1/messages
```

**Required headers**:
| Header | Value |
|---|---|
| `x-api-key` | The API key (e.g., `sk-ant-...`) |
| `anthropic-version` | `2023-06-01` |
| `content-type` | `application/json` |

**Request body** (streaming):
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 8192,
  "stream": true,
  "system": "You are a helpful assistant.",
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

### Response — Non-streaming
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "model": "claude-sonnet-4-20250514",
  "content": [{"type": "text", "text": "Hello!"}],
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 10, "output_tokens": 5}
}
```

### Response — Streaming
Content-Type: `text/event-stream`. See R1 for the complete event sequence.

### Rate-limit response headers
| Header | Description |
|---|---|
| `anthropic-ratelimit-requests-limit` | Max requests per minute |
| `anthropic-ratelimit-requests-remaining` | Remaining requests this window |
| `anthropic-ratelimit-requests-reset` | ISO-8601 timestamp when window resets |
| `anthropic-ratelimit-tokens-limit` | Max tokens per minute |
| `anthropic-ratelimit-tokens-remaining` | Remaining tokens this window |
| `anthropic-ratelimit-tokens-reset` | ISO-8601 timestamp when token window resets |
| `retry-after` | Seconds to wait (present on 429 responses) |
| `request-id` | Unique request identifier for debugging |

### Error codes
| HTTP Status | Error Type | Description | Retryable? |
|---|---|---|---|
| 400 | `invalid_request_error` | Malformed request body/params | No — fix request |
| 401 | `authentication_error` | Invalid or missing API key | No — fix key |
| 402 | `billing_error` | Billing/payment issue | No — fix billing |
| 403 | `permission_error` | Key lacks permission for resource | No — fix permissions |
| 404 | `not_found_error` | Resource not found | No — fix URL/model |
| 413 | `request_too_large` | Request exceeds 32 MB | No — reduce payload |
| 429 | `rate_limit_error` | Rate limit exceeded (RPM, ITPM, or OTPM) | Yes — honor `retry-after` header |
| 500 | `api_error` | Anthropic internal error | Yes — exponential backoff |
| 529 | `overloaded_error` | API overloaded (all users); not billed | Yes — exponential backoff |

**Error response body format**:
```json
{
  "type": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit reached. Please retry after 30 seconds."
  }
}
```

**Retry strategy**: For 429, parse `retry-after` header and sleep that many seconds. For 500/529, use exponential backoff starting at 1s with jitter, capped at 60s, max 3 retries. 529 requests are not billed.

**Alternatives**: None meaningful — this is the only direct Anthropic API. AWS Bedrock offers an alternative endpoint but requires AWS auth and a different contract.

---

## R3: httpx vs requests vs urllib

**Decision**: Use `httpx` in sync mode. HTTP/2 is NOT needed (do not install `httpx[http2]`).

**Rationale**:

| Feature | httpx | requests | urllib (stdlib) |
|---|---|---|---|
| Sync API | Yes — nearly identical to requests | Yes | Yes but verbose |
| Async API | Yes (same codebase) | No | No |
| HTTP/2 | Yes (`pip install httpx[http2]`) | No | No |
| Streaming | `client.stream()` context manager | `stream=True` on response | Manual chunked read |
| SSE support | Via `httpx-sse` | Via `sseclient-py` (GET only) | Manual |
| Default timeouts | Yes (5s each for connect/read/write/pool) | **No defaults** — hangs forever | No defaults |
| Connection pooling | Built-in with `Client()` | Via `Session()` | No |
| Requests compat | ~95% drop-in | N/A | N/A |

**Key advantages for this project**:
1. **Default timeouts** — requests has no timeout by default, dangerous for CLI tools that must not hang.
2. **Streaming context manager** — `with client.stream("POST", ...) as response:` ensures proper resource cleanup.
3. **httpx-sse compatibility** — the only SSE library that works with httpx and supports POST+SSE (required for Anthropic's streaming API).
4. **Future-proof** — if we later need async (e.g., parallel API calls), httpx supports it with the same API surface.

**Timeout configuration**:
```python
client = httpx.Client(
    timeout=httpx.Timeout(
        connect=10.0,   # connection establishment
        read=120.0,     # waiting for response data (long for LLM generation)
        write=10.0,     # sending request body
        pool=10.0,      # waiting for connection from pool
    )
)
```

**We do NOT need HTTP/2** — Anthropic's API works fine over HTTP/1.1, and HTTP/2 adds the `h2` dependency for no benefit in a serial CLI tool. If parallel API calls are needed later, HTTP/2 multiplexing could help, but `concurrent.futures` with multiple HTTP/1.1 connections is simpler.

**Alternatives considered**:
- `requests` — no default timeouts, no SSE library supporting POST streams, no async upgrade path. Would work but inferior.
- `urllib` — too low-level, no SSE support, verbose API. Only advantage is zero dependencies.
- `aiohttp` — async-only, requires event loop, overkill for a sync CLI.

---

## R4: Rich Live Dashboard Patterns

**Decision**: Use Rich `Live` with regenerated `Table` objects (not in-place row mutation) for the forge command's real-time progress dashboard. Use `ThreadPoolExecutor` for concurrent operations, with progress updates funneled through a thread-safe shared dict; only the main thread calls `live.update()`.

**Rationale**:

### Pattern: Regenerate Table on Each Tick

Rich's `Table` does not support updating or removing individual rows — you can only `add_row()`. The recommended pattern is to regenerate the entire `Table` object on each refresh cycle:

```python
from rich.live import Live
from rich.table import Table

def generate_table(tasks: dict[str, ServiceState]) -> Table:
    table = Table(title="Forge Progress")
    table.add_column("Service", style="cyan")
    table.add_column("Phase", style="bold")
    table.add_column("Status")
    table.add_column("Tokens", justify="right")
    for name, state in tasks.items():
        table.add_row(name, state.phase, state.status_icon, str(state.tokens))
    return table

with Live(generate_table(tasks), refresh_per_second=4) as live:
    while not all_done:
        time.sleep(0.25)
        live.update(generate_table(tasks))
```

### Thread Safety

- `Rich.Live.update()` internally uses a `threading.RLock` (as of Rich 13.x+). Calling it from any thread is technically safe.
- `Rich.Progress.update()` also uses an `RLock`, making per-task updates safe from worker threads.
- **Recommended pattern for concurrent.futures**: Worker threads update a shared `dict` (protected by `threading.Lock`). The main thread polls and regenerates the table. This avoids cross-thread Rich rendering calls entirely and is the cleanest separation.

### refresh_per_second

- Default is 4. For LLM streaming (tokens arrive ~20-50/s), `refresh_per_second=4` is sufficient — updating faster adds flicker without visual benefit.
- Set `refresh_per_second=2` if updates are infrequent (only phase transitions).

### Combining Live + Progress

Rich supports nesting Progress inside Live via `Live(Group(table, progress))`. Do NOT nest two `Live` contexts — Rich only supports one active Live display at a time.

**Alternatives considered**:
- Rich Progress only (no Table) — simpler but lacks the tabular layout needed to show per-service metadata (phase, tokens, timing).
- Direct table mutation with `threading.Lock` — even with locking, Rich's internal state can conflict during `Live.refresh()`. Queue/dict-based decoupling is cleaner.
- Textual TUI — full terminal app framework, massive overkill for a progress dashboard.

---

## R5: Structured Artifact Extraction from Markdown

**Decision**: Use **regex** for all structured extraction. No external markdown parser needed.

**Rationale**: The markdown files we parse are machine-generated by SpecForge's own Jinja2 templates. The heading structure, list formats, and ID patterns (e.g., `FR-001`, `UC-001`, `EC-001`) are deterministic and well-controlled.

**Why regex over a parser**:
1. **Controlled input** — templates produce predictable structure; no need for CommonMark-compliant parsing.
2. **Zero extra dependencies** — regex is stdlib.
3. **Simpler code** — extracting `## FR-001: Feature Title` is a one-liner, whereas a parser requires walking an AST and matching node types.
4. **Performance** — regex on files <100KB is effectively instant.

**Recommended patterns**:
```python
import re

# Feature requirement IDs and titles
# Matches: "- **FR-001**: User Authentication"
FR_PATTERN = re.compile(r"^-\s+\*\*FR-(\d{3})\*\*:\s+(.+)$", re.MULTILINE)

# User stories
# Matches: "### User Story 1 — Login Flow"
US_PATTERN = re.compile(r"^###\s+User\s+Story\s+(\d+)\s+[—-]\s+(.+)$", re.MULTILINE)

# Research decisions
# Matches: "## R1: HTTP API Provider"
RESEARCH_PATTERN = re.compile(r"^##\s+R(\d+):\s+(.+)$", re.MULTILINE)
DECISION_PATTERN = re.compile(r"^\*\*Decision\*\*:\s+(.+)$", re.MULTILINE)

# Entities under ## Entities heading
ENTITY_PATTERN = re.compile(r"^###\s+(\w+)", re.MULTILINE)

# Edge cases
# Matches: "### EC-001: Concurrent Login Attempts"
EC_PATTERN = re.compile(r"^###\s+EC-(\d{3}):\s+(.+)$", re.MULTILINE)

# Extract section content under a heading
def extract_section(md: str, heading: str, level: int = 2) -> str:
    hashes = "#" * level
    pattern = re.compile(
        rf"^{hashes}\s+{re.escape(heading)}\s*\n(.*?)(?=^{'#'{{1,{level}}}\s}|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(md)
    return match.group(1).strip() if match else ""
```

**When a parser becomes necessary**:
- If we ever parse **user-authored** freeform markdown with unpredictable structure.
- If we need to handle nested lists, tables, or inline formatting within extracted content.
- In that case, `markdown-it-py` is the best choice: fast, CommonMark-compliant, extensible, no transitive deps, ~50KB.

**Alternatives considered**:
- `markdown-it-py` — full CommonMark AST parser. Overkill for extracting from our own templates.
- `Python-Markdown` — older, extension-heavy, less suitable for AST walking.
- `mistune` — fast but less CommonMark-compliant.
- LLM-based extraction — accurate but absurdly expensive for a local CLI tool parsing its own output.

---

## R6: Enriched Prompt Architecture

**Decision**: Use Jinja2 enrichment templates (one per phase) that render 50-100 lines of detailed system instructions, prepended to the existing `PhasePrompt.system_instructions`.

**Rationale**: The existing `PhasePrompt` system instructions are 2-3 sentences. Enriched prompts need architecture-specific guidance, governance rules, quality thresholds, anti-patterns, and output examples. Jinja2 templates allow:
1. Parameterization by architecture type, governance rules, and service context
2. Template inheritance/reuse across phases
3. Auditability — templates are readable `.md.j2` files, not string concatenation

Integration approach: `EnrichedPromptBuilder` loads enrichment templates from `templates/base/enrichment/`, renders them with service context and governance data, and the result is prepended to `PhasePrompt.system_instructions` in `PromptAssembler.assemble()`. The existing `PhasePrompt` dataclass gains an optional `enrichment_template` field (the template filename).

**Alternatives considered**:
- Hardcoded strings in Python — rejected per constitution (Principle II: "All file generation MUST use Jinja2 templates").
- Separate enrichment config YAML — rejected as unnecessary indirection. Jinja2 templates are already the standard.

---

## R7: Auto-Initialization in Forge

**Decision**: Reuse existing `init` command logic in non-interactive mode, calling the core functions directly (not via Click).

**Rationale**: The forge command needs to auto-init when `.specforge/` doesn't exist (FR-003). Rather than shelling out to `specforge init --here`, we extract the core init logic:
1. Auto-detect agent via `detect_agent()` (no interactive prompt)
2. Auto-detect stack via `StackDetector.detect()`
3. Call `ProjectConfig.create()`, `build_scaffold_plan()`, `write_scaffold()`
4. Call `generate_governance_files()` and `_write_extended_config()`

This avoids subprocess overhead and the interactive prompts that `init` normally triggers when stdin is a TTY. The forge orchestrator calls these functions directly with auto-detected values.

**Alternatives considered**:
- `subprocess.run(["specforge", "init", "--here", "--agent", agent])` — rejected because it requires the CLI to be installed and adds subprocess overhead. Direct function calls are faster and avoid TTY detection issues.
- Skipping init entirely (require pre-existing `.specforge/`) — rejected per FR-003 which mandates auto-init for zero-interaction flow.

---

## R8: Provider Fallback Chain

**Decision**: ProviderFactory checks `ANTHROPIC_API_KEY` env var first. If present and agent is "claude", create `HttpApiProvider`. If key is invalid (detected on first call failure), fall back to `SubprocessProvider`. If no key, use `SubprocessProvider` for whatever agent is configured.

**Rationale**: The fallback chain needs to be:
1. `ANTHROPIC_API_KEY` set + agent is "claude" -> `HttpApiProvider` (fastest)
2. `ANTHROPIC_API_KEY` set but invalid -> `SubprocessProvider` with warning (FR-008)
3. No API key -> `SubprocessProvider` for configured agent (existing behavior, FR-018)

The invalid-key detection happens lazily on the first `call()` — we don't want to make a test API call during factory creation. Instead, `HttpApiProvider.call()` catches 401/403 errors and raises a specific exception that `ForgeOrchestrator` catches to trigger fallback.

**Alternatives considered**:
- Eager validation (test API call in factory) — rejected because it wastes an API call and adds latency to startup. Lazy detection is sufficient.
- Always prefer HTTP regardless of agent — rejected because HTTP provider only works with Anthropic API. Other agents (Copilot, Gemini, Codex) must use their CLI tools.

---

## R9: Token Budget Impact of Structured Extraction

**Decision**: ArtifactExtractor produces compressed structured summaries that are 30-50% smaller than raw artifact text while preserving all critical information.

**Rationale**: A typical spec.md is 3000-5000 characters. Raw concatenation of 3 prior artifacts (spec + research + datamodel) for the edgecase phase uses ~12,000 characters (~3,000 tokens). Structured extraction reduces this to:
- User stories: ~500 chars (bullet list of titles + acceptance scenario count)
- FR-IDs: ~300 chars (numbered list)
- Research decisions: ~400 chars (key-value pairs)
- Entity summaries: ~300 chars (entity names + field count + relationships)
- Total: ~1,500 chars (~375 tokens) — a 75% reduction

This meets SC-007 (30% reduction target) with significant margin. The LLM receives focused, structured context rather than full prose, which also improves output quality.

**Alternatives considered**:
- Full artifact text with truncation — rejected because truncation loses information at the end of documents, which often contains the most specific requirements.
- LLM-based summarization — rejected because it adds LLM calls and introduces non-determinism in the context assembly step.
