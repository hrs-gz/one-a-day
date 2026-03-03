"""Pydantic IO schemas for agent inputs and outputs.

These are the canonical data contracts between agents in the agentic pipeline.
Every schema is validated at the boundary where an LLM response is parsed.

Evidence gating rule: ``VerifiedLeadBundle`` enforces via a model validator
that every ``VerifiedFact`` carries a non-empty ``url`` and ``excerpt``.
Facts that cannot be grounded in a verbatim source excerpt are omitted by
the agent — not fabricated and not stored.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Planner output
# ---------------------------------------------------------------------------


class DailyRunPlanConstraints(BaseModel):
    max_per_org: int = 1
    min_topic_clusters: int = 2


class DailyRunPlan(BaseModel):
    """Output of the Planner agent.

    Decides how many leads to surface today, which source packs to search,
    and what diversity constraints to apply to the final selection.
    """

    leads_per_day: int = Field(default=3, ge=1, le=3)
    source_packs: list[str]
    constraints: DailyRunPlanConstraints = Field(
        default_factory=DailyRunPlanConstraints
    )


# ---------------------------------------------------------------------------
# Query Builder output
# ---------------------------------------------------------------------------


class SearchQuery(BaseModel):
    """A single structured search query."""

    q: str
    recency_days: int | None = None
    allow_domains: list[str] | None = None
    deny_domains: list[str] | None = None


class CandidateQueryPack(BaseModel):
    """Output of the Query Builder agent.

    A list of structured search queries to execute via the candidate gatherer.
    No prose — only structured query objects.
    """

    queries: list[SearchQuery]


# ---------------------------------------------------------------------------
# Verifier / Extractor output
# ---------------------------------------------------------------------------


class LeadIdentity(BaseModel):
    """The person's core identity extracted from a page."""

    name: str | None = None
    role: str | None = None
    org: str | None = None


class VerifiedFact(BaseModel):
    """A single fact about a person, grounded in a source URL and verbatim excerpt."""

    fact: str
    url: str
    excerpt: str


class ContactPath(BaseModel):
    """A way to reach the person, grounded in a source URL and verbatim excerpt."""

    type: str  # e.g. "email", "linkedin", "website"
    url: str
    excerpt: str


class VerifiedLeadBundle(BaseModel):
    """Output of the Verifier/Extractor agent.

    Evidence-gated: every ``VerifiedFact`` must carry a non-empty ``url``
    and verbatim ``excerpt``. The model validator raises ``ValueError`` if
    any fact violates this constraint.
    """

    identity: LeadIdentity
    urls: list[str]
    facts: list[VerifiedFact]
    contact_paths: list[ContactPath] = Field(default_factory=list)

    @model_validator(mode="after")
    def all_facts_have_evidence(self) -> VerifiedLeadBundle:
        """Enforce evidence gating: every fact must have url + excerpt."""
        for fact in self.facts:
            if not fact.url.strip() or not fact.excerpt.strip():
                raise ValueError(
                    f"Evidence gating violation: fact '{fact.fact[:60]}' "
                    "is missing a source url or verbatim excerpt"
                )
        return self


# ---------------------------------------------------------------------------
# Card Writer output
# ---------------------------------------------------------------------------


class ScoreBreakdown(BaseModel):
    """Six-dimension scoring breakdown (each 0–100)."""

    relevance: int = Field(ge=0, le=100)
    novelty: int = Field(ge=0, le=100)
    authority: int = Field(ge=0, le=100)
    reachability: int = Field(ge=0, le=100)
    timeliness: int = Field(ge=0, le=100)
    diversity: int = Field(ge=0, le=100)


class LeadScore(BaseModel):
    """Score container: total = mean of all six breakdown dimensions (0–100)."""

    total: int = Field(ge=0, le=100)
    breakdown: ScoreBreakdown


class LeadSummary(BaseModel):
    """The person's identity as used on the scoring card."""

    name: str
    role: str
    org: str
    primary_url: str
    tags: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    """A compelling excerpt selected by the Card Writer as supporting evidence."""

    excerpt: str
    url: str


class ScoredQuestion(BaseModel):
    """An open question to investigate further, linked to source facts."""

    q: str
    why: str
    linked_fact_urls: list[str] = Field(default_factory=list)


class ResearchTask(BaseModel):
    """A specific follow-up research task with an expected finding."""

    task: str
    expected_find: str


class ScoringCard(BaseModel):
    """Output of the Card Writer agent.

    Produced from ``VerifiedLeadBundle.facts`` only — no external knowledge.
    ``score.total`` is the mean of all six breakdown dimensions.
    """

    lead: LeadSummary
    score: LeadScore
    why_relevant: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    questions: list[ScoredQuestion] = Field(default_factory=list)
    research_tasks: list[ResearchTask] = Field(default_factory=list)
