"""Recommendation Contract — structured Builder output artifact."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Claim(BaseModel):
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)
    freshness: str = "unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class CandidateArchitecture(BaseModel):
    candidate_id: str
    name: str
    summary: str
    pattern_ids: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    expected_value: str = ""
    expected_cost: str = ""
    risk: str = ""
    reversibility: str = "high"
    affected_stakeholders: list[str] = Field(default_factory=list)
    tradeoffs: dict[str, str] = Field(default_factory=dict)


class ReviewScore(BaseModel):
    dimension: str
    score: float = Field(ge=0.0, le=1.0)
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    remediation: str = ""
    blocking: bool = False


class SimulationResult(BaseModel):
    mode: str  # static | scenario | replay | load | shadow
    name: str
    passed: bool
    findings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence_interval: str = "wide"
    limitations: list[str] = Field(default_factory=list)


class MigrationPlan(BaseModel):
    plan_id: str
    steps: list[str] = Field(default_factory=list)
    gates: list[str] = Field(default_factory=list)
    rollback: list[str] = Field(default_factory=list)
    owner: str = "HUMAN-1"
    success_measures: list[str] = Field(default_factory=list)
    environment: str = "sandbox"
    requires_human_approval: bool = True


class RecommendationContract(BaseModel):
    recommendation_id: str
    org_id: str
    created_at: datetime = Field(default_factory=_now)
    problem_statement: str
    reconstructed_intent: dict[str, Any] = Field(default_factory=dict)
    claims: list[Claim] = Field(default_factory=list)
    current_state_summary: str = ""
    preserved_strengths: list[str] = Field(default_factory=list)
    candidates: list[CandidateArchitecture] = Field(default_factory=list)
    decision_criteria: list[str] = Field(default_factory=list)
    weighted_tradeoffs: dict[str, float] = Field(default_factory=dict)
    simulation_results: list[SimulationResult] = Field(default_factory=list)
    review_scores: list[ReviewScore] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    chosen_candidate_id: str = ""
    choice_rationale: str = ""
    rejected_rationale: dict[str, str] = Field(default_factory=dict)
    migration_plan: MigrationPlan | None = None
    operating_mode: str = "advisory_only"
    approval_status: str = "pending_human"
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def blocked(self) -> bool:
        return any(s.blocking and s.score < 0.5 for s in self.review_scores)
