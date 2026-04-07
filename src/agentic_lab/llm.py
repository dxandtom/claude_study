from __future__ import annotations

import json
from typing import Any
from urllib import request

from .schemas import ChatMessage, LLMResponse, ToolCall


class BaseLLM:
    def chat(self, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        raise NotImplementedError


class OpenAICompatLLM(BaseLLM):
    def __init__(self, model: str, api_key: str | None, base_url: str) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        if not self.api_key:
            return self._offline_response(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]

        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            args_raw = fn.get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {"raw": args_raw}
            tool_calls.append(ToolCall(name=fn.get("name", "unknown"), arguments=args))
        return LLMResponse(content=content, tool_calls=tool_calls)

    def _offline_response(self, messages: list[ChatMessage]) -> LLMResponse:
        user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return LLMResponse(content=f"[offline-openai] Received task: {user_msg}\nPlease set OPENAI_API_KEY for real execution.")


class AnthropicLLM(BaseLLM):
    """Anthropic Messages API integration (text path + offline fallback)."""

    def __init__(self, model: str, api_key: str | None, base_url: str) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
        if not self.api_key:
            return self._offline_response(messages)

        sys_msgs = [m.content for m in messages if m.role == "system"]
        user_msgs = [m.to_dict() for m in messages if m.role in {"user", "assistant"}]
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1200,
            "system": "\n\n".join(sys_msgs),
            "messages": user_msgs,
        }

        req = request.Request(
            f"{self.base_url}/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        parts = data.get("content", [])
        text = "\n".join(p.get("text", "") for p in parts if p.get("type") == "text")
        return LLMResponse(content=text)

    def _offline_response(self, messages: list[ChatMessage]) -> LLMResponse:
        user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return LLMResponse(content=f"[offline-anthropic] Received task: {user_msg}\nPlease set ANTHROPIC_API_KEY for real execution.")


def build_llm(provider: str, model: str, api_key: str | None, base_url: str) -> BaseLLM:
    if provider == "anthropic":
        return AnthropicLLM(model, api_key, base_url)
    return OpenAICompatLLM(model, api_key, base_url)
