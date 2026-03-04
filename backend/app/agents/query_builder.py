"""Query-builder agent — emits search queries from plan + interests."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import CandidateQueryPack, DailyRunPlan


class QueryBuilderAgent(BaseAgent[CandidateQueryPack]):
    """Produces search queries that scrapers can use to find candidates."""

    agent_name = "query_builder"
    output_type = CandidateQueryPack

    def run(
        self,
        plan: DailyRunPlan,
        interests: list[InterestConfig],
    ) -> CandidateQueryPack:
        keywords = [i.keyword for i in interests if i.active]
        prompt = (
            "Daily run plan:\n"
            f"- Focus keywords: {plan.focus_keywords}\n"
            f"- Source packs: {plan.source_packs}\n"
            f"- Constraints: leads_per_day={plan.constraints.leads_per_day}\n"
            "\nAll user interest keywords:\n"
            + "\n".join(f"- {k}" for k in keywords)
            + "\n\nEmit a CandidateQueryPack JSON with search queries to "
            "find interesting people matching these interests."
        )
        return self._run(prompt)
