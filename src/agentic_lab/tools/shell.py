from __future__ import annotations

import subprocess

from .base import Tool


class SafeShellTool(Tool):
    name = "run_shell"
    description = "Run safe shell commands with timeout and denylist."
    parameters = {
        "type": "object",
        "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 20}},
        "required": ["command"],
    }

    denylist = ["rm -rf /", "shutdown", "reboot", ":(){:|:&};:"]

    def run(self, **kwargs) -> str:
        cmd = kwargs["command"]
        timeout = int(kwargs.get("timeout", 20))
        if any(x in cmd for x in self.denylist):
            return "Blocked by safety policy."
        try:
            out = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
            body = (out.stdout + "\n" + out.stderr).strip()
            return body[:12000] or "(no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"
