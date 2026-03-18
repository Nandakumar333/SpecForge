# Plugin Interface Contracts

**Feature**: 013-plugin-system | **Date**: 2026-03-18

## Stack Plugin Interface

```python
class StackPlugin(ABC):
    """Abstract base for technology stack plugins.

    Every method that varies by architecture receives an ArchitectureType parameter.
    Plugins return rule OVERRIDES only — base governance rules are inherited.
    """

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Unique identifier: 'dotnet', 'nodejs', 'python', etc."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for --help and plugin list output."""

    @property
    @abstractmethod
    def supported_architectures(self) -> list[str]:
        """List of ArchitectureType values this plugin supports."""

    @abstractmethod
    def get_prompt_rules(
        self, arch: str
    ) -> dict[str, list[PluginRule]]:
        """Return domain-keyed rule overrides for the given architecture.

        Keys are governance domain names: 'backend', 'database', 'cicd', etc.
        Values are lists of PluginRule instances to append after base rules.

        Returns empty dict for 'agnostic' or unsupported architectures.
        """

    @abstractmethod
    def get_build_commands(self, arch: str) -> list[str]:
        """Return suggested build commands for the given architecture."""

    @abstractmethod
    def get_docker_config(
        self, arch: str
    ) -> DockerConfig | None:
        """Return container config for microservice, None for monolith."""

    @abstractmethod
    def get_test_commands(self) -> list[str]:
        """Return suggested test commands (architecture-independent)."""

    @abstractmethod
    def get_folder_structure(
        self, arch: str
    ) -> dict[str, str]:
        """Return path → description mapping for recommended folders."""
```

## Agent Plugin Interface (Existing)

```python
class AgentPlugin(ABC):
    """Base class for agent-specific configuration generators.

    Concrete implementations generate config files in the format
    expected by each AI coding agent.
    """

    @abstractmethod
    def agent_name(self) -> str:
        """Return the agent identifier (e.g., 'claude')."""

    @abstractmethod
    def generate_config(
        self,
        target_dir: Path,
        context: dict[str, Any],
    ) -> list[Path]:
        """Generate agent-specific config files. Return written paths.

        Context dict contains:
        - project_name: str
        - stack: str
        - architecture: str
        - governance_summary: str (concatenated governance rules)
        """

    @abstractmethod
    def config_files(self) -> list[str]:
        """Return list of config file names this agent produces."""
```

## Plugin Manager Interface

```python
class PluginManager:
    """Discovers, loads, and provides access to all plugins."""

    def __init__(self, project_root: Path | None = None) -> None: ...

    def discover(self) -> Result[int, str]:
        """Discover all built-in and custom plugins. Return total count."""

    def get_stack_plugin(self, name: str) -> Result[StackPlugin, str]:
        """Lookup stack plugin by name. Err if not found."""

    def get_agent_plugin(self, name: str) -> Result[AgentPlugin, str]:
        """Lookup agent plugin by name. Err if not found."""

    def list_stack_plugins(self) -> list[StackPlugin]:
        """Return all registered stack plugins."""

    def list_agent_plugins(self) -> list[AgentPlugin]:
        """Return all registered agent plugins."""
```

## PluginRule Data Contract

```python
@dataclass(frozen=True)
class PluginRule:
    """A single governance rule override from a stack plugin."""
    rule_id: str           # e.g., "BACK-DOTNET-MS-001"
    title: str             # e.g., "Per-Service DbContext Isolation"
    severity: str          # "ERROR" or "WARNING"
    scope: str             # e.g., "all EF Core DbContext classes"
    description: str       # Rule body text
    thresholds: dict[str, str]  # e.g., {"max_dbcontexts_per_service": "1"}
    example_correct: str   # Correct code example
    example_incorrect: str # Incorrect code example
```

## PromptFileManager Modified Signature

```python
class PromptFileManager:
    def generate(
        self,
        project_name: str,
        stack: str,
        extra_rules_by_domain: dict[str, list[PluginRule]] | None = None,
    ) -> Result[list[Path], str]:
        """Generate all 7 governance files.

        If extra_rules_by_domain is provided, matching domain rules are
        appended to the rendered template output before checksum computation.
        """
```

## CLI Integration Contract

```python
# init_cmd.py — new steps integrated into existing flow
def init(...):
    # ... existing validation, detection, config creation ...

    # NEW: Plugin integration
    plugin_mgr = PluginManager(project_root=target_dir)
    plugin_mgr.discover()

    # Stack plugin rules
    extra_rules: dict[str, list[PluginRule]] = {}
    stack_result = plugin_mgr.get_stack_plugin(resolved_stack)
    if stack_result.ok:
        extra_rules = stack_result.value.get_prompt_rules(architecture)

    # Generate governance with plugin rules
    manager.generate(project_name, stack, extra_rules_by_domain=extra_rules)

    # Agent config
    agent_result = plugin_mgr.get_agent_plugin(detection.agent)
    if agent_result.ok:
        agent_result.value.generate_config(target_dir, context)
```
