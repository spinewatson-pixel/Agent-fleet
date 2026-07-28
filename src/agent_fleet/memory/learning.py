"""Controlled learning state machine.

document → statistical_test → out_of_sample_test → paper_trade →
risk_review → version → approve → gradual_deploy
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class LearningStage(str, Enum):
    DOCUMENTED = "documented"
    STATISTICAL_TEST = "statistical_test"
    OUT_OF_SAMPLE = "out_of_sample_test"
    PAPER_TRADE = "paper_trade"
    RISK_REVIEW = "risk_review"
    VERSIONED = "version"
    APPROVED = "approve"
    GRADUAL_DEPLOY = "gradual_deploy"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


STAGE_ORDER = [
    LearningStage.DOCUMENTED,
    LearningStage.STATISTICAL_TEST,
    LearningStage.OUT_OF_SAMPLE,
    LearningStage.PAPER_TRADE,
    LearningStage.RISK_REVIEW,
    LearningStage.VERSIONED,
    LearningStage.APPROVED,
    LearningStage.GRADUAL_DEPLOY,
]


class ChangeRequest(BaseModel):
    change_id: str
    target_agent_id: str
    hypothesis: str
    description: str
    evidence: list[str] = Field(default_factory=list)
    stage: LearningStage = LearningStage.DOCUMENTED
    experimental_only: bool = True
    production_rules_touched: bool = False
    approvals: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    def can_advance(self) -> bool:
        if self.production_rules_touched and self.experimental_only is False:
            # production changes require full chain + approvals
            return len(self.approvals) >= 2
        return True

    def advance(self, to: LearningStage, approver: str | None = None, note: str = "") -> None:
        if self.stage == LearningStage.REJECTED:
            raise RuntimeError("Cannot advance rejected change")
        if to == LearningStage.REJECTED:
            self.stage = to
            if note:
                self.notes.append(note)
            return
        cur_idx = STAGE_ORDER.index(self.stage)
        new_idx = STAGE_ORDER.index(to)
        if new_idx != cur_idx + 1:
            raise ValueError(f"Invalid transition {self.stage} → {to}; must be sequential")
        if to in {LearningStage.RISK_REVIEW, LearningStage.APPROVED} and approver:
            self.approvals.append(approver)
        if to == LearningStage.GRADUAL_DEPLOY and self.production_rules_touched:
            required = {"RISK-APPR-001", "GOV-COMP-001"}
            if not required.issubset(set(self.approvals)):
                raise PermissionError(f"Missing approvals {required - set(self.approvals)}")
        self.stage = to
        if note:
            self.notes.append(note)


class LearningRegistry:
    def __init__(self) -> None:
        self.changes: dict[str, ChangeRequest] = {}

    def register(self, change: ChangeRequest) -> None:
        if not change.experimental_only and change.production_rules_touched:
            # still allowed to register, but deploy gated
            pass
        self.changes[change.change_id] = change

    def get(self, change_id: str) -> ChangeRequest:
        return self.changes[change_id]
