"""Unit tests for wave computation and TopologicalParallelExecutor (Feature 016)."""

from __future__ import annotations

import pytest

from specforge.core.topological_parallel_executor import (
    architecture_to_waves,
    compute_waves,
)


class TestComputeWaves:
    def test_all_independent(self):
        manifest = {
            "services": [
                {"slug": "a", "communication": []},
                {"slug": "b", "communication": []},
                {"slug": "c", "communication": []},
            ],
        }
        result = compute_waves(manifest)
        assert result.ok
        waves = result.value
        assert len(waves) == 1
        assert set(waves[0].services) == {"a", "b", "c"}

    def test_linear_chain(self):
        manifest = {
            "services": [
                {"slug": "a", "communication": []},
                {"slug": "b", "communication": [{"target": "a"}]},
                {"slug": "c", "communication": [{"target": "b"}]},
            ],
        }
        result = compute_waves(manifest)
        assert result.ok
        waves = result.value
        assert len(waves) == 3
        assert waves[0].services == ("a",)
        assert waves[1].services == ("b",)
        assert waves[2].services == ("c",)

    def test_diamond_deps(self):
        manifest = {
            "services": [
                {"slug": "a", "communication": []},
                {"slug": "b", "communication": [{"target": "a"}]},
                {"slug": "c", "communication": [{"target": "a"}]},
                {"slug": "d", "communication": [
                    {"target": "b"}, {"target": "c"},
                ]},
            ],
        }
        result = compute_waves(manifest)
        assert result.ok
        waves = result.value
        assert len(waves) == 3
        assert waves[0].services == ("a",)
        assert set(waves[1].services) == {"b", "c"}
        assert waves[2].services == ("d",)

    def test_cycle_error(self):
        manifest = {
            "services": [
                {"slug": "a", "communication": [{"target": "b"}]},
                {"slug": "b", "communication": [{"target": "a"}]},
            ],
        }
        result = compute_waves(manifest)
        assert not result.ok
        assert "cycle" in result.error.lower()

    def test_empty_services(self):
        manifest = {"services": []}
        result = compute_waves(manifest)
        assert not result.ok


class TestArchitectureToWaves:
    def test_monolith_single_wave(self):
        manifest = {
            "architecture": "monolithic",
            "services": [
                {"slug": "mod-a"},
                {"slug": "mod-b"},
                {"slug": "mod-c"},
            ],
        }
        result = architecture_to_waves(manifest)
        assert result.ok
        waves = result.value
        assert len(waves) == 1
        assert set(waves[0].services) == {"mod-a", "mod-b", "mod-c"}

    def test_microservice_uses_graph(self):
        manifest = {
            "architecture": "microservice",
            "services": [
                {"slug": "auth", "communication": []},
                {"slug": "billing", "communication": [{"target": "auth"}]},
            ],
        }
        result = architecture_to_waves(manifest)
        assert result.ok
        waves = result.value
        assert len(waves) == 2

    def test_modular_monolith_no_comm_single_wave(self):
        manifest = {
            "architecture": "modular-monolith",
            "services": [
                {"slug": "a"},
                {"slug": "b"},
            ],
        }
        result = architecture_to_waves(manifest)
        assert result.ok
        assert len(result.value) == 1

    def test_modular_monolith_with_comm_uses_graph(self):
        manifest = {
            "architecture": "modular-monolith",
            "services": [
                {"slug": "a", "communication": []},
                {"slug": "b", "communication": [{"target": "a"}]},
            ],
        }
        result = architecture_to_waves(manifest)
        assert result.ok
        assert len(result.value) == 2

    def test_no_services_error(self):
        manifest = {"architecture": "microservice", "services": []}
        result = architecture_to_waves(manifest)
        assert not result.ok
