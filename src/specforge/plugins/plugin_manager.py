"""PluginManager — discovers, registers, and resolves plugins."""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
from pathlib import Path

from specforge.core.config import CUSTOM_PLUGIN_DIR
from specforge.core.result import Err, Ok, Result
from specforge.plugins.agents.base import AgentPlugin
from specforge.plugins.stack_plugin_base import StackPlugin


class PluginManager:
    """Central registry for stack and agent plugins."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root
        self._stack_plugins: dict[str, StackPlugin] = {}
        self._agent_plugins: dict[str, AgentPlugin] = {}

    def discover(self) -> Result[int, str]:
        """Discover all built-in and custom plugins. Return total count."""
        try:
            self._discover_built_in_stacks()
            self._discover_built_in_agents()
            self._discover_custom_stacks()
            self._discover_custom_agents()
            total = len(self._stack_plugins) + len(self._agent_plugins)
            return Ok(total)
        except Exception as exc:
            return Err(f"Plugin discovery failed: {exc}")

    def get_stack_plugin(self, name: str) -> Result[StackPlugin, str]:
        """Lookup by name. Err lists available plugins if not found."""
        if name in self._stack_plugins:
            return Ok(self._stack_plugins[name])
        available = sorted(self._stack_plugins.keys())
        return Err(
            f"Stack plugin '{name}' not found. "
            f"Available stack plugins: {', '.join(available) or 'none'}"
        )

    def get_agent_plugin(self, name: str) -> Result[AgentPlugin, str]:
        """Lookup by name. Err lists available plugins if not found."""
        if name in self._agent_plugins:
            return Ok(self._agent_plugins[name])
        available = sorted(self._agent_plugins.keys())
        return Err(
            f"Agent plugin '{name}' not found. "
            f"Available agent plugins: {', '.join(available) or 'none'}"
        )

    def list_stack_plugins(self) -> list[StackPlugin]:
        """Return all registered stack plugins sorted by name."""
        return [
            self._stack_plugins[k]
            for k in sorted(self._stack_plugins.keys())
        ]

    def list_agent_plugins(self) -> list[AgentPlugin]:
        """Return all registered agent plugins sorted by name."""
        return [
            self._agent_plugins[k]
            for k in sorted(self._agent_plugins.keys())
        ]

    # ── Internal discovery ───────────────────────────────────────────

    def _discover_built_in_stacks(self) -> None:
        """Scan specforge.plugins.stacks for *_plugin.py modules."""
        pkg = importlib.import_module("specforge.plugins.stacks")
        for _importer, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
            if not modname.endswith("_plugin"):
                continue
            module = importlib.import_module(
                f"specforge.plugins.stacks.{modname}"
            )
            self._register_stack_classes(module)

    def _discover_built_in_agents(self) -> None:
        """Scan specforge.plugins.agents for *_plugin.py modules."""
        pkg = importlib.import_module("specforge.plugins.agents")
        for _importer, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
            if not modname.endswith("_plugin"):
                continue
            module = importlib.import_module(
                f"specforge.plugins.agents.{modname}"
            )
            self._register_agent_classes(module)

    def _discover_custom_stacks(self) -> None:
        """Load custom stack plugins from project .specforge/plugins/stacks/."""
        if not self._project_root:
            return
        custom_dir = self._project_root / CUSTOM_PLUGIN_DIR / "stacks"
        if not custom_dir.is_dir():
            return
        self._load_custom_plugins(
            custom_dir, StackPlugin, self._stack_plugins, "plugin_name",
        )

    def _discover_custom_agents(self) -> None:
        """Load custom agent plugins from project .specforge/plugins/agents/."""
        if not self._project_root:
            return
        custom_dir = self._project_root / CUSTOM_PLUGIN_DIR / "agents"
        if not custom_dir.is_dir():
            return
        self._load_custom_plugins(
            custom_dir, AgentPlugin, self._agent_plugins, "agent_name",
        )

    def _load_custom_plugins(
        self,
        directory: Path,
        base_class: type,
        registry: dict,
        name_attr: str,
    ) -> None:
        """Load plugins from directory using importlib.util."""
        for path in sorted(directory.glob("*_plugin.py")):
            self._try_load_plugin(path, base_class, registry, name_attr)

    def _try_load_plugin(
        self,
        path: Path,
        base_class: type,
        registry: dict,
        name_attr: str,
    ) -> None:
        """Attempt to load a single plugin file. Skip on error."""
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec is None or spec.loader is None:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._register_custom_from_module(
                module, base_class, registry, name_attr,
            )
        except Exception:
            return

    def _register_custom_from_module(
        self,
        module: object,
        base_class: type,
        registry: dict,
        name_attr: str,
    ) -> None:
        """Register all subclasses of base_class found in module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not (
                isinstance(attr, type)
                and issubclass(attr, base_class)
                and attr is not base_class
            ):
                continue
            instance = attr()
            name = _resolve_plugin_name(instance, name_attr)
            if name:
                registry[name] = instance

    def _register_stack_classes(self, module: object) -> None:
        """Find and register StackPlugin subclasses in a module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, StackPlugin)
                and attr is not StackPlugin
                and getattr(attr, "__module__", None) == module.__name__
            ):
                instance = attr()
                self._stack_plugins[instance.plugin_name] = instance

    def _register_agent_classes(self, module: object) -> None:
        """Find and register AgentPlugin subclasses in a module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, AgentPlugin)
                and attr is not AgentPlugin
                and getattr(attr, "__module__", None) == module.__name__
            ):
                instance = attr()
                self._agent_plugins[instance.agent_name()] = instance


def _resolve_plugin_name(instance: object, name_attr: str) -> str | None:
    """Extract the plugin name from an instance."""
    try:
        value = getattr(instance, name_attr)
        return value() if callable(value) else value
    except Exception:
        return None
