from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime, timezone
from dataclasses import asdict

from .config import Settings
from .llm import OpenAICompatLLM
from .memory import MemoryStore
from .planner import HeuristicPlanner
from .schemas import ChatMessage
from .tools import build_default_registry

SYSTEM_PROMPT = """You are an Agentic coordinator with Planner/Executor/Reviewer discipline.
Rules:
1) Generate focused tool calls when needed.
2) Keep edits safe and reversible.
3) Validate outcomes before final answer.
4) If unsure, ask for clarification."""


class AgenticOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm = OpenAICompatLLM(settings.model, settings.api_key, settings.base_url)
        self.tools = build_default_registry()
        self.memory = MemoryStore(settings.memory_file)
        self.planner = HeuristicPlanner()

    def run(self, task: str) -> str:
        plan = self.planner.make_plan(task)
        recalls = self.memory.recall(task)

        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="system", content=f"Plan: {json.dumps(asdict(plan), ensure_ascii=False, indent=2)}"),
        ]
        if recalls:
            messages.append(ChatMessage(role="system", content="Relevant memory:\n- " + "\n- ".join(recalls)))
        messages.append(ChatMessage(role="user", content=task))

        final_text = ""
        for _ in range(self.settings.max_rounds):
            resp = self.llm.chat(messages, tools=self.tools.schemas())
            if resp.tool_calls:
                messages.append(ChatMessage(role="assistant", content=resp.content or "[tool invocation]"))
                for tc in resp.tool_calls:
                    result = self.tools.execute(tc.name, tc.arguments)
                    result = result[: self.settings.max_tool_chars]
                    messages.append(ChatMessage(role="tool", name=tc.name, content=result))
                continue

            final_text = resp.content.strip()
            messages.append(ChatMessage(role="assistant", content=final_text))
            break

        self._save_checkpoint(task, plan.steps, messages, final_text)
        self.memory.add("task", task)
        self.memory.add("result", final_text)
        return final_text or "No response produced."

    def _save_checkpoint(self, task: str, plan_steps: list[str], messages: list[ChatMessage], final_text: str) -> None:
        out_dir = Path(self.settings.checkpoint_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        data = {
            "task": task,
            "plan_steps": plan_steps,
            "messages": [m.to_dict() for m in messages],
            "final": final_text,
        }
        (out_dir / f"run-{ts}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
