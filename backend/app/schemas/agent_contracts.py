"""Pydantic models for all agent input/output contracts.

These are in-memory DTOs — not ORM models. They define the structured JSON
that each agent must produce (and that the orchestrator validates).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Planner agent
# ---------------------------------------------------------------------------


class DailyRunConstraints(BaseModel):
    """Constraints the planner puts on the pipeline run."""

    max_per_org: int = Field(
        default=1,
        description="Max leads from the same organisation in one day.",
    )
    min_topic_clusters: int = Field(
        default=2,
        description="Minimum distinct topic clusters to cover.",
    )
    leads_per_day: int = Field(
        default=3,
        description="Target number of leads to persist.",
    )


class DailyRunPlan(BaseModel):
    """Output of the PlannerAgent."""

    source_packs: list[str] = Field(
        description="Scraper source names to use today.",
    )
    focus_keywords: list[str] = Field(
        description="Keywords to emphasise during scoring.",
    )
    constraints: DailyRunConstraints = Field(
        default_factory=DailyRunConstraints,
    )


# ---------------------------------------------------------------------------
# Query-builder agent
# ---------------------------------------------------------------------------


class CandidateQuery(BaseModel):
    """A single search query emitted by the query builder."""

    query: str
    source_type: str = "university"
    max_results: int = 10


class CandidateQueryPack(BaseModel):
    """Output of the QueryBuilderAgent."""

    queries: list[CandidateQuery]


# ---------------------------------------------------------------------------
# Verifier / extractor agent
# ---------------------------------------------------------------------------


class VerifiedFact(BaseModel):
    """A single verifiable fact extracted from a page."""

    claim: str = Field(description="The factual statement.")
    excerpt: str = Field(description="Verbatim excerpt from the source page.")
    source_url: str = Field(description="URL where this fact was found.")


class ContactPath(BaseModel):
    """A way to contact the person."""

    type: str = Field(description="linkedin | email | twitter | website")
    value: str


class LeadIdentity(BaseModel):
    """Core identity of a person extracted from a page."""

    name: str
    title: str = ""
    affiliation: str = ""


class VerifiedLeadBundle(BaseModel):
    """Output of the VerifierExtractorAgent for one URL."""

    identity: LeadIdentity
    facts: list[VerifiedFact]
    contact_paths: list[ContactPath] = Field(default_factory=list)
    source_url: str


# ---------------------------------------------------------------------------
# Card-writer agent
# ---------------------------------------------------------------------------


class ScoreBreakdown(BaseModel):
    """Per-dimension score (total = sum of all dimensions)."""

    relevance: float = Field(default=0, ge=0, le=40)
    novelty: float = Field(default=0, ge=0, le=20)
    authority: float = Field(default=0, ge=0, le=15)
    reachability: float = Field(default=0, ge=0, le=15)
    timeliness: float = Field(default=0, ge=0, le=10)

    @property
    def total(self) -> float:
        return (
            self.relevance
            + self.novelty
            + self.authority
            + self.reachability
            + self.timeliness
        )


class Evidence(BaseModel):
    """A supporting evidence item for a scoring card."""

    fact: str
    source_url: str
    excerpt: str


class ResearchQuestion(BaseModel):
    """A follow-up question raised by the card writer."""

    question: str
    priority: str = "medium"  # low | medium | high


class ResearchTask(BaseModel):
    """A concrete research task to investigate further."""

    task: str
    estimated_effort: str = "low"  # low | medium | high


class ScoringCard(BaseModel):
    """Output of the CardWriterAgent for one verified lead bundle."""

    name: str
    title: str
    affiliation: str
    summary: str = Field(description="1–3 sentence summary.")
    source_url: str
    contact_hint: str | None = None
    source_type: str = "university"
    score: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    evidence: list[Evidence] = Field(default_factory=list)
    questions: list[ResearchQuestion] = Field(default_factory=list)
    tasks: list[ResearchTask] = Field(default_factory=list)

    @property
    def total_score(self) -> float:
        return self.score.total
