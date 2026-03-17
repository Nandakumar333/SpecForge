"""Tests for Feature 008 build sequence definitions."""

from __future__ import annotations


class TestMicroserviceBuildSequence:
    """MICROSERVICE_BUILD_SEQUENCE validation."""

    def test_has_14_steps(self) -> None:
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        assert len(MICROSERVICE_BUILD_SEQUENCE) == 14

    def test_sequential_order(self) -> None:
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        orders = [s.order for s in MICROSERVICE_BUILD_SEQUENCE]
        assert orders == list(range(1, 15))

    def test_step_categories(self) -> None:
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        expected = [
            "scaffolding", "domain_models", "database", "repository",
            "service_layer", "communication_clients", "controllers",
            "event_handlers", "health_checks", "contract_tests",
            "unit_tests", "integration_tests", "container_optimization",
            "gateway_config",
        ]
        actual = [s.category for s in MICROSERVICE_BUILD_SEQUENCE]
        assert actual == expected

    def test_step6_depends_on_step5(self) -> None:
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        step6 = MICROSERVICE_BUILD_SEQUENCE[5]
        assert step6.category == "communication_clients"
        assert 5 in step6.depends_on

    def test_step7_parallelizable_with_step6(self) -> None:
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        step7 = MICROSERVICE_BUILD_SEQUENCE[6]
        assert step7.category == "controllers"
        assert 6 in step7.parallelizable_with

    def test_step8_parallelizable_with_step6_and_7(self) -> None:
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        step8 = MICROSERVICE_BUILD_SEQUENCE[7]
        assert step8.category == "event_handlers"
        assert 6 in step8.parallelizable_with
        assert 7 in step8.parallelizable_with

    def test_default_effort_values(self) -> None:
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        efforts = {s.category: s.default_effort for s in MICROSERVICE_BUILD_SEQUENCE}
        assert efforts["scaffolding"] == "S"
        assert efforts["domain_models"] == "M"
        assert efforts["service_layer"] == "L"
        assert efforts["integration_tests"] == "XL"
        assert efforts["health_checks"] == "S"

    def test_all_steps_frozen(self) -> None:
        import pytest
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        for step in MICROSERVICE_BUILD_SEQUENCE:
            with pytest.raises(AttributeError):
                step.order = 99  # type: ignore[misc]

    def test_file_path_patterns_have_placeholder(self) -> None:
        from specforge.core.build_sequence import MICROSERVICE_BUILD_SEQUENCE

        for step in MICROSERVICE_BUILD_SEQUENCE:
            assert "{service}" in step.file_path_pattern or \
                step.file_path_pattern.startswith("infrastructure/")


class TestMonolithBuildSequence:
    """MONOLITH_BUILD_SEQUENCE validation."""

    def test_has_7_steps(self) -> None:
        from specforge.core.build_sequence import MONOLITH_BUILD_SEQUENCE

        assert len(MONOLITH_BUILD_SEQUENCE) == 7

    def test_sequential_order(self) -> None:
        from specforge.core.build_sequence import MONOLITH_BUILD_SEQUENCE

        orders = [s.order for s in MONOLITH_BUILD_SEQUENCE]
        assert orders == list(range(1, 8))

    def test_step_categories(self) -> None:
        from specforge.core.build_sequence import MONOLITH_BUILD_SEQUENCE

        expected = [
            "folder_structure", "domain_models", "database",
            "repo_service", "controllers", "boundary_interface", "tests",
        ]
        actual = [s.category for s in MONOLITH_BUILD_SEQUENCE]
        assert actual == expected

    def test_boundary_interface_depends_on_repo_service(self) -> None:
        from specforge.core.build_sequence import MONOLITH_BUILD_SEQUENCE

        step6 = MONOLITH_BUILD_SEQUENCE[5]
        assert step6.category == "boundary_interface"
        assert 4 in step6.depends_on

    def test_file_path_patterns_have_module_placeholder(self) -> None:
        from specforge.core.build_sequence import MONOLITH_BUILD_SEQUENCE

        for step in MONOLITH_BUILD_SEQUENCE:
            assert "{module}" in step.file_path_pattern


class TestGetSequence:
    """get_sequence() factory function."""

    def test_microservice_returns_14_steps(self) -> None:
        from specforge.core.build_sequence import get_sequence

        seq = get_sequence("microservice")
        assert len(seq) == 14

    def test_monolithic_returns_7_steps(self) -> None:
        from specforge.core.build_sequence import get_sequence

        seq = get_sequence("monolithic")
        assert len(seq) == 7

    def test_modular_monolith_returns_7_steps(self) -> None:
        from specforge.core.build_sequence import get_sequence

        seq = get_sequence("modular-monolith")
        assert len(seq) == 7

    def test_deterministic_order(self) -> None:
        """Same input always produces same output."""
        from specforge.core.build_sequence import get_sequence

        seq1 = get_sequence("microservice")
        seq2 = get_sequence("microservice")
        assert seq1 == seq2

    def test_unknown_architecture_defaults_monolith(self) -> None:
        from specforge.core.build_sequence import get_sequence

        seq = get_sequence("unknown")
        assert len(seq) == 7
