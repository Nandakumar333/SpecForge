"""ContractResolver — loads contracts from dependent services only."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.config import FEATURES_DIR
from specforge.core.result import Err, Ok, Result

if TYPE_CHECKING:
    from specforge.core.service_context import ServiceDependency

logger = logging.getLogger(__name__)


class ContractResolver:
    """Loads shared contracts from services that the target depends on."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def resolve(
        self,
        dependencies: tuple[ServiceDependency, ...],
    ) -> Result[dict[str, str], str]:
        """Load contracts for each dependency. Non-blocking on missing."""
        contracts: dict[str, str] = {}
        for dep in dependencies:
            content = self._load_contracts_for(dep.target_slug)
            if content:
                contracts[dep.target_slug] = content
        return Ok(contracts)

    def _load_contracts_for(self, dep_slug: str) -> str:
        """Read all files from a dependency's contracts/ directory."""
        contracts_dir = (
            self._root / FEATURES_DIR / dep_slug / "contracts"
        )
        if not contracts_dir.is_dir():
            logger.warning(
                "No contracts directory for '%s' at %s",
                dep_slug, contracts_dir,
            )
            return ""

        parts: list[str] = []
        for path in sorted(contracts_dir.iterdir()):
            if path.is_file():
                try:
                    parts.append(path.read_text(encoding="utf-8"))
                except OSError as exc:
                    logger.warning(
                        "Failed to read contract '%s': %s", path, exc,
                    )
        return "\n".join(parts)
