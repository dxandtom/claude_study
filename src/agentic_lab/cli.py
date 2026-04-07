from __future__ import annotations

import argparse

from .config import Settings
from .orchestrator import AgenticOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic Lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="Execute one task")
    run_parser.add_argument("task", help="Task you want the agentic framework to execute")

    args = parser.parse_args()
    if args.command == "run":
        settings = Settings.from_env()
        orchestrator = AgenticOrchestrator(settings)
        result = orchestrator.run(args.task)
        print("\nResult")
        print(result)


if __name__ == "__main__":
    main()
