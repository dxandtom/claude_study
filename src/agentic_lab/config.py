from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class Settings:
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    max_rounds: int = 10
    max_tool_chars: int = 12000
    memory_file: str = ".agentic/memory.jsonl"
    checkpoint_dir: str = ".agentic/checkpoints"
    skills_dir: str = "src/agentic_lab/skills"

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("AGENTIC_PROVIDER", "openai").lower()
        if provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
            base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
            model = os.getenv("AGENTIC_MODEL", "claude-3-7-sonnet-latest")
        else:
            key = os.getenv("OPENAI_API_KEY")
            base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("AGENTIC_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))

        return cls(
            provider=provider,
            model=model,
            api_key=key,
            base_url=base,
            max_rounds=int(os.getenv("AGENTIC_MAX_ROUNDS", "10")),
            skills_dir=os.getenv("AGENTIC_SKILLS_DIR", "src/agentic_lab/skills"),
        )
