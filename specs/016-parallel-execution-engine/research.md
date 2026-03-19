# Research: Parallel Execution Engine

**Feature**: 016-parallel-execution-engine
**Date**: 2026-03-19

## R1: ThreadPoolExecutor Concurrency Patterns for I/O-Bound Workloads

**Decision**: Use `concurrent.futures.ThreadPoolExecutor` with `as_completed()` for non-blocking result collection and `shutdown(cancel_futures=True)` for fail-fast cancellation.

**Rationale**: The workload is I/O-bound (each worker spawns a subprocess via `SubprocessProvider.call()` and blocks waiting for LLM response). ThreadPoolExecutor is ideal because: (1) no pickling overhead (shared memory), (2) GIL is released during `subprocess.run()` blocking calls, (3) `cancel_futures=True` (Python 3.9+) provides clean fail-fast semantics.

**Alternatives considered**:
- `ProcessPoolExecutor`: Would require all arguments to be picklable. `PipelineOrchestrator` holds `TemplateRenderer` (Jinja2 environment) and `SubprocessProvider` instances that are not trivially serializable. Added complexity without benefit for I/O-bound work.
- `asyncio`: Would require rewriting `SubprocessProvider.call()` to use `asyncio.create_subprocess_exec()`. Pervasive change across the codebase for marginal benefit over threads.
- `threading.Thread` (manual): ThreadPoolExecutor already provides future-based error propagation, `max_workers` limiting, and `shutdown()` semantics. Reimplementing would be unnecessary.

## R2: Thread-Safe State Persistence Strategy

**Decision**: Each service writes to its own `.pipeline-state.json` in its own directory. No cross-service state file contention. The `ProgressTracker` uses a single `threading.Lock` for its internal counters and writes the aggregated `parallel-state.json` atomically.

**Rationale**: The existing pipeline state architecture already provides per-service isolation (each service has its own `.specforge/features/<slug>/` directory). No changes needed to `save_state()` or `load_state()` — they already use `tempfile.NamedTemporaryFile` + `os.replace()` which is atomic on all platforms. The only shared state is the `ProgressTracker`, which uses a single lock for its in-memory counters and a separate atomic write for the JSON file.

**Alternatives considered**:
- `threading.RLock` per-service: Unnecessary since services already write to separate files.
- File-based inter-thread coordination (e.g., advisory locks): Over-engineering — threads within a single process don't need filesystem coordination.
- SQLite for state: Adds an external dependency for no benefit over atomic JSON writes.

## R3: Fail-Fast Cancellation Semantics

**Decision**: On `--fail-fast`, call `executor.shutdown(wait=False, cancel_futures=True)` and set a `threading.Event` that workers check between phases. Workers that are mid-LLM-call will complete their current phase but not proceed to the next.

**Rationale**: `cancel_futures=True` (Python 3.9+) prevents queued-but-not-started futures from executing. For already-running workers, we cannot safely kill a subprocess mid-call (would leave partial artifacts). Instead, workers check a shared `shutdown_event: threading.Event` between phases. If set, the worker marks its current phase as complete (since the LLM call finished) and returns early with a "cancelled" status.

**Alternatives considered**:
- `subprocess.Popen.kill()`: Killing the LLM subprocess mid-call risks orphaned processes and partial output. The LLM call takes 30-120 seconds; waiting for the current phase to complete is acceptable.
- Ignoring in-flight workers: Would waste API quota and leave unclear state.

## R4: Inline Console Progress Output

**Decision**: Use Rich's `Console.print()` (thread-safe) with structured prefix format: `"  [slug] phase_event [N/7]"`. No Rich `Progress` bars (they conflict with concurrent print output).

**Rationale**: Rich's `Console` is thread-safe when using `print()`. Progress bars (`rich.progress.Progress`) with `Live` display conflict with concurrent `print()` calls from multiple threads. Since the dashboard (`specforge status --watch`) provides rich progress visualization, the inline output during parallel execution should be simple log-style lines.

**Alternatives considered**:
- Rich `Progress` with `Live`: Requires all output to go through the `Live` context. Multiple threads calling `task.update()` works, but any `console.print()` outside the Live context causes display corruption.
- No inline output (dashboard only): Users need immediate feedback without opening a second terminal. The spec explicitly requires inline streaming (FR-017).
- Python `logging` module: Adds configuration overhead. Direct `console.print()` is simpler and matches existing SpecForge patterns.

## R5: --auto Flag Integration with Existing Decompose Flow

**Decision**: `--auto` bypasses three interactive points in `decompose_cmd.py`: (1) architecture selection prompt → uses LLM-suggested architecture from decompose response, (2) feature list confirmation → accepts LLM output directly, (3) over-engineering warning → suppresses (equivalent to `--no-warn`). No new LLM calls needed.

**Rationale**: The existing `_try_llm_decompose()` already asks the LLM to select architecture and discover features. The interactive prompts exist for human review. `--auto` simply skips those review gates, trusting the LLM output. This is consistent with CI/automation use cases where human review is deferred to spec artifact review.

**Alternatives considered**:
- Separate "auto-architecture" and "auto-features" flags: Over-fragmentation. Users who want automation want all-or-nothing; partial automation is confusing.
- Additional LLM call for architecture confidence scoring: Unnecessary complexity. The decompose LLM prompt already includes architecture rationale in its response.

## R6: Monolith Module Independence Model

**Decision**: Monolith modules are always treated as a single wave (all independent). Modular-monolith modules with `communication[]` entries use the same topological sort as microservices.

**Rationale**: In the manifest schema, monolithic architectures do not populate `communication[]` between modules (they share infrastructure). The dependency graph is empty, so `compute_phases()` returns a single wave. Modular-monolith architectures may have boundary-aware communication entries; if present, the graph is populated and waves are computed. This requires no special-casing — the existing `build_graph()` + `compute_phases()` handles both cases correctly.

**Alternatives considered**:
- Explicit `parallel_strategy` field in manifest: Adds schema complexity. The architecture type already implies the strategy.
- Manual dependency annotation for monolith modules: Violates the principle that monolith modules share infrastructure and are inherently independent.

## R7: Resume Semantics for Parallel Execution

**Decision**: On resume, load `parallel-state.json` to identify completed services. Filter them out. Re-run only services with `status != "completed"`. Each service's individual pipeline state handles phase-level resume via `detect_interrupted()`.

**Rationale**: Two-level resume: (1) parallel level — skip completed services entirely, (2) pipeline level — within a service, resume from the last completed phase. The existing `PipelineOrchestrator.run()` already handles phase-level resume via `detect_interrupted()` which resets `in-progress` phases to `pending`. No changes needed to the per-service pipeline.

**Alternatives considered**:
- Re-run all services on resume: Wasteful. A 6-service run that failed on service 5 should not re-run services 1-4.
- Checkpoint at wave granularity only: Too coarse. If 3 of 4 services in wave 2 completed, we should only re-run the 1 failed service.

## R8: SIGINT/Ctrl+C Graceful Shutdown

**Decision**: Register a `signal.signal(signal.SIGINT, handler)` that sets a `threading.Event`. Workers check this event between phases. The main thread calls `executor.shutdown(wait=True)` to collect in-progress results before exiting. On second SIGINT, force exit.

**Rationale**: Python's default SIGINT handler raises `KeyboardInterrupt` in the main thread. With `ThreadPoolExecutor`, this interrupts `executor.shutdown()` or `future.result()`. By catching SIGINT and converting it to an event, we allow workers to finish their current phase cleanly and persist state for resume.

**Alternatives considered**:
- Let `KeyboardInterrupt` propagate naturally: Workers may be mid-write, leaving corrupt state files. The main thread exception may not cleanly collect all future results.
- `atexit` handler: Does not fire on SIGINT by default. Less reliable than signal handler.
