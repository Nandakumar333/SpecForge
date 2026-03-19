"""PipelineOrchestrator — coordinates phase execution for a service."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.architecture_adapter import create_adapter
from specforge.core.config import (
    CONTRACTS_DIR,
    FEATURES_DIR,
    PIPELINE_LOCK_FILENAME,
    PIPELINE_STATE_FILENAME,
    STUB_CONTRACT_SUFFIX,
)
from specforge.core.phases.base_phase import BasePhase
from specforge.core.phases.checklist_phase import ChecklistPhase
from specforge.core.phases.datamodel_phase import DatamodelPhase
from specforge.core.phases.edgecase_phase import EdgecasePhase
from specforge.core.phases.plan_phase import PlanPhase
from specforge.core.phases.research_phase import ResearchPhase
from specforge.core.phases.specify_phase import SpecifyPhase
from specforge.core.phases.tasks_phase import TasksPhase
from specforge.core.pipeline_lock import acquire_lock, is_stale, release_lock
from specforge.core.pipeline_state import (
    create_initial_state,
    detect_interrupted,
    is_phase_complete,
    load_state,
    mark_complete,
    mark_failed,
    mark_in_progress,
    reset_all_phases,
    save_state,
)
from specforge.core.result import Err, Ok, Result
from specforge.core.service_context import load_service_context, resolve_target

if TYPE_CHECKING:
    from specforge.core.llm_provider import LLMProvider
    from specforge.core.output_postprocessor import OutputPostprocessor
    from specforge.core.output_validator import OutputValidator
    from specforge.core.prompt_assembler import PromptAssembler
    from specforge.core.template_registry import TemplateRegistry
    from specforge.core.template_renderer import TemplateRenderer


class PipelineOrchestrator:
    """Coordinates pipeline execution for a service."""

    def __init__(
        self,
        renderer: TemplateRenderer,
        registry: TemplateRegistry,
        prompt_context: str = "",
        provider: LLMProvider | None = None,
        assembler: PromptAssembler | None = None,
        validator: OutputValidator | None = None,
        postprocessor: OutputPostprocessor | None = None,
        dry_run_prompt: bool = False,
    ) -> None:
        self._renderer = renderer
        self._registry = registry
        self._prompt_context = prompt_context
        self._provider = provider
        self._assembler = assembler
        self._validator = validator
        self._postprocessor = postprocessor
        self._dry_run_prompt = dry_run_prompt

    def run(
        self,
        target: str,
        project_root: Path,
        force: bool = False,
        from_phase: str | None = None,
    ) -> Result:
        """Run the pipeline for a target service or feature number."""
        slug_result = resolve_target(target, project_root)
        if not slug_result.ok:
            return slug_result
        ctx_result = load_service_context(slug_result.value, project_root)
        if not ctx_result.ok:
            return ctx_result
        service_ctx = ctx_result.value
        return self._execute(service_ctx, force, from_phase)

    def _execute(
        self,
        service_ctx: object,
        force: bool,
        from_phase: str | None,
    ) -> Result:
        """Execute phases with lock, state, and error handling."""
        lock_path = service_ctx.output_dir / PIPELINE_LOCK_FILENAME
        if lock_path.exists():
            if not force and not is_stale(lock_path):
                return _lock_error(lock_path, service_ctx.service_slug)
            release_lock(lock_path)
        lock_result = acquire_lock(lock_path, service_ctx.service_slug)
        if not lock_result.ok:
            return lock_result
        try:
            return self._run_phases(service_ctx, force, from_phase)
        finally:
            release_lock(lock_path)

    def _run_phases(
        self,
        service_ctx: object,
        force: bool,
        from_phase: str | None,
    ) -> Result:
        """Load state, execute each phase, save state."""
        state_path = service_ctx.output_dir / PIPELINE_STATE_FILENAME
        state = _load_or_create_state(state_path, service_ctx.service_slug)
        state = detect_interrupted(state)
        if force:
            state = reset_all_phases(state)
        if from_phase:
            state = _reset_from_phase(state, from_phase)
        phases = _build_phase_list(self._prompt_context)
        artifacts: dict[str, str] = {}
        for phase in phases:
            if is_phase_complete(state, phase.name):
                artifacts.update(_load_existing_artifact(service_ctx, phase))
                continue
            if _is_parallel_pair(phase.name):
                state, artifacts = self._run_parallel_3(
                    service_ctx, state, phases, artifacts, state_path
                )
                continue
            state = mark_in_progress(state, phase.name)
            save_state(state_path, state)
            result = phase.run(
                service_ctx, _get_adapter(service_ctx),
                self._renderer, self._registry, artifacts,
                provider=self._provider,
                assembler=self._assembler,
                validator=self._validator,
                postprocessor=self._postprocessor,
                dry_run_prompt=self._dry_run_prompt,
            )
            if not result.ok:
                state = mark_failed(state, phase.name, result.error)
                save_state(state_path, state)
                return result
            state = mark_complete(
                state, phase.name, (str(result.value),)
            )
            save_state(state_path, state)
            artifacts[phase.name] = result.value.read_text(encoding="utf-8")
        _generate_api_spec(service_ctx)
        _generate_stub_contracts(service_ctx)
        return Ok(service_ctx.output_dir)

    def _run_parallel_3(
        self,
        service_ctx: object,
        state: object,
        phases: list[BasePhase],
        artifacts: dict[str, str],
        state_path: object,
    ) -> tuple:
        """Run datamodel and edgecase phases in parallel."""
        dm = _find_phase(phases, "datamodel")
        ec = _find_phase(phases, "edgecase")
        adapter = _get_adapter(service_ctx)
        state = mark_in_progress(state, "datamodel")
        state = mark_in_progress(state, "edgecase")
        save_state(state_path, state)
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_dm = pool.submit(
                dm.run, service_ctx, adapter,
                self._renderer, self._registry, artifacts,
                provider=self._provider,
                assembler=self._assembler,
                validator=self._validator,
                postprocessor=self._postprocessor,
                dry_run_prompt=self._dry_run_prompt,
            )
            fut_ec = pool.submit(
                ec.run, service_ctx, adapter,
                self._renderer, self._registry, artifacts,
                provider=self._provider,
                assembler=self._assembler,
                validator=self._validator,
                postprocessor=self._postprocessor,
                dry_run_prompt=self._dry_run_prompt,
            )
            res_dm = fut_dm.result()
            res_ec = fut_ec.result()
        for name, res in [("datamodel", res_dm), ("edgecase", res_ec)]:
            if res.ok:
                state = mark_complete(state, name, (str(res.value),))
                artifacts[name] = res.value.read_text(encoding="utf-8")
            else:
                state = mark_failed(state, name, res.error)
        save_state(state_path, state)
        return state, artifacts


def _generate_stub_contracts(service_ctx: object) -> None:
    """Generate stub contracts for unspecified dependencies (FR-050)."""
    if service_ctx.architecture != "microservice":
        return
    project_root = _find_project_root(service_ctx.output_dir)
    for dep in service_ctx.dependencies:
        dep_dir = project_root / FEATURES_DIR / dep.target_slug
        contracts_dir = dep_dir / CONTRACTS_DIR
        real_contract = contracts_dir / "api-spec.json"
        if real_contract.exists():
            continue
        stub_path = contracts_dir / f"api-spec{STUB_CONTRACT_SUFFIX}"
        if stub_path.exists():
            continue
        contracts_dir.mkdir(parents=True, exist_ok=True)
        stub = _build_stub(dep, service_ctx.service_slug)
        stub_path.write_text(
            json.dumps(stub, indent=2), encoding="utf-8"
        )


def _generate_api_spec(service_ctx: object) -> None:
    """Generate api-spec.json for the service itself (FR-049)."""
    if service_ctx.architecture != "microservice":
        return
    contracts_dir = service_ctx.output_dir / CONTRACTS_DIR
    contracts_dir.mkdir(parents=True, exist_ok=True)
    spec_path = contracts_dir / "api-spec.json"
    spec = {
        "service": service_ctx.service_slug,
        "stub": False,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "endpoints": _build_endpoints(service_ctx),
    }
    spec_path.write_text(
        json.dumps(spec, indent=2), encoding="utf-8"
    )


def _build_stub(dep: object, generated_by: str) -> dict:
    """Build a stub contract dict from a dependency."""
    return {
        "service": dep.target_slug,
        "stub": True,
        "generated_by": generated_by,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "endpoints": [
            {
                "method": "GET",
                "path": f"/{dep.target_slug}/resource",
                "description": f"Inferred from {dep.pattern} dependency",
                "request": {},
                "response": {"id": "string"},
            },
        ],
    }


def _build_endpoints(service_ctx: object) -> list[dict]:
    """Build endpoint list from service features."""
    endpoints: list[dict] = []
    for feat in service_ctx.features:
        endpoints.append({
            "method": "GET",
            "path": f"/{feat.name}",
            "description": feat.description,
            "request": {},
            "response": {"id": "string"},
        })
    return endpoints


def _find_project_root(output_dir: Path) -> Path:
    """Derive project root from output dir (.specforge/features/<slug>)."""
    return output_dir.parent.parent.parent


def _lock_error(lock_path: object, slug: str) -> Result:
    """Build lock error from existing lock file."""
    return Err(
        f"Pipeline lock exists for '{slug}'. "
        "Another pipeline may be running. Use --force to override."
    )


def _load_or_create_state(state_path: object, slug: str) -> object:
    """Load existing state or create initial."""
    result = load_state(state_path)
    if result.ok and result.value is not None:
        return result.value
    return create_initial_state(slug)


def _build_phase_list(prompt_context: str) -> list[BasePhase]:
    """Build the ordered list of phase runners."""
    return [
        SpecifyPhase(),
        ResearchPhase(),
        DatamodelPhase(),
        EdgecasePhase(),
        PlanPhase(prompt_context=prompt_context),
        ChecklistPhase(),
        TasksPhase(),
    ]


def _is_parallel_pair(phase_name: str) -> bool:
    """Check if this is the first of the parallel pair."""
    return phase_name == "datamodel"


def _find_phase(phases: list[BasePhase], name: str) -> BasePhase:
    """Find a phase by name."""
    for p in phases:
        if p.name == name:
            return p
    msg = f"Phase '{name}' not found"
    raise ValueError(msg)


def _get_adapter(service_ctx: object) -> object:
    """Create the correct adapter for the service's architecture."""
    return create_adapter(service_ctx.architecture)


def _load_existing_artifact(
    service_ctx: object, phase: BasePhase
) -> dict[str, str]:
    """Load content of an already-complete artifact."""
    path = service_ctx.output_dir / phase.artifact_filename
    if path.exists():
        return {phase.name: path.read_text(encoding="utf-8")}
    return {}


def _reset_from_phase(state: object, from_phase: str) -> object:
    """Reset phases from the specified phase onward."""
    from specforge.core.config import PIPELINE_PHASES
    from specforge.core.pipeline_state import PhaseStatus

    from_idx = PIPELINE_PHASES.index(from_phase) if from_phase in PIPELINE_PHASES else 0
    phases_to_reset = set(PIPELINE_PHASES[from_idx:])
    from dataclasses import replace

    new_phases = tuple(
        PhaseStatus(name=ps.name, status="pending")
        if ps.name in phases_to_reset
        else ps
        for ps in state.phases
    )
    return replace(state, phases=new_phases)
