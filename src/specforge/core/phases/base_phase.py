"""BasePhase — template method pattern for pipeline phases."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specforge.core.result import Err, Ok, Result
from specforge.core.template_models import TemplateType

if TYPE_CHECKING:
    from specforge.core.architecture_adapter import ArchitectureAdapter
    from specforge.core.service_context import ServiceContext
    from specforge.core.template_registry import TemplateRegistry
    from specforge.core.template_renderer import TemplateRenderer


class BasePhase(ABC):
    """Abstract base for pipeline phases using template method pattern."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Phase name (e.g., 'spec', 'research')."""

    @property
    @abstractmethod
    def artifact_filename(self) -> str:
        """Output filename (e.g., 'spec.md')."""

    def run(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        renderer: TemplateRenderer,
        registry: TemplateRegistry,
        input_artifacts: dict[str, str],
    ) -> Result:
        """Execute phase: build context -> render -> write."""
        context = self._build_context(service_ctx, adapter, input_artifacts)
        render_result = renderer.render(
            self._template_name(),
            TemplateType.feature,
            context,
        )
        if not render_result.ok:
            return render_result
        return self._write_artifact(service_ctx, render_result.value)

    @abstractmethod
    def _build_context(
        self,
        service_ctx: ServiceContext,
        adapter: ArchitectureAdapter,
        input_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        """Build template context dict. Subclasses implement this."""

    def _template_name(self) -> str:
        """Template logical name for registry lookup."""
        return self.name

    def _post_render(  # noqa: B027
        self, service_ctx: ServiceContext, artifact_path: Path
    ) -> None:
        """Optional hook after artifact is written. Override if needed."""

    def _write_artifact(
        self, service_ctx: ServiceContext, content: str
    ) -> Result:
        """Write rendered content to the artifact file."""
        output_dir = service_ctx.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = output_dir / self.artifact_filename
        try:
            artifact_path.write_text(content, encoding="utf-8")
            self._post_render(service_ctx, artifact_path)
            return Ok(artifact_path)
        except OSError as exc:
            return Err(f"Failed to write {self.artifact_filename}: {exc}")
