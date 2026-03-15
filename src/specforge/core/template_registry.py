"""Template registry — discovers and resolves templates."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.result import Err, Ok, Result
from specforge.core.template_models import (
    TemplateInfo,
    TemplateSource,
    TemplateType,
)

if TYPE_CHECKING:
    from importlib.abc import Traversable

# Files excluded from registry discovery (rendered via render_raw only)
_EXCLUDED_FILES = {"decisions.md.j2", "gitignore.j2"}

# Directories that map to template types
_TYPE_MAP: dict[str, TemplateType] = {
    "prompts": TemplateType.prompt,
    "features": TemplateType.feature,
    "partials": TemplateType.partial,
}


class TemplateRegistry:
    """Discovers templates from built-in and user-override directories."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root
        self._catalog: dict[
            tuple[str, TemplateType, str | None, TemplateSource],
            TemplateInfo,
        ] = {}

    def discover(self) -> Result:
        """Scan all template sources and populate the internal catalog."""
        try:
            count = self._discover_built_in()
            count += self._discover_user_overrides()
            return Ok(count)
        except Exception as exc:
            return Err(f"Template discovery failed: {exc}")

    def get(
        self,
        name: str,
        template_type: TemplateType,
        stack: str = "agnostic",
    ) -> Result:
        """Resolve a template by name, type, and optional stack.

        Resolution order (4-step chain):
        1. User-override variant (stack-specific)
        2. User-override generic
        3. Built-in variant (stack-specific)
        4. Built-in generic
        """
        resolution_chain = self._build_resolution_chain(
            name, template_type, stack
        )
        for key in resolution_chain:
            if key in self._catalog:
                info = self._catalog[key]
                if not info.is_base:
                    return Ok(info)
        return Err(
            f"Template not found: '{name}' "
            f"(type={template_type.value}, stack={stack}). "
            f"Check template directories for {name}.md.j2"
        )

    def list(
        self, template_type: TemplateType | None = None
    ) -> list[TemplateInfo]:
        """Return all known templates, optionally filtered by type."""
        entries = [
            info
            for info in self._catalog.values()
            if not info.is_base
        ]
        if template_type is not None:
            entries = [
                e for e in entries if e.template_type == template_type
            ]
        return sorted(entries, key=lambda e: (e.template_type.value, e.logical_name))

    def has(self, name: str, template_type: TemplateType) -> bool:
        """Quick check for template existence (generic only)."""
        key = (name, template_type, None, TemplateSource.built_in)
        if key in self._catalog:
            return True
        key_user = (name, template_type, None, TemplateSource.user_override)
        return key_user in self._catalog

    def _build_resolution_chain(
        self,
        name: str,
        template_type: TemplateType,
        stack: str,
    ) -> list[tuple[str, TemplateType, str | None, TemplateSource]]:
        """Build the 4-step resolution chain."""
        chain: list[tuple[str, TemplateType, str | None, TemplateSource]] = []
        if stack and stack != "agnostic":
            chain.append(
                (name, template_type, stack, TemplateSource.user_override)
            )
            chain.append(
                (name, template_type, None, TemplateSource.user_override)
            )
            chain.append(
                (name, template_type, stack, TemplateSource.built_in)
            )
            chain.append(
                (name, template_type, None, TemplateSource.built_in)
            )
        else:
            chain.append(
                (name, template_type, None, TemplateSource.user_override)
            )
            chain.append(
                (name, template_type, None, TemplateSource.built_in)
            )
        return chain

    def _discover_built_in(self) -> int:
        """Discover templates from the built-in package."""
        count = 0
        base = files("specforge.templates").joinpath("base")
        count += self._scan_top_level(base, TemplateSource.built_in)
        for subdir_name, ttype in _TYPE_MAP.items():
            subdir = base.joinpath(subdir_name)
            count += self._scan_directory(
                subdir, ttype, TemplateSource.built_in, f"base/{subdir_name}"
            )
        return count

    def _discover_user_overrides(self) -> int:
        """Discover templates from user override directory."""
        if self._project_root is None:
            return 0
        user_dir = self._project_root / ".specforge" / "templates"
        if not user_dir.is_dir():
            return 0
        count = 0
        count += self._scan_user_top_level(user_dir)
        for subdir_name, ttype in _TYPE_MAP.items():
            subdir = user_dir / subdir_name
            if subdir.is_dir():
                count += self._scan_user_directory(
                    subdir, ttype, subdir_name
                )
        return count

    def _scan_top_level(
        self,
        base: Traversable,
        source: TemplateSource,
    ) -> int:
        """Scan top-level .j2 files as constitution templates."""
        count = 0
        for item in base.iterdir():
            name = item.name if hasattr(item, "name") else str(item)
            if not name.endswith(".md.j2"):
                continue
            if name in _EXCLUDED_FILES:
                continue
            logical = name.removesuffix(".md.j2")
            info = TemplateInfo(
                logical_name=logical,
                template_type=TemplateType.constitution,
                source=source,
                template_path=f"base/{name}",
            )
            self._catalog[info.identity] = info
            count += 1
        return count

    def _scan_directory(
        self,
        directory: Traversable,
        template_type: TemplateType,
        source: TemplateSource,
        path_prefix: str,
    ) -> int:
        """Scan a subdirectory for templates."""
        count = 0
        try:
            items = list(directory.iterdir())
        except (FileNotFoundError, TypeError):
            return 0
        for item in items:
            name = item.name if hasattr(item, "name") else str(item)
            if not name.endswith(".md.j2"):
                continue
            info = self._parse_template_file(
                name, template_type, source, path_prefix
            )
            if info is not None:
                self._catalog[info.identity] = info
                count += 1
        return count

    def _scan_user_top_level(self, user_dir: Path) -> int:
        """Scan user override top-level for constitution templates."""
        count = 0
        for item in user_dir.iterdir():
            if not item.name.endswith(".md.j2"):
                continue
            if item.name in _EXCLUDED_FILES:
                continue
            logical = item.name.removesuffix(".md.j2")
            info = TemplateInfo(
                logical_name=logical,
                template_type=TemplateType.constitution,
                source=TemplateSource.user_override,
                template_path=str(item),
            )
            self._catalog[info.identity] = info
            count += 1
        return count

    def _scan_user_directory(
        self,
        directory: Path,
        template_type: TemplateType,
        subdir_name: str,
    ) -> int:
        """Scan user override subdirectory for templates."""
        count = 0
        for item in directory.iterdir():
            if not item.name.endswith(".md.j2"):
                continue
            info = self._parse_template_file(
                item.name,
                template_type,
                TemplateSource.user_override,
                str(directory),
            )
            if info is not None:
                self._catalog[info.identity] = info
                count += 1
        return count

    @staticmethod
    def _parse_template_file(
        filename: str,
        template_type: TemplateType,
        source: TemplateSource,
        path_prefix: str,
    ) -> TemplateInfo | None:
        """Parse a template filename into TemplateInfo."""
        is_base = filename.startswith("_")
        stripped = filename.removesuffix(".md.j2")
        if is_base:
            stripped = stripped.lstrip("_")

        parts = stripped.split(".")
        logical_name = parts[0]
        stack = parts[1] if len(parts) > 1 else None

        return TemplateInfo(
            logical_name=logical_name,
            template_type=template_type,
            source=source,
            template_path=f"{path_prefix}/{filename}",
            stack=stack,
            is_base=is_base,
        )
