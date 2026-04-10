from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class MissionState:
    mission_id: str
    task: str
    phase: str = "new"
    status: str = "running"
    writer_output: str = ""
    reviewer_report: dict[str, Any] = field(default_factory=dict)
    merged: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "task": self.task,
            "phase": self.phase,
            "status": self.status,
            "writer_output": self.writer_output,
            "reviewer_report": self.reviewer_report,
            "merged": self.merged,
            "events": self.events,
        }


class MissionBoard:
    def __init__(self, board_file: str = ".agentic/board/events.jsonl", mission_dir: str = ".agentic/board/missions") -> None:
        self.board_file = Path(board_file)
        self.mission_dir = Path(mission_dir)
        self.board_file.parent.mkdir(parents=True, exist_ok=True)
        self.mission_dir.mkdir(parents=True, exist_ok=True)

    def create(self, task: str) -> MissionState:
        mission = MissionState(mission_id=uuid4().hex[:10], task=task)
        self._persist_state(mission)
        self.append_event(mission, actor="system", event_type="mission.created", payload={"task": task})
        return mission

    def append_event(self, mission: MissionState, actor: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mission_id": mission.mission_id,
            "actor": actor,
            "type": event_type,
            "payload": payload,
        }
        mission.events.append(event)
        with self.board_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._persist_state(mission)

    def _persist_state(self, mission: MissionState) -> None:
        path = self.mission_dir / f"{mission.mission_id}.json"
        path.write_text(json.dumps(mission.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
