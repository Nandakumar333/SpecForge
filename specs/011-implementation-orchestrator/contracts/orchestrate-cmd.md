# CLI Contract: `specforge implement --all`

**Feature**: 011-implementation-orchestrator
**Date**: 2026-03-17
**Backward Compatibility**: Extends existing `specforge implement` command (Feature 009)

## Command Signature

```
specforge implement --all [--to-phase N] [--resume] [--mode MODE] [--max-fix-attempts N]
```

### New Flags (Feature 011)

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--all` | flag | `false` | Implement all services in dependency order with inter-phase verification |
| `--to-phase` | int | None | Limit execution to phases 0 through N (inclusive). Requires `--all` |

### Existing Flags (Feature 009, unchanged)

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--shared-infra` | flag | `false` | Build cross-service infrastructure only |
| `--resume` | flag | `false` | Resume from saved state |
| `--mode` | choice | `prompt-display` | Execution mode (`prompt-display` or `agent-call`) |
| `--max-fix-attempts` | int | 3 | Max auto-fix retry attempts per task |

### Mutual Exclusivity

- `--all` and `target` (positional) are mutually exclusive
- `--all` and `--shared-infra` are mutually exclusive
- `--to-phase` requires `--all`

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All phases completed successfully, integration passed |
| 1 | Implementation or verification failure (halted) |
| 2 | Argument/configuration error (bad flags, missing manifest, cycles) |

## Internal Interface Contracts

### IntegrationOrchestrator

```python
class IntegrationOrchestrator:
    def __init__(
        self,
        sub_agent_executor: SubAgentExecutor,
        shared_infra_executor: SharedInfraExecutor,
        contract_enforcer: ContractEnforcer,
        integration_test_runner: IntegrationTestRunner,
        integration_reporter: IntegrationReporter,
        project_root: Path,
    ) -> None: ...

    def execute(
        self,
        mode: ExecutionMode,
        resume: bool = False,
        phase_ceiling: int | None = None,
    ) -> Result[IntegrationReport, str]: ...
```

### PhaseExecutor

```python
class PhaseExecutor:
    def __init__(
        self,
        sub_agent_executor: SubAgentExecutor,
        project_root: Path,
    ) -> None: ...

    def run(
        self,
        phase: Phase,
        mode: ExecutionMode,
        skipped_services: frozenset[str] = frozenset(),
    ) -> Result[tuple[ServiceStatus, ...], str]: ...
```

### ContractEnforcer

```python
class ContractEnforcer:
    def __init__(self, project_root: Path, boundary_analyzer: BoundaryAnalyzer | None = None) -> None: ...

    def verify(
        self,
        implemented_services: tuple[str, ...],
        manifest: dict,
    ) -> Result[VerificationResult, str]: ...
```

### IntegrationTestRunner

```python
class IntegrationTestRunner:
    def __init__(self, project_root: Path) -> None: ...

    def run(
        self,
        services: tuple[str, ...],
        architecture: str,
    ) -> Result[IntegrationTestResult, str]: ...
```

### IntegrationReporter

```python
class IntegrationReporter:
    def __init__(
        self,
        renderer: TemplateRenderer,
        registry: TemplateRegistry,
    ) -> None: ...

    def generate(
        self,
        state: OrchestrationState,
        plan: OrchestrationPlan,
    ) -> Result[Path, str]: ...
```

### dependency_graph (pure functions)

```python
def build_graph(
    manifest: dict,
) -> Result[dict[str, tuple[str, ...]], str]: ...

def detect_cycles(
    graph: dict[str, tuple[str, ...]],
) -> tuple[tuple[str, ...], ...]: ...

def compute_phases(
    graph: dict[str, tuple[str, ...]],
) -> Result[tuple[Phase, ...], str]: ...
```

## Backward Compatibility

This feature ONLY adds new flags (`--all`, `--to-phase`) to the existing `implement` command. All existing functionality (single-service `implement <target>`, `--shared-infra`, `--resume`) is preserved unchanged. The `--all` flag is the sole entry point to the new orchestration logic.
