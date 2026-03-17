"""ContextBuilder — assembles per-task context with strict isolation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.config import (
    CHARS_PER_TOKEN_ESTIMATE,
    CONTEXT_PRIORITY,
    CONTEXT_TOKEN_BUDGET,
    FEATURES_DIR,
)
from specforge.core.executor_models import ExecutionContext
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.contract_resolver import ContractResolver
    from specforge.core.prompt_loader import PromptLoader
    from specforge.core.service_context import ServiceContext
    from specforge.core.task_models import TaskItem

logger = logging.getLogger(__name__)

# Architecture-specific context for microservice projects
_MICROSERVICE_PROMPTS = (
    "## Microservice Architecture Constraints\n"
    "- Each service runs in its own container\n"
    "- Inter-service communication via gRPC or REST\n"
    "- Event-driven messaging for async operations\n"
    "- Health check endpoint required at /health\n"
    "- Dockerfile required for each service\n"
    "- docker-compose.yml registers all services\n"
)


class ContextBuilder:
    """Assembles isolated per-task context for the sub-agent."""

    def __init__(
        self,
        project_root: Path,
        prompt_loader: PromptLoader | None,
        contract_resolver: ContractResolver,
    ) -> None:
        self._root = project_root
        self._prompt_loader = prompt_loader
        self._contract_resolver = contract_resolver

    def build(
        self,
        service_ctx: ServiceContext,
        task: TaskItem,
    ) -> Result[ExecutionContext, str]:
        """Assemble context for a single task. Called per-task."""
        constitution = self._load_constitution()
        governance = self._load_governance(task)
        artifacts = self._load_service_artifacts(service_ctx)
        if not artifacts.ok:
            return artifacts
        specs = artifacts.value
        contracts = self._load_contracts(service_ctx)
        arch_prompts = self._load_arch_prompts(service_ctx)
        current_task = f"[{task.id}] {task.description}"

        ctx = ExecutionContext(
            constitution=constitution,
            governance_prompts=governance,
            service_spec=specs["spec"],
            service_plan=specs["plan"],
            service_data_model=specs["data_model"],
            service_edge_cases=specs["edge_cases"],
            service_tasks=specs["tasks"],
            current_task=current_task,
            dependency_contracts=contracts,
            architecture_prompts=arch_prompts,
        )
        ctx = self._apply_token_budget(ctx)
        return Ok(ctx)

    def _load_constitution(self) -> str:
        """Load constitution.md — warn if missing, never block."""
        path = self._root / "constitution.md"
        if not path.exists():
            logger.warning("constitution.md not found at %s", path)
            return ""
        return path.read_text(encoding="utf-8")

    def _load_governance(self, task: TaskItem) -> str:
        """Build governance prompts via PromptContextBuilder."""
        if self._prompt_loader is None:
            return ""
        try:
            from specforge.core.prompt_context import PromptContextBuilder

            result = self._prompt_loader.load_for_feature("")
            if not result.ok:
                logger.warning("Failed to load governance: %s", result.error)
                return ""
            return PromptContextBuilder.build(
                result.value, task_domain=task.layer,
            )
        except Exception as exc:
            logger.warning("Governance loading failed: %s", exc)
            return ""

    def _load_service_artifacts(
        self, service_ctx: ServiceContext,
    ) -> Result[dict[str, str], str]:
        """Load the 5 required spec artifacts for the service."""
        slug = service_ctx.service_slug
        feature_dir = self._root / FEATURES_DIR / slug
        artifacts: dict[str, str] = {}
        names = {
            "spec": "spec.md",
            "plan": "plan.md",
            "data_model": "data-model.md",
            "edge_cases": "edge-cases.md",
            "tasks": "tasks.md",
        }
        for key, filename in names.items():
            path = feature_dir / filename
            if path.exists():
                artifacts[key] = path.read_text(encoding="utf-8")
            else:
                artifacts[key] = ""
                logger.warning("Missing artifact: %s", path)
        return Ok(artifacts)

    def _load_contracts(
        self, service_ctx: ServiceContext,
    ) -> dict[str, str]:
        """Load dependency contracts — isolation enforced."""
        result = self._contract_resolver.resolve(service_ctx.dependencies)
        if result.ok:
            return result.value
        logger.warning("Contract loading failed: %s", result.error)
        return {}

    def _load_arch_prompts(
        self, service_ctx: ServiceContext,
    ) -> str:
        """Load architecture-specific prompts (microservice only)."""
        if service_ctx.architecture == "microservice":
            return _MICROSERVICE_PROMPTS
        return ""

    def _apply_token_budget(
        self, ctx: ExecutionContext,
    ) -> ExecutionContext:
        """Estimate tokens and truncate if over budget."""
        from dataclasses import replace

        sections = self._get_sections_by_priority(ctx)
        total_chars = sum(len(v) for v in sections.values())
        estimated = total_chars // CHARS_PER_TOKEN_ESTIMATE

        if estimated <= CONTEXT_TOKEN_BUDGET:
            return replace(ctx, estimated_tokens=estimated)

        logger.warning(
            "Context exceeds token budget: ~%d tokens (budget: %d). "
            "Truncating lowest-priority sections.",
            estimated, CONTEXT_TOKEN_BUDGET,
        )
        return self._truncate(ctx, sections, estimated)

    def _truncate(
        self,
        ctx: ExecutionContext,
        sections: dict[str, str],
        estimated: int,
    ) -> ExecutionContext:
        """Truncate lowest-priority sections to fit budget."""
        from dataclasses import replace

        field_map = {
            "edge_cases": "service_edge_cases",
            "architecture_prompts": "architecture_prompts",
            "dependency_contracts": None,
            "data_model": "service_data_model",
            "plan": "service_plan",
            "governance_prompts": "governance_prompts",
            "spec": "service_spec",
        }

        overages = estimated - CONTEXT_TOKEN_BUDGET
        updates: dict[str, str] = {}

        for key in CONTEXT_PRIORITY:
            if key in ("constitution", "current_task"):
                continue
            if overages <= 0:
                break
            content = sections.get(key, "")
            if not content:
                continue
            chars_to_remove = overages * CHARS_PER_TOKEN_ESTIMATE
            if chars_to_remove >= len(content):
                updates[key] = ""
                overages -= len(content) // CHARS_PER_TOKEN_ESTIMATE
                logger.warning("Truncated section '%s' entirely", key)
            else:
                keep = len(content) - chars_to_remove
                updates[key] = content[:keep] + "\n[TRUNCATED]"
                overages = 0

        kwargs: dict = {}
        for key, field_name in field_map.items():
            if key in updates and field_name is not None:
                kwargs[field_name] = updates[key]

        new_ctx = replace(ctx, **kwargs) if kwargs else ctx
        new_chars = sum(
            len(v) for v in self._get_sections_by_priority(new_ctx).values()
        )
        return replace(
            new_ctx,
            estimated_tokens=new_chars // CHARS_PER_TOKEN_ESTIMATE,
        )

    def _get_sections_by_priority(
        self, ctx: ExecutionContext,
    ) -> dict[str, str]:
        """Map context fields to priority keys."""
        contracts_str = "\n".join(ctx.dependency_contracts.values())
        return {
            "edge_cases": ctx.service_edge_cases,
            "architecture_prompts": ctx.architecture_prompts,
            "dependency_contracts": contracts_str,
            "data_model": ctx.service_data_model,
            "plan": ctx.service_plan,
            "governance_prompts": ctx.governance_prompts,
            "spec": ctx.service_spec,
            "constitution": ctx.constitution,
            "current_task": ctx.current_task,
        }
