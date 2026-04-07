from __future__ import annotations

from pathlib import Path
import difflib

from .base import Tool


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a UTF-8 text file."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    def run(self, **kwargs) -> str:
        p = Path(kwargs["path"])
        if not p.exists():
            return f"File does not exist: {p}"
        return p.read_text(encoding="utf-8")


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write whole file contents (creates parent dirs)."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    }

    def run(self, **kwargs) -> str:
        p = Path(kwargs["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        new = kwargs["content"]
        p.write_text(new, encoding="utf-8")
        diff = "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile=f"a/{p}", tofile=f"b/{p}", lineterm=""))
        return diff or f"No changes for {p}"


class ReplaceInFileTool(Tool):
    name = "replace_in_file"
    description = "Unique string replace with safety checks."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old": {"type": "string"},
            "new": {"type": "string"},
        },
        "required": ["path", "old", "new"],
    }

    def run(self, **kwargs) -> str:
        p = Path(kwargs["path"])
        if not p.exists():
            return f"File does not exist: {p}"
        content = p.read_text(encoding="utf-8")
        old = kwargs["old"]
        new = kwargs["new"]
        count = content.count(old)
        if count != 1:
            return f"Expected exactly one match, found {count}."
        updated = content.replace(old, new)
        p.write_text(updated, encoding="utf-8")
        return f"Updated {p} (1 replacement)."
