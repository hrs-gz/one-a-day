"""Planner agent — chooses source packs and constraints for the daily run."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import DailyRunPlan


class PlannerAgent(BaseAgent[DailyRunPlan]):
    """Produces a DailyRunPlan from user interests and available sources."""

    agent_name = "planner"
    output_type = DailyRunPlan

    def run(
        self,
        interests: list[InterestConfig],
        source_names: list[str],
    ) -> DailyRunPlan:
        keywords = [f"{i.keyword} (weight={i.weight})" for i in interests if i.active]
        prompt = (
            "User interests:\n"
            + "\n".join(f"- {k}" for k in keywords)
            + "\n\nAvailable scraper sources:\n"
            + "\n".join(f"- {s}" for s in source_names)
            + "\n\nProduce a DailyRunPlan JSON. Choose which sources to "
            "scrape, which keywords to focus on, and set constraints."
        )
        return self._run(prompt)
