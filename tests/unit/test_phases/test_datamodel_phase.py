"""Unit tests for DatamodelPhase boundary scoping."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from specforge.core.architecture_adapter import (
    MicroserviceAdapter,
    ModularMonolithAdapter,
    MonolithAdapter,
)
from specforge.core.phases.datamodel_phase import DatamodelPhase
from specforge.core.result import Ok
from specforge.core.service_context import FeatureInfo, ServiceContext


def _ctx(tmp_path: Path, arch: str = "microservice") -> ServiceContext:
    return ServiceContext(
        service_slug="ledger-service",
        service_name="Ledger Service",
        architecture=arch,
        project_description="Finance app",
        domain="finance",
        features=(
            FeatureInfo("002", "accts", "Accounts", "Acct mgmt", "P1", "core"),
            FeatureInfo("003", "txns", "Transactions", "Txn mgmt", "P1", "core"),
        ),
        dependencies=(),
        events=(),
        output_dir=tmp_path / ".specforge" / "features" / "ledger-service",
    )


class TestDatamodelPhase:
    def test_microservice_isolated_scope(self, tmp_path: Path) -> None:
        phase = DatamodelPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        assert ctx["datamodel_context"]["entity_scope"] == "isolated"
        assert ctx["datamodel_context"]["shared_entities"] is False

    def test_monolith_module_scope(self, tmp_path: Path) -> None:
        phase = DatamodelPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "monolithic"), MonolithAdapter(), {}
        )
        assert ctx["datamodel_context"]["entity_scope"] == "module"
        assert ctx["datamodel_context"]["shared_entities"] is True

    def test_modular_monolith_strict_scope(self, tmp_path: Path) -> None:
        phase = DatamodelPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "modular-monolith"), ModularMonolithAdapter(), {}
        )
        dm = ctx["datamodel_context"]
        assert dm["entity_scope"] == "strict_module"
        assert dm["no_cross_module_db"] is True

    def test_post_render_creates_shared_entities_monolith(
        self, tmp_path: Path
    ) -> None:
        svc_ctx = _ctx(tmp_path, "monolithic")
        phase = DatamodelPhase()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Data Model")
        phase.run(svc_ctx, MonolithAdapter(), renderer, MagicMock(), {})
        shared = tmp_path / ".specforge" / "shared_entities.md"
        assert shared.exists()

    def test_post_render_creates_shared_entities_modular(
        self, tmp_path: Path
    ) -> None:
        svc_ctx = _ctx(tmp_path, "modular-monolith")
        phase = DatamodelPhase()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Data Model")
        phase.run(svc_ctx, ModularMonolithAdapter(), renderer, MagicMock(), {})
        shared = tmp_path / ".specforge" / "shared_entities.md"
        assert shared.exists()

    def test_post_render_no_shared_entities_microservice(
        self, tmp_path: Path
    ) -> None:
        svc_ctx = _ctx(tmp_path, "microservice")
        phase = DatamodelPhase()
        renderer = MagicMock()
        renderer.render.return_value = Ok("# Data Model")
        phase.run(svc_ctx, MicroserviceAdapter(), renderer, MagicMock(), {})
        shared = tmp_path / ".specforge" / "shared_entities.md"
        assert not shared.exists()

    def test_covers_all_features(self, tmp_path: Path) -> None:
        phase = DatamodelPhase()
        ctx = phase._build_context(
            _ctx(tmp_path, "microservice"), MicroserviceAdapter(), {}
        )
        assert len(ctx["features"]) == 2
