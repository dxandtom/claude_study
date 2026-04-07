from __future__ import annotations

from dataclasses import dataclass
import shlex


@dataclass
class PermissionDecision:
    allowed: bool
    stage: str
    reason: str


class PermissionPipeline:
    """Four-stage guardrail inspired by Claude Code permission pipeline ideas."""

    dangerous_tokens = {"rm", "shutdown", "reboot", "mkfs", "dd"}
    blocked_patterns = ["rm -rf /", ":(){:|:&};:"]

    def evaluate(self, command: str) -> PermissionDecision:
        parse = self._parse_stage(command)
        if not parse.allowed:
            return parse
        classify = self._classify_stage(command)
        if not classify.allowed:
            return classify
        policy = self._policy_stage(command)
        if not policy.allowed:
            return policy
        return PermissionDecision(True, "final", "allowed by policy pipeline")

    def _parse_stage(self, command: str) -> PermissionDecision:
        if not command.strip():
            return PermissionDecision(False, "parse", "empty command")
        try:
            shlex.split(command)
            return PermissionDecision(True, "parse", "valid shell syntax")
        except ValueError as exc:
            return PermissionDecision(False, "parse", f"invalid shell syntax: {exc}")

    def _classify_stage(self, command: str) -> PermissionDecision:
        if any(p in command for p in self.blocked_patterns):
            return PermissionDecision(False, "classify", "matched blocked command pattern")
        first = shlex.split(command)[0]
        if first in self.dangerous_tokens:
            return PermissionDecision(False, "classify", f"dangerous root token: {first}")
        return PermissionDecision(True, "classify", "risk low")

    def _policy_stage(self, command: str) -> PermissionDecision:
        redirections = [">", ">>", "2>"]
        if any(tok in command for tok in redirections) and "|" not in command:
            return PermissionDecision(True, "policy", "write command allowed in local mode")
        return PermissionDecision(True, "policy", "read/compute command allowed")
