"""ArtifactExtractor — structured extraction from prior artifacts (Feature 017)."""

from __future__ import annotations

import re
from pathlib import Path

from specforge.core.result import Ok, Result

_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)", re.MULTILINE)
_FR_RE = re.compile(r"FR-\d{3}")
_SC_RE = re.compile(r"SC-\d{3}")
_EC_RE = re.compile(r"EC-\d{3}")
_USER_STORY_RE = re.compile(
    r"###\s+User Story\s+\d+\s*[\u2014\u2013-]\s*(.+?)(?:\(Priority:\s*(\w+)\))?$",
    re.MULTILINE,
)
_ENTITY_RE = re.compile(r"###\s+(\w+)\s*$", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$", re.MULTILINE)
_DECISION_RE = re.compile(
    r"##\s+R\d+:\s*(.+?)$.*?\*\*Decision\*\*:\s*(.+?)$",
    re.MULTILINE | re.DOTALL,
)
_SEVERITY_RE = re.compile(r"\*\*Severity\*\*:\s*(\w+)", re.MULTILINE)


class ArtifactExtractor:
    """Stateless extractor for structured data from markdown artifacts."""

    def extract_from_spec(self, text: str | None) -> dict:
        if not text:
            return {}
        stories = self._extract_user_stories(text)
        frs = [{"id": m} for m in _FR_RE.findall(text)]
        scs = [{"id": m} for m in _SC_RE.findall(text)]
        return {
            "user_stories": stories,
            "functional_requirements": frs,
            "success_criteria": scs,
        }

    def extract_from_research(self, text: str | None) -> dict:
        if not text:
            return {}
        decisions = []
        for block in re.split(r"(?=^## R\d+:)", text, flags=re.MULTILINE):
            m_topic = re.search(r"^## R\d+:\s*(.+)$", block, re.MULTILINE)
            m_dec = re.search(r"\*\*Decision\*\*:\s*(.+)$", block, re.MULTILINE)
            m_rat = re.search(r"\*\*Rationale\*\*:\s*(.+)$", block, re.MULTILINE)
            if m_topic and m_dec:
                decisions.append({
                    "topic": m_topic.group(1).strip(),
                    "decision": m_dec.group(1).strip(),
                    "rationale": m_rat.group(1).strip() if m_rat else "",
                })
        return {"decisions": decisions}

    def extract_from_data_model(self, text: str | None) -> dict:
        if not text:
            return {}
        entities = []
        blocks = re.split(r"(?=^### \w)", text, flags=re.MULTILINE)
        for block in blocks:
            name_m = re.match(r"### (\w+)", block)
            if not name_m:
                continue
            rows = _TABLE_ROW_RE.findall(block)
            field_count = max(0, len(rows) - 1)
            entities.append({
                "name": name_m.group(1),
                "field_count": field_count,
                "relationships": [],
            })
        return {"entities": entities}

    def extract_from_edge_cases(self, text: str | None) -> dict:
        if not text:
            return {}
        cases = []
        ec_ids = _EC_RE.findall(text)
        severities = _SEVERITY_RE.findall(text)
        headings = re.findall(r"### EC-\d{3}:\s*(.+)$", text, re.MULTILINE)
        for i, ec_id in enumerate(ec_ids):
            cases.append({
                "id": ec_id,
                "severity": severities[i] if i < len(severities) else "Medium",
                "description": headings[i].strip() if i < len(headings) else "",
            })
        return {"edge_cases": cases}

    def extract_from_plan(self, text: str | None) -> dict:
        if not text:
            return {}
        headings = _HEADING_RE.findall(text)
        phases = [h.strip() for h in headings if h.strip().startswith("Phase")]
        return {"structure": headings, "phases": phases}

    def extract_all(
        self, service_dir: Path, phase_name: str,
    ) -> Result[dict, str]:
        """Read relevant prior artifacts and extract structured data."""
        extractors = {
            "spec": ("spec.md", self.extract_from_spec),
            "research": ("research.md", self.extract_from_research),
            "datamodel": ("data-model.md", self.extract_from_data_model),
            "edgecase": ("edge-cases.md", self.extract_from_edge_cases),
            "plan": ("plan.md", self.extract_from_plan),
        }
        result: dict = {}
        for name, (filename, extractor) in extractors.items():
            if name == phase_name:
                break
            path = service_dir / filename
            if path.exists():
                text = path.read_text(encoding="utf-8")
                result[name] = extractor(text)
            else:
                result[name] = {}
        return Ok(result)

    def format_for_prompt(
        self, phase_name: str, extractions: dict,
    ) -> str:
        """Render extractions as compact markdown for LLM context."""
        parts: list[str] = []
        for artifact, data in extractions.items():
            if not data:
                continue
            section = f"### Prior: {artifact}\n"
            section += self._format_section(data)
            parts.append(section)
        return "\n\n".join(parts)

    def _extract_user_stories(self, text: str) -> list[dict]:
        stories = []
        for m in _USER_STORY_RE.finditer(text):
            title = m.group(1).strip()
            priority = m.group(2) or "P1"
            start = m.end()
            next_h = re.search(r"^### ", text[start:], re.MULTILINE)
            block = text[start:start + next_h.start()] if next_h else text[start:]
            scenario_count = block.count("**Given**")
            stories.append({
                "title": title, "priority": priority,
                "scenario_count": scenario_count,
            })
        return stories

    @staticmethod
    def _format_section(data: dict) -> str:
        lines: list[str] = []
        for key, items in data.items():
            if isinstance(items, list):
                lines.append(f"- **{key}** ({len(items)} items)")
                for item in items[:5]:
                    if isinstance(item, dict):
                        summary = ", ".join(f"{k}={v}" for k, v in item.items())
                        lines.append(f"  - {summary}")
            elif isinstance(items, str):
                lines.append(f"- **{key}**: {items[:100]}")
        return "\n".join(lines)
