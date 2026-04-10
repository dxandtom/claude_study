from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _default_skills_dir() -> str:
    return str((Path(__file__).resolve().parent / "skills").resolve())


@dataclass
class Settings:
    provider: str = "openai"
    model: str = "gpt-5"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"

    writer_provider: str = "anthropic"
    writer_model: str = "claude-sonnet-4-20250514"
    writer_api_key: str | None = None
    writer_base_url: str = "https://api.anthropic.com/v1"

    reviewer_provider: str = "openai"
    reviewer_model: str = "gpt-5"
    reviewer_api_key: str | None = None
    reviewer_base_url: str = "https://api.openai.com/v1"

    writer_agent_name: str = "claude_code"
    writer_agent_command: str = "claude -p --output-format json"
    reviewer_agent_name: str = "codex_cli"
    reviewer_agent_command: str = "codex exec --json"
    external_agent_timeout_seconds: int = 900
    fallback_to_llm_on_agent_error: bool = True

    max_rounds: int = 10
    max_tool_chars: int = 12000
    memory_file: str = ".agentic/memory.jsonl"
    checkpoint_dir: str = ".agentic/checkpoints"
    skills_dir: str = _default_skills_dir()

    board_events_file: str = ".agentic/board/events.jsonl"
    board_mission_dir: str = ".agentic/board/missions"
    multi_agent_roles: str = "writer,reviewer,integrator"
    multi_agent_max_actions: int = 12

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("AGENTIC_PROVIDER", "openai").lower()
        if provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
            base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
            model = os.getenv("AGENTIC_MODEL", "claude-sonnet-4-20250514")
        else:
            key = os.getenv("OPENAI_API_KEY")
            base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("AGENTIC_MODEL", os.getenv("OPENAI_MODEL", "gpt-5"))

        writer_provider = os.getenv("AGENTIC_WRITER_PROVIDER", "anthropic").lower()
        writer_key = os.getenv("AGENTIC_WRITER_API_KEY")
        if not writer_key:
            writer_key = os.getenv("ANTHROPIC_API_KEY") if writer_provider == "anthropic" else os.getenv("OPENAI_API_KEY")
        writer_base = os.getenv(
            "AGENTIC_WRITER_BASE_URL",
            os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
            if writer_provider == "anthropic"
            else os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        writer_model = os.getenv(
            "AGENTIC_WRITER_MODEL",
            "claude-sonnet-4-20250514" if writer_provider == "anthropic" else "gpt-5",
        )

        reviewer_provider = os.getenv("AGENTIC_REVIEWER_PROVIDER", "openai").lower()
        reviewer_key = os.getenv("AGENTIC_REVIEWER_API_KEY")
        if not reviewer_key:
            reviewer_key = os.getenv("OPENAI_API_KEY") if reviewer_provider == "openai" else os.getenv("ANTHROPIC_API_KEY")
        reviewer_base = os.getenv(
            "AGENTIC_REVIEWER_BASE_URL",
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            if reviewer_provider == "openai"
            else os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
        )
        reviewer_model = os.getenv(
            "AGENTIC_REVIEWER_MODEL",
            "gpt-5" if reviewer_provider == "openai" else "claude-sonnet-4-20250514",
        )

        return cls(
            provider=provider,
            model=model,
            api_key=key,
            base_url=base,
            writer_provider=writer_provider,
            writer_model=writer_model,
            writer_api_key=writer_key,
            writer_base_url=writer_base,
            reviewer_provider=reviewer_provider,
            reviewer_model=reviewer_model,
            reviewer_api_key=reviewer_key,
            reviewer_base_url=reviewer_base,
            writer_agent_name=os.getenv("AGENTIC_WRITER_AGENT", "claude_code"),
            writer_agent_command=os.getenv("AGENTIC_WRITER_AGENT_CMD", "claude -p --output-format json"),
            reviewer_agent_name=os.getenv("AGENTIC_REVIEWER_AGENT", "codex_cli"),
            reviewer_agent_command=os.getenv("AGENTIC_REVIEWER_AGENT_CMD", "codex exec --json"),
            external_agent_timeout_seconds=int(os.getenv("AGENTIC_AGENT_TIMEOUT_SECONDS", "900")),
            fallback_to_llm_on_agent_error=os.getenv("AGENTIC_FALLBACK_TO_LLM_ON_AGENT_ERROR", "1") != "0",
            max_rounds=int(os.getenv("AGENTIC_MAX_ROUNDS", "10")),
            skills_dir=os.getenv("AGENTIC_SKILLS_DIR", _default_skills_dir()),
            board_events_file=os.getenv("AGENTIC_BOARD_EVENTS_FILE", ".agentic/board/events.jsonl"),
            board_mission_dir=os.getenv("AGENTIC_BOARD_MISSION_DIR", ".agentic/board/missions"),
            multi_agent_roles=os.getenv("AGENTIC_MULTI_AGENT_ROLES", "writer,reviewer,integrator"),
            multi_agent_max_actions=int(os.getenv("AGENTIC_MULTI_AGENT_MAX_ACTIONS", "12")),
        )
