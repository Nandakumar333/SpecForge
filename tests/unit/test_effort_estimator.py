"""Tests for Feature 008 EffortEstimator."""

from __future__ import annotations

import pytest


def _make_step(category: str, default_effort: str = "M"):
    """Helper to create a minimal BuildStep for testing."""
    from specforge.core.task_models import BuildStep

    return BuildStep(
        order=1,
        category=category,
        description_template="Test",
        default_effort=default_effort,
        file_path_pattern="src/test/",
        depends_on=(),
        parallelizable_with=(),
    )


class TestEffortEstimatorBaseDefaults:
    """Base effort defaults from build sequence."""

    def test_scaffolding_is_s(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(_make_step("scaffolding", "S"), 1, 0) == "S"

    def test_domain_models_is_m(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(_make_step("domain_models", "M"), 1, 0) == "M"

    def test_service_layer_is_l(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(_make_step("service_layer", "L"), 1, 0) == "L"

    def test_integration_tests_is_xl(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(
            _make_step("integration_tests", "XL"), 1, 0,
        ) == "XL"


class TestEffortEstimatorFeatureBump:
    """Feature count bumps effort."""

    def test_domain_models_bumps_at_4_features(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(_make_step("domain_models", "M"), 4, 0) == "L"

    def test_service_layer_bumps_at_5_features(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(_make_step("service_layer", "L"), 5, 0) == "XL"

    def test_health_checks_stays_s_regardless(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(_make_step("health_checks", "S"), 10, 0) == "S"

    def test_no_bump_below_threshold(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(_make_step("domain_models", "M"), 2, 0) == "M"


class TestEffortEstimatorDependencyBump:
    """Dependency count bumps communication_clients."""

    def test_comm_clients_bumps_at_3_deps(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(
            _make_step("communication_clients", "M"), 1, 3,
        ) == "L"

    def test_comm_clients_no_bump_at_2_deps(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(
            _make_step("communication_clients", "M"), 1, 2,
        ) == "M"


class TestEffortEstimatorCap:
    """Effort never exceeds XL."""

    def test_xl_stays_xl(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        assert est.estimate(
            _make_step("integration_tests", "XL"), 10, 10,
        ) == "XL"

    def test_bump_capped_at_xl(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        # service_layer base L → bump at 5 features → XL (not beyond)
        result = est.estimate(_make_step("service_layer", "L"), 5, 0)
        assert result == "XL"


class TestEffortEstimatorDeterminism:
    """Same input always produces same output."""

    def test_deterministic(self) -> None:
        from specforge.core.effort_estimator import EffortEstimator

        est = EffortEstimator()
        step = _make_step("service_layer", "L")
        results = [est.estimate(step, 4, 2) for _ in range(10)]
        assert len(set(results)) == 1
