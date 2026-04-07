from __future__ import annotations

from .schemas import TaskPlan


class HeuristicPlanner:
    """Optimization over CoreCoder's single-loop: explicit plan stage for inspectability."""

    def make_plan(self, goal: str) -> TaskPlan:
        steps = [
            "Clarify objective and acceptance criteria",
            "Inspect existing context/files and gather facts",
            "Propose solution path and execute changes incrementally",
            "Run checks/tests and collect evidence",
            "Summarize outcomes, risks, and next actions",
        ]
        return TaskPlan(goal=goal, steps=steps)
