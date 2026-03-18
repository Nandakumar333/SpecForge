# Quickstart: Project Status Dashboard

**Feature**: `012-project-status-dashboard`  
**Date**: 2026-03-18

## Prerequisites

- SpecForge project initialized (`specforge init`)
- Project decomposed (`specforge decompose`) — produces `manifest.json`
- At least one service with pipeline state (produced by `specforge specify/research/plan/tasks`)

## Basic Usage

### Terminal Dashboard (default)

```bash
# Show project-wide status in the terminal
specforge status
```

Displays:
1. Architecture badge: `[MICROSERVICE]`, `[MONOLITH]`, or `[MODULAR]`
2. Service status table with per-service lifecycle progress
3. Phase progress bars (microservice projects with orchestration state)
4. Quality summary panel (when quality reports exist)

### Generate Reports

```bash
# Generate shareable markdown report
specforge status --format markdown
# Output: .specforge/reports/status.md

# Generate machine-readable JSON for CI/CD
specforge status --format json
# Output: .specforge/reports/status.json

# Generate both reports simultaneously
specforge status --format markdown --format json
```

### Dependency Graph

```bash
# Show ASCII dependency graph in terminal
specforge status --graph

# Include Mermaid graph in markdown report
specforge status --format markdown --graph
```

### Watch Mode (live monitoring)

```bash
# Auto-refresh every 5 seconds (default)
specforge status --watch

# Custom refresh interval
specforge status --watch --interval 10

# Exit: Ctrl+C or when all services reach COMPLETE/FAILED
```

## Understanding the Output

### Service Status Labels

| Status | Meaning |
|--------|---------|
| **COMPLETE** | All lifecycle phases done, all quality checks pass |
| **IN PROGRESS** | Implementation tasks underway |
| **PLANNING** | Spec or plan in progress, no implementation yet |
| **NOT STARTED** | Service declared in manifest but no artifacts exist |
| **BLOCKED** | Dependencies in a prior phase are incomplete |
| **FAILED** | Implementation or quality checks failed |
| **UNKNOWN** | State files corrupted or unreadable |

### Architecture-Specific Columns

- **Microservice**: Shows Docker build status and contract test columns
- **Monolith**: Simpler table without Docker/contract columns
- **Modular Monolith**: Shows module boundary compliance instead of Docker

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No services in FAILED state |
| 1 | At least one service is FAILED |

Use exit codes in CI/CD: `specforge status --format json && deploy.sh`

## Integration with CI/CD

```yaml
# Example GitHub Actions step
- name: Check project status
  run: |
    specforge status --format json
    # status.json is at .specforge/reports/status.json
    
- name: Gate deployment on Phase 1
  run: |
    python -c "
    import json, sys
    data = json.load(open('.specforge/reports/status.json'))
    phase1 = next(p for p in data['phases'] if p['index'] == 0)
    sys.exit(0 if phase1['completion_percent'] == 100 else 1)
    "
```

## Development Notes

### Module Dependency Chain

```
status_cmd.py (CLI entry)
  → status_collector.py (reads state files)
    → status_models.py (data structures)
  → metrics_calculator.py (computes derived values)
    → status_models.py
  → dashboard_renderer.py (Rich terminal output)
    → status_models.py
  → report_generator.py (JSON + markdown files)
    → status_models.py
    → status-report.md.j2 (Jinja2 template)
  → graph_builder.py (dependency graph)
    → status_models.py
```

### Testing Strategy

```bash
# Run all tests for this feature
pytest tests/unit/test_status_*.py tests/unit/test_metrics_calculator.py tests/unit/test_graph_builder.py tests/integration/test_status_cmd.py -v

# Run with coverage
pytest tests/unit/test_status_*.py --cov=specforge.core.status_collector --cov=specforge.core.status_models --cov=specforge.core.metrics_calculator --cov-report=term-missing
```
