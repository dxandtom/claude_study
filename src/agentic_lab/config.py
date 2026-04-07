from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class Settings:
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    max_rounds: int = 10
    max_tool_chars: int = 12000
    memory_file: str = ".agentic/memory.jsonl"
    checkpoint_dir: str = ".agentic/checkpoints"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model=os.getenv("AGENTIC_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            max_rounds=int(os.getenv("AGENTIC_MAX_ROUNDS", "10")),
        )
