from __future__ import annotations

import argparse

from .config import Settings
from .orchestrator import AgenticOrchestrator
from .skills_engine import SkillManager
from .webui import serve_ui


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic Lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Execute one task")
    run_parser.add_argument("task", help="Task you want the agentic framework to execute")
    run_parser.add_argument("--skills", default="", help="Comma separated explicit skills")

    sub.add_parser("skills", help="List available skills")

    ui_parser = sub.add_parser("ui", help="Start beautiful local web UI")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "run":
        orchestrator = AgenticOrchestrator(settings)
        skill_list = [x.strip() for x in args.skills.split(",") if x.strip()]
        result = orchestrator.run(args.task, requested_skills=skill_list)
        print("\nResult")
        print(result)
        return

    if args.command == "skills":
        manager = SkillManager(settings.skills_dir)
        for s in manager.available():
            print(f"- {s.name}: {s.description}")
        return

    if args.command == "ui":
        serve_ui(settings, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
