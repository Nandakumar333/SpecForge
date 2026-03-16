"""Unit tests for SpecifyPhase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    ModularMonolithAdapter,
    MonolithAdapter,
)
from specforge.core.phases.specify_phase import SpecifyPhase
from specforge.core.result import Ok
from specforge.core.service_context import (
    EventInfo,
    FeatureInfo,
    ServiceContext,
    ServiceDependency,
)


def _ctx(
    tmp_path: Path,
    arch: str = "microservice",
    num_features: int = 2,
) -> ServiceContext:
    feats = [
        FeatureInfo(f"{i:03d}", f"f{i}", f"Feature {i}", f"Desc {i}", "P1", "core")
        for i in range(1, num_features + 1)
    ]
    deps = (
        ServiceDependency("identity-service", "Identity", "sync-rest", True, "Auth"),
    ) if arch == "microservice" else ()
    events = (
        EventInfo("txn.created", "ledger-service", ("identity-service",), "Txn"),
    ) if arch == "microservice" else ()
    return ServiceContext(
        service_slug="ledger-service",
        service_name="Ledger Service",
        architecture=arch,
        project_description="Finance app",
        domain="finance",
        features=tuple(feats),
        dependencies=deps,
        events=events,
        output_dir=tmp_path,
    )


class TestSpecifyPhase:
    def test_microservice_includes_deps(self, tmp_path: Path) -> None:
        phase = SpecifyPhase()
        adapter = MicroserviceAdapter()
        ctx = phase._build_context(_ctx(tmp_path, "microservice"), adapter, {})
        assert "dependencies" in ctx
        assert len(ctx["dependencies"]) == 1

    def test_monolith_no_deps(self, tmp_path: Path) -> None:
        phase = SpecifyPhase()
        adapter = MonolithAdapter()
        ctx = phase._build_context(_ctx(tmp_path, "monolithic"), adapter, {})
        assert "module_context" in ctx

    def test_single_feature_no_subsections(self, tmp_path: Path) -> None:
        phase = SpecifyPhase()
        adapter = MonolithAdapter()
        ctx = phase._build_context(_ctx(tmp_path, "monolithic", 1), adapter, {})
        assert len(ctx["capabilities"]) == 1
        assert len(ctx["capabilities"][0]["features"]) == 1

    def test_four_features_grouped(self, tmp_path: Path) -> None:
        phase = SpecifyPhase()
        adapter = MonolithAdapter()
        ctx = phase._build_context(_ctx(tmp_path, "monolithic", 4), adapter, {})
        assert len(ctx["capabilities"]) >= 1

    def test_modular_monolith_context(self, tmp_path: Path) -> None:
        phase = SpecifyPhase()
        adapter = ModularMonolithAdapter()
        ctx = phase._build_context(
            _ctx(tmp_path, "modular-monolith"), adapter, {}
        )
        assert ctx["architecture"] == "modular-monolith"
        assert "strict_boundaries" in ctx

    def test_run_writes_artifact(self, tmp_path: Path) -> None:
        phase = SpecifyPhase()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Spec content")
        result = phase.run(
            _ctx(tmp_path, "microservice"),
            MicroserviceAdapter(),
            renderer,
            MagicMock(),
            {},
        )
        assert result.ok
        assert (tmp_path / "spec.md").exists()
