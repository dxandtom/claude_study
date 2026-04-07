from __future__ import annotations

import subprocess

from ..security import PermissionPipeline
from .base import Tool


class SafeShellTool(Tool):
    name = "run_shell"
    description = "Run shell commands through a 4-stage permission pipeline."
    parameters = {
        "type": "object",
        "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 20}},
        "required": ["command"],
    }

    def __init__(self) -> None:
        self.pipeline = PermissionPipeline()

    def run(self, **kwargs) -> str:
        cmd = kwargs["command"]
        timeout = int(kwargs.get("timeout", 20))

        decision = self.pipeline.evaluate(cmd)
        if not decision.allowed:
            return f"Blocked by safety policy ({decision.stage}): {decision.reason}"

        try:
            out = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
            body = (out.stdout + "\n" + out.stderr).strip()
            return body[:12000] or "(no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"
