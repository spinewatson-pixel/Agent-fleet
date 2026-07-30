"""Structured inter-agent message contracts.

Every handoff in the operating chain uses MessageEnvelope + typed payload.
Strategy agents emit TradeProposal only; they never set capital limits,
approve themselves, execute, or grade their own performance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from agent_fleet.schemas.enums import (
    ActionType,
    ApprovalStatus,
    MarketRegime,
    MessageType,
    Side,
    Stage,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


class MessageEnvelope(BaseModel):
    """Universal wrapper for all agent-to-agent communication."""

    message_id: str = Field(default_factory=_new_id)
    correlation_id: str = Field(default_factory=_new_id)
    parent_message_id: Optional[str] = None
    message_type: MessageType
    stage: Stage
    sender_id: str
    recipient_ids: list[str]
    created_at: datetime = Field(default_factory=_utcnow)
    environment: str = "paper"
    schema_version: str = "1.0.0"
    payload: dict[str, Any]
    lineage: list[str] = Field(default_factory=list)
    permissions_scope: list[str] = Field(default_factory=list)

    def with_child(self, **kwargs: Any) -> "MessageEnvelope":
        data = self.model_dump()
        data.update(kwargs)
        data["message_id"] = _new_id()
        data["parent_message_id"] = self.message_id
        data["created_at"] = _utcnow()
        lineage = list(self.lineage) + [self.message_id]
        data["lineage"] = lineage
        return MessageEnvelope(**data)


class MarketEvent(BaseModel):
    symbol: str
    event_type: str  # quote | bar | news | filing | earnings | macro | calendar
    source: str
    source_verified: bool
    timestamp: datetime
    tags: list[str] = Field(default_factory=list)
    normalized: dict[str, Any] = Field(default_factory=dict)
    raw_ref: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class ResearchSignal(BaseModel):
    signal_id: str = Field(default_factory=_new_id)
    research_agent_id: str
    symbol: str
    thesis: str
    direction: Side
    conviction: float = Field(ge=0.0, le=1.0)
    horizon_days: int = Field(gt=0)
    catalysts: list[str] = Field(default_factory=list)
    regime_context: list[MarketRegime] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    version: str = "1.0.0"


class TradeProposal(BaseModel):
    """Strategy output. Capital limits and approval are NOT set here."""

    proposal_id: str = Field(default_factory=_new_id)
    strategy_agent_id: str
    strategy_version: str
    symbol: str
    side: Side
    thesis: str
    setup_rules_fired: list[str]
    entry_price_target: float
    stop_loss: float
    take_profit: Optional[float] = None
    invalidation_rules: list[str]
    suggested_size_pct_nav: float = Field(gt=0.0, le=5.0)
    suggested_size_usd: Optional[float] = Field(default=None, gt=0.0)
    holding_period_days_min: int
    holding_period_days_max: int
    valid_regimes: list[MarketRegime]
    current_regime: MarketRegime
    required_data_inputs: list[str]
    research_signal_ids: list[str] = Field(default_factory=list)
    evidence_package_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    expected_edge_bps: float
    max_slippage_bps: float = 15.0
    time_in_force: str = "DAY"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("stop_loss")
    @classmethod
    def stop_must_differ(cls, v: float, info: Any) -> float:
        entry = info.data.get("entry_price_target")
        if entry is not None and v == entry:
            raise ValueError("stop_loss must differ from entry_price_target")
        return v


class ValidationResult(BaseModel):
    proposal_id: str
    validator_agent_id: str
    passed: bool
    checks: dict[str, bool]
    defects: list[str] = Field(default_factory=list)
    notes: str = ""


class PortfolioVerdict(BaseModel):
    proposal_id: str
    portfolio_agent_id: str
    action: ActionType
    approved_size_pct_nav: Optional[float] = None
    approved_size_usd: Optional[float] = None
    reasons: list[str]
    exposure_after: dict[str, float] = Field(default_factory=dict)
    correlation_flags: list[str] = Field(default_factory=list)


class RiskVerdict(BaseModel):
    proposal_id: str
    risk_agent_id: str
    action: ActionType
    approved_size_pct_nav: Optional[float] = None
    approved_size_usd: Optional[float] = None
    stress_pnl_pct: Optional[float] = None
    limit_breaches: list[str] = Field(default_factory=list)
    reasons: list[str]
    veto: bool = False


class ApprovalDecision(BaseModel):
    proposal_id: str
    status: ApprovalStatus
    final_size_pct_nav: Optional[float] = None
    final_size_usd: Optional[float] = None
    approving_agents: list[str]
    rejecting_agents: list[str] = Field(default_factory=list)
    authority_chain: list[str]
    reasons: list[str]
    execution_authorized: bool = False


class ExecutionReport(BaseModel):
    proposal_id: str
    order_id: str = Field(default_factory=_new_id)
    execution_agent_id: str
    symbol: str
    side: Side
    requested_qty: float
    filled_qty: float
    avg_price: float
    slippage_bps: float
    status: str  # filled | partial | rejected | cancelled
    paper: bool = True
    timestamp: datetime = Field(default_factory=_utcnow)


class MonitoringAlert(BaseModel):
    position_id: str
    proposal_id: str
    alert_type: str  # stop | invalidation | regime_break | drawdown | data_gap
    severity: str  # info | warn | critical
    message: str
    recommended_action: ActionType
    timestamp: datetime = Field(default_factory=_utcnow)


class AttributionReport(BaseModel):
    proposal_id: str
    strategy_agent_id: str
    pnl: float
    pnl_bps: float
    holding_days: float
    alpha_estimate: float
    factor_attribution: dict[str, float] = Field(default_factory=dict)
    execution_cost_bps: float
    decision_quality_score: float = Field(ge=0.0, le=1.0)
    lessons: list[str] = Field(default_factory=list)


class ImprovementProposal(BaseModel):
    """Controlled learning artifact — never auto-applied to production."""

    improvement_id: str = Field(default_factory=_new_id)
    proposer_agent_id: str
    target_agent_id: str
    change_summary: str
    hypothesis: str
    evidence_refs: list[str]
    required_tests: list[str] = Field(
        default_factory=lambda: [
            "documented",
            "statistical_test",
            "out_of_sample",
            "paper_trade",
            "risk_review",
            "versioned",
            "approved",
            "gradual_deploy",
        ]
    )
    status: str = "proposed"  # proposed | testing | paper | risk_review | approved | rejected | deployed
    production_mutation_allowed: bool = False
