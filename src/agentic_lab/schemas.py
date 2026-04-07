from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ChatMessage:
    role: Role
    content: str
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class TaskPlan:
    goal: str
    steps: list[str] = field(default_factory=list)


@dataclass
class ReviewReport:
    approved: bool
    summary: str
    risks: list[str] = field(default_factory=list)
