from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from .agent_runners import AgentRunResult, ClaudeCodeRunner, CodexCLIRunner, ExternalAgentRunner
from .config import Settings
from .context import ContextManager
from .llm import BaseLLM, build_llm
from .memory import MemoryStore
from .mission_board import MissionBoard, MissionState
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

WRITER_SYSTEM_PROMPT = """You are Claude Code acting as the implementation agent.
You should perform coding tasks, use tools when needed, and summarize concrete changes.
When reviewer feedback is provided, prioritize applying the feedback precisely."""

REVIEWER_SYSTEM_PROMPT = """You are Codex acting as the reviewer agent.
Review implementation output for correctness, risk, and optimization opportunities.
All review comments must be in Chinese.
Return STRICT JSON with this schema:
{
  \"approved\": true|false,
  \"summary\": \"简短中文总结\",
  \"findings\": [\"中文问题1\", \"中文问题2\"],
  \"suggestions\": [\"中文建议1\", \"中文建议2\"]
}"""


class AgenticOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm = build_llm(settings.provider, settings.model, settings.api_key, settings.base_url)
        self.writer_llm = build_llm(
            settings.writer_provider,
            settings.writer_model,
            settings.writer_api_key,
            settings.writer_base_url,
        )
        self.reviewer_llm = build_llm(
            settings.reviewer_provider,
            settings.reviewer_model,
            settings.reviewer_api_key,
            settings.reviewer_base_url,
        )
        self.writer_agent = self._build_external_agent(
            settings.writer_agent_name,
            settings.writer_agent_command,
            timeout_seconds=settings.external_agent_timeout_seconds,
        )
        self.reviewer_agent = self._build_external_agent(
            settings.reviewer_agent_name,
            settings.reviewer_agent_command,
            timeout_seconds=settings.external_agent_timeout_seconds,
        )
        self.board = MissionBoard(settings.board_events_file, settings.board_mission_dir)
        self.tools = build_default_registry()
        self.memory = MemoryStore(settings.memory_file)
        self.planner = HeuristicPlanner()
        self.skills = SkillManager(settings.skills_dir)
        self.context = ContextManager()

    def run(self, task: str, requested_skills: list[str] | None = None, multi_agent: bool = False) -> str:
        if multi_agent:
            return self.run_multi_agent(task, requested_skills=requested_skills)

        plan = self.planner.make_plan(task)
        recalls = [r[:400] for r in self.memory.recall(task)]
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

        final_text = self._run_single_agent_loop(
            messages=messages, llm=self.llm, allow_tools=True, provider=self.settings.provider
        )

        self._save_checkpoint(task, plan.steps, active_skills, messages, final_text, mode="single")
        self.memory.add("task", task)
        self.memory.add("result", final_text)
        return final_text or "No response produced."

    def run_multi_agent(self, task: str, requested_skills: list[str] | None = None) -> str:
        plan = self.planner.make_plan(task)
        recalls = [r[:400] for r in self.memory.recall(task)]
        active_skills = self.skills.select_for_task(task, explicit=requested_skills)
        mission = self.board.create(task)

        shared_context_blocks = [f"Plan: {json.dumps(asdict(plan), ensure_ascii=False, indent=2)}"]
        if recalls:
            shared_context_blocks.append("Relevant memory:\n- " + "\n- ".join(recalls))
        if active_skills:
            shared_context_blocks.append(
                "Active skills: " + ", ".join(s.name for s in active_skills) + "\n\n" + "\n\n".join(s.content for s in active_skills)
            )
        shared_context = "\n\n".join(shared_context_blocks)
        mission_context = {"shared_context": shared_context, "reviewer_feedback": ""}

        roles = [r.strip() for r in self.settings.multi_agent_roles.split(",") if r.strip()]
        action_count = 0
        while action_count < self.settings.multi_agent_max_actions and mission.status == "running":
            progressed = False
            for role in roles:
                if not self._agent_should_act(role, mission):
                    continue
                progressed = True
                action_count += 1
                result = self._agent_act(role, mission, mission_context)
                self.board.append_event(
                    mission,
                    actor=role,
                    event_type="agent.action",
                    payload={
                        "phase_before": mission.phase,
                        "backend": result.backend,
                        "ok": result.ok,
                        "error": result.error,
                        "output": result.output[:4000],
                    },
                )
                self._apply_agent_action(role, mission, mission_context, result)
                if mission.status != "running" or action_count >= self.settings.multi_agent_max_actions:
                    break
            if mission.status != "running":
                break
            if not progressed:
                mission.status = "stalled"
                self.board.append_event(mission, actor="system", event_type="mission.stalled", payload={"phase": mission.phase})
                break

        if mission.status == "running" and action_count >= self.settings.multi_agent_max_actions:
            mission.status = "limit_reached"
            self.board.append_event(
                mission,
                actor="system",
                event_type="mission.limit_reached",
                payload={"max_actions": self.settings.multi_agent_max_actions, "phase": mission.phase},
            )

        final_report = {
            "mode": "multi-agent-autonomous",
            "mission_id": mission.mission_id,
            "status": mission.status,
            "phase": mission.phase,
            "merged": mission.merged,
            "writer_output": mission.writer_output,
            "reviewer_report": mission.reviewer_report,
            "events": mission.events,
        }
        final_serialized = json.dumps(final_report, ensure_ascii=False, indent=2)

        checkpoint_messages = [
            ChatMessage(role="system", content="Multi-agent autonomous run (Mission Board + event-driven agents)"),
            ChatMessage(role="user", content=task),
            ChatMessage(role="assistant", content=final_serialized),
        ]
        self._save_checkpoint(task, plan.steps, active_skills, checkpoint_messages, final_serialized, mode="multi-autonomous")
        self.memory.add("task", task)
        self.memory.add("result", final_serialized)
        return final_serialized

    def _agent_should_act(self, role: str, mission: MissionState) -> bool:
        if role == "writer":
            return mission.phase in {"new", "changes_requested"} and mission.status == "running"
        if role == "reviewer":
            return mission.phase == "implemented" and mission.status == "running"
        if role == "integrator":
            return mission.phase == "approved" and mission.status == "running"
        return False

    def _agent_act(self, role: str, mission: MissionState, mission_context: dict[str, str]) -> AgentRunResult:
        if role == "writer":
            prompt = self._build_writer_prompt(mission.task, mission_context.get("shared_context", ""), mission_context.get("reviewer_feedback", ""), len(mission.events) + 1)
            return self._run_external_or_fallback(
                agent=self.writer_agent,
                prompt=prompt,
                llm=self.writer_llm,
                llm_provider=self.settings.writer_provider,
                llm_system_prompt=WRITER_SYSTEM_PROMPT,
                llm_user_prompt=prompt,
                allow_tools=True,
            )

        if role == "reviewer":
            prompt = self._build_reviewer_prompt(mission.task, mission.writer_output)
            return self._run_external_or_fallback(
                agent=self.reviewer_agent,
                prompt=prompt,
                llm=self.reviewer_llm,
                llm_provider=self.settings.reviewer_provider,
                llm_system_prompt=REVIEWER_SYSTEM_PROMPT,
                llm_user_prompt=prompt,
                allow_tools=False,
            )

        if role == "integrator":
            return AgentRunResult(ok=True, output="Review approved. Mission auto-marked as merged.", backend="autonomous_integrator")

        return AgentRunResult(ok=False, output="", backend=role, error="unknown role")

    def _apply_agent_action(self, role: str, mission: MissionState, mission_context: dict[str, str], result: AgentRunResult) -> None:
        if role == "writer":
            mission.writer_output = result.output
            mission.phase = "implemented"
            if not result.ok and not mission.writer_output:
                mission.status = "failed"
                self.board.append_event(mission, actor="system", event_type="mission.failed", payload={"reason": result.error or "writer failed"})
            return

        if role == "reviewer":
            report = self._parse_review_json(result.output)
            mission.reviewer_report = report
            mission_context["reviewer_feedback"] = self._format_reviewer_feedback(report)
            approved = bool(report.get("approved"))
            mission.phase = "approved" if approved else "changes_requested"
            return

        if role == "integrator":
            mission.merged = True
            mission.phase = "merged"
            mission.status = "completed"
            self.board.append_event(mission, actor="integrator", event_type="mission.merged", payload={"message": result.output})

    def _build_external_agent(self, agent_name: str, command: str, timeout_seconds: int) -> ExternalAgentRunner:
        normalized = agent_name.strip().lower()
        if normalized == "claude_code":
            return ClaudeCodeRunner(command=command, timeout_seconds=timeout_seconds)
        if normalized == "codex_cli":
            return CodexCLIRunner(command=command, timeout_seconds=timeout_seconds)
        return ExternalAgentRunner(name=normalized or "external_agent", command=command, timeout_seconds=timeout_seconds)

    def _run_external_or_fallback(
        self,
        agent: ExternalAgentRunner,
        prompt: str,
        llm: BaseLLM,
        llm_provider: str,
        llm_system_prompt: str,
        llm_user_prompt: str,
        allow_tools: bool,
    ) -> AgentRunResult:
        result = agent.run(prompt=prompt, cwd=str(Path.cwd()))
        if result.ok:
            return result
        if not self.settings.fallback_to_llm_on_agent_error:
            return result

        messages = [
            ChatMessage(role="system", content=llm_system_prompt),
            ChatMessage(role="user", content=llm_user_prompt),
        ]
        llm_output = self._run_single_agent_loop(messages=messages, llm=llm, allow_tools=allow_tools, provider=llm_provider)
        return AgentRunResult(ok=True, output=llm_output, backend=f"fallback_llm:{llm_provider}", error=result.error)

    def _build_writer_prompt(self, task: str, shared_context: str, reviewer_feedback: str, round_id: int) -> str:
        prompt = (
            f"原始任务:\n{task}\n\n"
            f"共享上下文:\n{shared_context}\n\n"
            f"自治执行轮次: {round_id}。请直接完成实现，并给出变更摘要。"
        )
        if reviewer_feedback:
            prompt += f"\n\n最新检视反馈（需优先处理）:\n{reviewer_feedback}"
        return prompt

    def _build_reviewer_prompt(self, task: str, writer_output: str) -> str:
        return (
            "请自主审查以下最新代码实现产出，并输出规定 JSON。\n\n"
            f"原始任务:\n{task}\n\n"
            f"实现产出:\n{writer_output}"
        )

    def _run_single_agent_loop(self, messages: list[ChatMessage], llm: BaseLLM, allow_tools: bool, provider: str | None = None) -> str:
        final_text = ""
        for _ in range(self.settings.max_rounds):
            messages = self.context.maybe_compress(messages)
            tools = self.tools.schemas() if allow_tools else None
            resp = llm.chat(messages, tools=tools)
            if allow_tools and resp.tool_calls:
                self._append_tool_round(messages, resp.content, resp.tool_calls, provider=provider or self.settings.provider)
                continue
            final_text = resp.content.strip()
            messages.append(ChatMessage(role="assistant", content=final_text))
            break
        return final_text

    def _append_tool_round(self, messages: list[ChatMessage], content: str, tool_calls: list[ToolCall], provider: str) -> None:
        if provider == "openai":
            messages.append(ChatMessage(role="assistant", content=content or "", tool_calls=tool_calls))
        else:
            messages.append(ChatMessage(role="assistant", content=content or "[tool invocation]"))

        for tc in tool_calls:
            result = self.tools.execute(tc.name, tc.arguments)
            result = result[: self.settings.max_tool_chars]
            if provider == "openai":
                messages.append(ChatMessage(role="tool", name=tc.name, tool_call_id=tc.call_id, content=result))
            else:
                messages.append(ChatMessage(role="tool", name=tc.name, content=result))

    def _parse_review_json(self, raw: str) -> dict[str, object]:
        candidate = raw.strip()
        if candidate.startswith("```"):
            candidate = candidate.strip("`")
            candidate = candidate.replace("json", "", 1).strip()
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass
        return {
            "approved": False,
            "summary": "审查器输出不是合法 JSON，默认不通过。",
            "findings": [raw.strip() or "空输出"],
            "suggestions": ["请按约定输出 JSON。"],
        }

    def _format_reviewer_feedback(self, review: dict[str, object]) -> str:
        summary = str(review.get("summary", ""))
        findings = review.get("findings") or []
        suggestions = review.get("suggestions") or []
        findings_text = "\n".join(f"- {x}" for x in findings if isinstance(x, str))
        suggestions_text = "\n".join(f"- {x}" for x in suggestions if isinstance(x, str))
        return f"总结:\n{summary}\n\n问题:\n{findings_text or '- 无'}\n\n建议:\n{suggestions_text or '- 无'}"

    def _save_checkpoint(
        self,
        task: str,
        plan_steps: list[str],
        active_skills: list,
        messages: list[ChatMessage],
        final_text: str,
        mode: str = "single",
    ) -> None:
        out_dir = Path(self.settings.checkpoint_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        run_id = uuid4().hex[:8]
        data = {
            "task": task,
            "mode": mode,
            "provider": self.settings.provider,
            "model": self.settings.model,
            "plan_steps": plan_steps,
            "active_skills": [s.name for s in active_skills],
            "messages": [m.to_dict() for m in messages],
            "final": final_text,
        }
        (out_dir / f"run-{ts}-{run_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
