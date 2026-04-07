from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class Skill:
    name: str
    description: str
    content: str
    triggers: list[str]


class SkillManager:
    """Load and select skills inspired by Claude Code on-demand skill loading."""

    def __init__(self, skill_dir: str) -> None:
        self.skill_dir = Path(skill_dir)
        self.skills: dict[str, Skill] = {}
        self._load()

    def _load(self) -> None:
        self.skills.clear()
        if not self.skill_dir.exists():
            return
        for skill_file in self.skill_dir.glob("*/SKILL.md"):
            raw = skill_file.read_text(encoding="utf-8")
            name = skill_file.parent.name
            description = self._extract_field(raw, "description") or f"Skill: {name}"
            trigger_raw = self._extract_field(raw, "triggers") or ""
            triggers = [t.strip().lower() for t in trigger_raw.split(",") if t.strip()]
            self.skills[name] = Skill(name=name, description=description, content=raw, triggers=triggers)

    @staticmethod
    def _extract_field(content: str, field: str) -> str | None:
        pattern = rf"^{field}\s*:\s*(.+)$"
        for line in content.splitlines()[:30]:
            m = re.match(pattern, line.strip(), re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def available(self) -> list[Skill]:
        return sorted(self.skills.values(), key=lambda x: x.name)

    def select_for_task(self, task: str, explicit: list[str] | None = None) -> list[Skill]:
        selected: list[Skill] = []
        explicit = explicit or []
        if explicit:
            for name in explicit:
                if name in self.skills:
                    selected.append(self.skills[name])
            return selected

        low = task.lower()
        for skill in self.skills.values():
            if skill.name.lower() in low or any(t in low for t in skill.triggers):
                selected.append(skill)
        return selected
