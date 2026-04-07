from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime, timezone


class MemoryStore:
    """Append-only memory with simple retrieval by keyword overlap."""

    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, kind: str, content: str) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "content": content,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def recall(self, query: str, limit: int = 5) -> list[str]:
        if not self.path.exists():
            return []
        q_terms = set(query.lower().split())
        scored: list[tuple[int, str]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            text = rec["content"]
            score = sum(1 for t in q_terms if t in text.lower())
            if score > 0:
                scored.append((score, text))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored[:limit]]
