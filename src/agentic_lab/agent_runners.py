from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import subprocess


@dataclass
class AgentRunResult:
    ok: bool
    output: str
    backend: str
    error: str | None = None


class ExternalAgentRunner:
    def __init__(self, name: str, command: str, timeout_seconds: int = 900) -> None:
        self.name = name
        self.command = command
        self.timeout_seconds = timeout_seconds

    def run(self, prompt: str, cwd: str | None = None) -> AgentRunResult:
        argv = shlex.split(self.command)
        argv.append(prompt)
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return AgentRunResult(ok=False, output="", backend=self.name, error=f"command not found: {argv[0]}")
        except subprocess.TimeoutExpired:
            return AgentRunResult(ok=False, output="", backend=self.name, error=f"timeout after {self.timeout_seconds}s")

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        if completed.returncode != 0:
            msg = stderr or stdout or f"exit code {completed.returncode}"
            return AgentRunResult(ok=False, output=stdout, backend=self.name, error=msg)
        return AgentRunResult(ok=True, output=stdout, backend=self.name)


class ClaudeCodeRunner(ExternalAgentRunner):
    def __init__(self, command: str = "claude -p --output-format json", timeout_seconds: int = 900) -> None:
        super().__init__(name="claude_code", command=command, timeout_seconds=timeout_seconds)

    def run(self, prompt: str, cwd: str | None = None) -> AgentRunResult:
        result = super().run(prompt=prompt, cwd=cwd)
        if not result.ok:
            return result

        parsed = _extract_json_text(result.output)
        return AgentRunResult(ok=True, output=parsed or result.output, backend=result.backend)


class CodexCLIRunner(ExternalAgentRunner):
    def __init__(self, command: str = "codex exec --json", timeout_seconds: int = 900) -> None:
        super().__init__(name="codex_cli", command=command, timeout_seconds=timeout_seconds)

    def run(self, prompt: str, cwd: str | None = None) -> AgentRunResult:
        result = super().run(prompt=prompt, cwd=cwd)
        if not result.ok:
            return result

        parsed = _extract_codex_json_text(result.output)
        return AgentRunResult(ok=True, output=parsed or result.output, backend=result.backend)


def _extract_json_text(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            for key in ("result", "content", "output", "text"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    except json.JSONDecodeError:
        pass
    return text


def _extract_codex_json_text(raw: str) -> str:
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    if not lines:
        return ""

    final_message = ""
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        for key in ("last_agent_message", "agent_message", "content", "output_text", "text"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                final_message = value.strip()

        item = event.get("item")
        if isinstance(item, dict):
            for key in ("text", "content"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    final_message = value.strip()

    return final_message or raw.strip()
