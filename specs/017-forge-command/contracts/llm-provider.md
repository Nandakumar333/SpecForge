# Contract: LLMProvider Protocol Extension

## Existing Protocol (unchanged)

```python
@runtime_checkable
class LLMProvider(Protocol):
    def call(self, system_prompt: str, user_prompt: str) -> Result[str, str]: ...
    def is_available(self) -> Result[None, str]: ...
```

## New Implementation: HttpApiProvider

### Constructor

```python
class HttpApiProvider:
    def __init__(
        self,
        api_key: str,                              # from ANTHROPIC_API_KEY env var
        model: str = "claude-sonnet-4-20250514",    # overridable via --model
        max_tokens: int = 8192,                     # max output tokens per call
        timeout: float = 120.0,                     # read timeout for streaming
        max_retries: int = 3,                       # retry count for transient errors
        backoff_base: float = 1.0,                  # exponential backoff base
        max_backoff: float = 16.0,                  # max backoff delay
        token_callback: Callable[[str], None] | None = None,  # streaming progress callback
    ) -> None: ...
```

### call() Contract

**Input**: system_prompt (str), user_prompt (str)
**Output**: Result[str, str] — Ok(full_text) or Err(error_message)

**Behavior**:
1. POST to `https://api.anthropic.com/v1/messages` with `stream: true`
2. Collect text from `content_block_delta` SSE events
3. Invoke `token_callback` with each text chunk (if set)
4. On `message_stop`, return Ok(accumulated_text)
5. On HTTP error: classify as transient or permanent
   - Transient (429, 500, 529): retry with exponential backoff
   - Permanent (401, 403, 400): return Err immediately
6. On timeout: retry as transient error

### is_available() Contract

**Output**: Result[None, str]
- Ok(None) if `api_key` is non-empty
- Err("ANTHROPIC_API_KEY not set") if empty

Note: Does NOT make a network call. Validity is checked lazily on first `call()`.

## ProviderFactory Changes

### Updated create() logic

```python
@staticmethod
def create(config_path: Path, model: str | None = None) -> Result[LLMProvider, str]:
    # 1. Read config.json for agent name
    # 2. If agent == "claude" and ANTHROPIC_API_KEY is set:
    #      return Ok(HttpApiProvider(api_key, model=model or config_model))
    # 3. Else: fall through to existing SubprocessProvider logic
    # 4. Check is_available() before returning
```

### Fallback Behavior

The `ForgeOrchestrator` handles provider fallback, not the factory:

```python
# In ForgeOrchestrator:
result = self._provider.call(system, user)
if not result.ok and self._is_auth_error(result.error):
    # Switch to SubprocessProvider for remainder of run
    self._provider = self._create_subprocess_fallback()
    result = self._provider.call(system, user)
```
