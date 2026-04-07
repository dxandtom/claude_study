from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from .config import Settings
from .llm import build_llm
from .memory import MemoryStore
from .planner import HeuristicPlanner
from .schemas import ChatMessage, ToolCall
from .skills_engine import SkillManager
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
        self.llm = build_llm(settings.provider, settings.model, settings.api_key, settings.base_url)
        self.tools = build_default_registry()
        self.memory = MemoryStore(settings.memory_file)
        self.planner = HeuristicPlanner()
        self.skills = SkillManager(settings.skills_dir)

    def run(self, task: str, requested_skills: list[str] | None = None) -> str:
        plan = self.planner.make_plan(task)
        recalls = self.memory.recall(task)
        active_skills = self.skills.select_for_task(task, explicit=requested_skills)

        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="system", content=f"Plan: {json.dumps(asdict(plan), ensure_ascii=False, indent=2)}"),
        ]
        if active_skills:
            skill_header = "Active skills: " + ", ".join(s.name for s in active_skills)
            skill_bodies = "\n\n".join(s.content for s in active_skills)
            messages.append(ChatMessage(role="system", content=f"{skill_header}\n\n{skill_bodies}"))

        if recalls:
            messages.append(ChatMessage(role="system", content="Relevant memory:\n- " + "\n- ".join(recalls)))
        messages.append(ChatMessage(role="user", content=task))

        final_text = ""
        for _ in range(self.settings.max_rounds):
            tools = self.tools.schemas() if self.settings.provider == "openai" else None
            resp = self.llm.chat(messages, tools=tools)
            if resp.tool_calls:
                self._append_tool_round(messages, resp.content, resp.tool_calls)
                continue

            final_text = resp.content.strip()
            messages.append(ChatMessage(role="assistant", content=final_text))
            break

        self._save_checkpoint(task, plan.steps, active_skills, messages, final_text)
        self.memory.add("task", task)
        self.memory.add("result", final_text)
        return final_text or "No response produced."

    def _append_tool_round(self, messages: list[ChatMessage], content: str, tool_calls: list[ToolCall]) -> None:
        if self.settings.provider == "openai":
            messages.append(ChatMessage(role="assistant", content=content or "", tool_calls=tool_calls))
        else:
            messages.append(ChatMessage(role="assistant", content=content or "[tool invocation]"))

        for tc in tool_calls:
            result = self.tools.execute(tc.name, tc.arguments)
            result = result[: self.settings.max_tool_chars]
            if self.settings.provider == "openai":
                messages.append(
                    ChatMessage(
                        role="tool",
                        name=tc.name,
                        tool_call_id=tc.call_id,
                        content=result,
                    )
                )
            else:
                messages.append(ChatMessage(role="tool", name=tc.name, content=result))

    def _save_checkpoint(
        self,
        task: str,
        plan_steps: list[str],
        active_skills: list,
        messages: list[ChatMessage],
        final_text: str,
    ) -> None:
        out_dir = Path(self.settings.checkpoint_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        run_id = uuid4().hex[:8]
        data = {
            "task": task,
            "provider": self.settings.provider,
            "model": self.settings.model,
            "plan_steps": plan_steps,
            "active_skills": [s.name for s in active_skills],
            "messages": [m.to_dict() for m in messages],
            "final": final_text,
        }
        (out_dir / f"run-{ts}-{run_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
