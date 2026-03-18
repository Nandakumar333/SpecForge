"""PythonPlugin — Python stack plugin with architecture-aware rules."""

from __future__ import annotations

from specforge.core.config import VALID_ARCHITECTURES
from specforge.plugins.stack_plugin_base import DockerConfig, PluginRule, StackPlugin
from specforge.plugins.stacks.python_rules import (
    MICROSERVICE_BACKEND_RULES,
    MICROSERVICE_CICD_RULES,
    MICROSERVICE_DATABASE_RULES,
    MODULAR_MONOLITH_BACKEND_RULES,
    MONOLITH_BACKEND_RULES,
    MONOLITH_CICD_RULES,
    MONOLITH_DATABASE_RULES,
)


class PythonPlugin(StackPlugin):
    """Python stack plugin providing architecture-specific governance rules."""

    @property
    def plugin_name(self) -> str:
        return "python"

    @property
    def description(self) -> str:
        return (
            "Python stack plugin with architecture-aware governance "
            "rules for microservice, monolithic, and modular-monolith patterns."
        )

    @property
    def supported_architectures(self) -> list[str]:
        return list(VALID_ARCHITECTURES)

    # ── Rules ────────────────────────────────────────────────────────

    def get_prompt_rules(self, arch: str) -> dict[str, list[PluginRule]]:
        if arch == "microservice":
            return self._microservice_rules()
        if arch == "monolithic":
            return self._monolith_rules()
        if arch == "modular-monolith":
            return self._modular_monolith_rules()
        return {}

    def _microservice_rules(self) -> dict[str, list[PluginRule]]:
        return {
            "backend": list(MICROSERVICE_BACKEND_RULES),
            "database": list(MICROSERVICE_DATABASE_RULES),
            "cicd": list(MICROSERVICE_CICD_RULES),
        }

    def _monolith_rules(self) -> dict[str, list[PluginRule]]:
        return {
            "backend": list(MONOLITH_BACKEND_RULES),
            "database": list(MONOLITH_DATABASE_RULES),
            "cicd": list(MONOLITH_CICD_RULES),
        }

    def _modular_monolith_rules(self) -> dict[str, list[PluginRule]]:
        return {
            "backend": list(MODULAR_MONOLITH_BACKEND_RULES),
            "database": list(MONOLITH_DATABASE_RULES),
            "cicd": list(MONOLITH_CICD_RULES),
        }

    # ── Docker ───────────────────────────────────────────────────────

    def get_docker_config(self, arch: str) -> DockerConfig | None:
        if arch == "microservice":
            return DockerConfig(
                base_image="python:3.11-slim",
                build_stages=("builder", "runtime"),
                exposed_ports=(8000,),
            )
        return None

    # ── Build Commands ───────────────────────────────────────────────

    def get_build_commands(self, arch: str) -> list[str]:
        if arch == "microservice":
            return [
                "pip install -r requirements.txt",
                "pip install -e .",
            ]
        return [
            "pip install -r requirements.txt",
            "pip install -e .",
        ]

    # ── Test Commands ────────────────────────────────────────────────

    def get_test_commands(self) -> list[str]:
        return ["pytest"]

    # ── Folder Structure ─────────────────────────────────────────────

    def get_folder_structure(self, arch: str) -> dict[str, str]:
        if arch == "microservice":
            return self._microservice_folders()
        if arch == "modular-monolith":
            return self._modular_monolith_folders()
        return self._monolith_folders()

    def _microservice_folders(self) -> dict[str, str]:
        return {
            "services/": "Individual microservice packages",
            "shared/": "Shared libraries and contracts",
            "tests/": "Test suites per service",
            "deploy/": "Deployment manifests and Dockerfiles",
        }

    def _monolith_folders(self) -> dict[str, str]:
        return {
            "src/app/": "Main application package",
            "src/app/api/": "API routes and endpoints",
            "src/app/services/": "Business logic layer",
            "src/app/models/": "Domain models and schemas",
            "tests/": "Unit and integration tests",
        }

    def _modular_monolith_folders(self) -> dict[str, str]:
        return {
            "src/modules/": "Feature modules with contracts",
            "src/app/": "Composition root and startup",
            "src/shared/": "Shared domain primitives",
            "tests/": "Test suites per module",
        }
