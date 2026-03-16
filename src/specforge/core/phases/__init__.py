"""Pipeline phase definitions and registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseDefinition:
    """Static definition of a pipeline phase."""

    name: str
    number: int
    template_name: str
    artifact_filename: str
    prerequisites: tuple[str, ...]
    parallel_with: str | None = None


PHASE_DEFINITIONS: tuple[PhaseDefinition, ...] = (
    PhaseDefinition(
        name="spec",
        number=1,
        template_name="spec",
        artifact_filename="spec.md",
        prerequisites=(),
    ),
    PhaseDefinition(
        name="research",
        number=2,
        template_name="research",
        artifact_filename="research.md",
        prerequisites=("spec",),
    ),
    PhaseDefinition(
        name="datamodel",
        number=3,
        template_name="datamodel",
        artifact_filename="data-model.md",
        prerequisites=("research",),
        parallel_with="edgecase",
    ),
    PhaseDefinition(
        name="edgecase",
        number=3,
        template_name="edge-cases",
        artifact_filename="edge-cases.md",
        prerequisites=("research",),
        parallel_with="datamodel",
    ),
    PhaseDefinition(
        name="plan",
        number=4,
        template_name="plan",
        artifact_filename="plan.md",
        prerequisites=("datamodel", "edgecase"),
    ),
    PhaseDefinition(
        name="checklist",
        number=5,
        template_name="checklist",
        artifact_filename="checklist.md",
        prerequisites=("plan",),
    ),
    PhaseDefinition(
        name="tasks",
        number=6,
        template_name="tasks",
        artifact_filename="tasks.md",
        prerequisites=("checklist",),
    ),
)


def get_phase(name: str) -> PhaseDefinition | None:
    """Look up a phase definition by name."""
    for phase in PHASE_DEFINITIONS:
        if phase.name == name:
            return phase
    return None
