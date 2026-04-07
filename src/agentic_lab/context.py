from __future__ import annotations

from dataclasses import dataclass

from .schemas import ChatMessage


@dataclass
class ContextPolicy:
    max_chars: int = 60000
    snip_chars: int = 2000
    keep_recent: int = 12


class ContextManager:
    """Inspired by claude-code-book context budgeting: snip + summarize + keep-recent."""

    def __init__(self, policy: ContextPolicy | None = None) -> None:
        self.policy = policy or ContextPolicy()

    def maybe_compress(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        total = sum(len(m.content) for m in messages)
        if total <= self.policy.max_chars:
            return messages

        head = [m for m in messages[:2]]
        tail = messages[-self.policy.keep_recent :]
        middle = messages[2 : -self.policy.keep_recent]

        summary_lines: list[str] = []
        for m in middle:
            content = m.content
            if len(content) > self.policy.snip_chars:
                content = f"{content[: self.policy.snip_chars]} ... [snipped]"
            summary_lines.append(f"[{m.role}] {content[:240]}")

        summary = "历史摘要（压缩）:\n" + "\n".join(summary_lines[:120])
        return head + [ChatMessage(role="system", content=summary)] + tail
