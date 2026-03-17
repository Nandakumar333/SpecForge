"""Unit tests for context_builder.py — isolated context assembly."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.service_context import ServiceContext, ServiceDependency


def _make_service_ctx(
    tmp_path: Path,
    slug: str = "ledger-service",
    arch: str = "microservice",
    deps: tuple[ServiceDependency, ...] = (),
) -> ServiceContext:
    """Helper to create a minimal ServiceContext."""
    from specforge.core.service_context import EventInfo, FeatureInfo

    return ServiceContext(
        service_slug=slug,
        service_name=slug.replace("-", " ").title(),
        architecture=arch,
        project_description="Test project",
        domain="finance",
        features=(
            FeatureInfo(
                id="001",
                name="core-feature",
                display_name="Core Feature",
                description="Core feature for testing",
                priority="P1",
                category="core",
            ),
        ),
        dependencies=deps,
        events=(),
        output_dir=tmp_path / "src" / slug,
    )


def _scaffold_service_artifacts(
    tmp_path: Path, slug: str = "ledger-service",
) -> None:
    """Write minimal spec artifacts for a service."""
    feature_dir = tmp_path / ".specforge" / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec for " + slug)
    (feature_dir / "plan.md").write_text("# Plan for " + slug)
    (feature_dir / "data-model.md").write_text("# Data model for " + slug)
    (feature_dir / "edge-cases.md").write_text("# Edge cases for " + slug)
    (feature_dir / "tasks.md").write_text("# Tasks for " + slug)


def _scaffold_constitution(tmp_path: Path) -> None:
    """Write a minimal constitution.md."""
    (tmp_path / "constitution.md").write_text("# Constitution\nSpec-first development.")


class TestContextBuilderBuild:
    """ContextBuilder.build() assembles isolated per-task context."""

    def test_loads_constitution(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver
        from specforge.core.task_models import TaskItem

        _scaffold_constitution(tmp_path)
        _scaffold_service_artifacts(tmp_path)
        svc_ctx = _make_service_ctx(tmp_path)
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        result = builder.build(svc_ctx, task)
        assert result.ok
        assert "Constitution" in result.value.constitution

    def test_missing_constitution_warns_not_error(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path)
        svc_ctx = _make_service_ctx(tmp_path)
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        result = builder.build(svc_ctx, task)
        assert result.ok
        assert result.value.constitution == ""

    def test_loads_all_five_spec_artifacts(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path)
        svc_ctx = _make_service_ctx(tmp_path)
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        result = builder.build(svc_ctx, task)
        assert result.ok
        ctx = result.value
        assert "Spec for ledger-service" in ctx.service_spec
        assert "Plan for ledger-service" in ctx.service_plan
        assert "Data model for ledger-service" in ctx.service_data_model
        assert "Edge cases for ledger-service" in ctx.service_edge_cases
        assert "Tasks for ledger-service" in ctx.service_tasks

    def test_includes_dependency_contracts(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path)
        # Set up identity-service contracts
        contracts_dir = tmp_path / ".specforge" / "features" / "identity-service" / "contracts"
        contracts_dir.mkdir(parents=True)
        (contracts_dir / "api-spec.json").write_text(
            json.dumps({"endpoint": "/auth"}), encoding="utf-8",
        )

        dep = ServiceDependency(
            target_slug="identity-service",
            target_name="Identity Service",
            pattern="sync-rest",
            required=True,
            description="Auth dependency",
        )
        svc_ctx = _make_service_ctx(tmp_path, deps=(dep,))
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        result = builder.build(svc_ctx, task)
        assert result.ok
        assert "identity-service" in result.value.dependency_contracts
        assert "/auth" in result.value.dependency_contracts["identity-service"]

    def test_excludes_files_outside_allowlist(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path)
        # Create another service's source code — MUST NOT appear in context
        other_src = tmp_path / ".specforge" / "features" / "planning-service" / "src"
        other_src.mkdir(parents=True)
        (other_src / "budget.py").write_text("class BudgetService: pass")

        svc_ctx = _make_service_ctx(tmp_path)
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        result = builder.build(svc_ctx, task)
        assert result.ok
        ctx = result.value
        # Context should contain NOTHING from planning-service
        assert "BudgetService" not in ctx.service_spec
        assert "BudgetService" not in ctx.service_plan
        assert "planning-service" not in ctx.dependency_contracts

    def test_microservice_adds_architecture_prompts(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path)
        svc_ctx = _make_service_ctx(tmp_path, arch="microservice")
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        result = builder.build(svc_ctx, task)
        assert result.ok
        # Microservice gets architecture-specific context
        assert result.value.architecture_prompts != ""

    def test_monolith_omits_architecture_prompts(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path, slug="auth-module")
        svc_ctx = _make_service_ctx(tmp_path, slug="auth-module", arch="monolithic")
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        result = builder.build(svc_ctx, task)
        assert result.ok
        assert result.value.architecture_prompts == ""

    def test_token_estimation(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path)
        svc_ctx = _make_service_ctx(tmp_path)
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        result = builder.build(svc_ctx, task)
        assert result.ok
        assert result.value.estimated_tokens > 0

    def test_truncation_removes_lowest_priority_first(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path)
        _scaffold_constitution(tmp_path)
        # Write a very large edge-cases.md to push over budget
        feature_dir = tmp_path / ".specforge" / "features" / "ledger-service"
        (feature_dir / "edge-cases.md").write_text("X" * 500_000)

        svc_ctx = _make_service_ctx(tmp_path)
        task = _make_task()

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )
        # Use a small budget to force truncation
        with patch("specforge.core.context_builder.CONTEXT_TOKEN_BUDGET", 100):
            result = builder.build(svc_ctx, task)

        assert result.ok
        ctx = result.value
        # Constitution and current task are NEVER truncated
        assert ctx.constitution != ""
        assert ctx.current_task != ""

    def test_per_task_current_task_varies(self, tmp_path: Path) -> None:
        from specforge.core.context_builder import ContextBuilder
        from specforge.core.contract_resolver import ContractResolver

        _scaffold_service_artifacts(tmp_path)
        svc_ctx = _make_service_ctx(tmp_path)

        task1 = _make_task(task_id="T001", desc="Create User model")
        task2 = _make_task(task_id="T002", desc="Create UserService")

        builder = ContextBuilder(
            project_root=tmp_path,
            prompt_loader=None,
            contract_resolver=ContractResolver(tmp_path),
        )

        r1 = builder.build(svc_ctx, task1)
        r2 = builder.build(svc_ctx, task2)

        assert r1.ok and r2.ok
        assert "Create User model" in r1.value.current_task
        assert "Create UserService" in r2.value.current_task
        assert r1.value.current_task != r2.value.current_task


# ── Helpers ──────────────────────────────────────────────────────────


def _make_task(
    task_id: str = "T001",
    desc: str = "Create TransactionService",
    layer: str = "service_layer",
) -> "TaskItem":
    from specforge.core.task_models import TaskItem

    return TaskItem(
        id=task_id,
        description=desc,
        phase=1,
        layer=layer,
        dependencies=(),
        parallel=False,
        effort="M",
        user_story="US1",
        file_paths=("src/services/transaction.py",),
        service_scope="ledger-service",
        governance_rules=(),
        commit_message=f"feat(ledger): {desc}",
    )
