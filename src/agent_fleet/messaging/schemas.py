"""Typed inter-agent messages for the operating chain.

Every stage handoff uses a versioned message schema. Authorities to
approve / reject / reduce / pause / close are explicit fields — never implied.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    MARKET_DATA = "market_data"
    NEWS_EVENT = "news_event"
    DATA_VALIDATED = "data_validated"
    RESEARCH_NOTE = "research_note"
    SIGNAL = "signal"
    TRADE_PROPOSAL = "trade_proposal"
    VALIDATION_RESULT = "validation_result"
    PORTFOLIO_EVALUATION = "portfolio_evaluation"
    RISK_DECISION = "risk_decision"
    CAPITAL_STEWARD_DECISION = "capital_steward_decision"
    EXECUTION_ORDER = "execution_order"
    FILL_REPORT = "fill_report"
    POSITION_UPDATE = "position_update"
    ALERT = "alert"
    ATTRIBUTION_REPORT = "attribution_report"
    IMPROVEMENT_PROPOSAL = "improvement_proposal"
    GOVERNANCE_EVENT = "governance_event"
    EMERGENCY_HALT = "emergency_halt"
    HEARTBEAT = "heartbeat"


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"
    COVER = "cover"
    SHORT = "short"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class DecisionAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REDUCE = "reduce"
    PAUSE = "pause"
    CLOSE = "close"
    DEFER = "defer"


class Envelope(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    causation_id: str | None = None
    message_type: MessageType
    source_agent_id: str
    target_agent_ids: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0"
    environment: str = "paper"
    payload: dict[str, Any]
    audit_tags: list[str] = Field(default_factory=list)


class MarketDataPayload(BaseModel):
    symbol: str
    venue: str
    ts: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: float | None = None
    source_id: str
    quality_score: float = 1.0


class NewsEventPayload(BaseModel):
    event_id: str
    headline: str
    source_id: str
    published_at: datetime
    symbols: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    sentiment: float | None = None
    verified: bool = False
    raw_uri: str | None = None


class ResearchNotePayload(BaseModel):
    note_id: str
    thesis: str
    symbols: list[str]
    horizon: str
    conviction: float = Field(ge=0, le=1)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    signal_hints: list[str] = Field(default_factory=list)
    author_agent_id: str


class SignalPayload(BaseModel):
    signal_id: str
    symbol: str
    direction: Side
    strength: float = Field(ge=-1, le=1)
    horizon: str
    features: dict[str, float] = Field(default_factory=dict)
    model_ids: list[str] = Field(default_factory=list)
    regime: str | None = None
    expires_at: datetime | None = None


class TradeProposalPayload(BaseModel):
    proposal_id: str
    strategy_agent_id: str
    strategy_version: str
    symbol: str
    side: Side
    order_type: OrderType = OrderType.LIMIT
    quantity_hint: float | None = None  # hint only; portfolio/risk size
    limit_price: float | None = None
    stop_price: float | None = None
    thesis: str
    setup_rules_fired: list[str]
    invalidation_rules: list[str]
    expected_holding_period: str
    risk_per_trade_pct_nav_request: float | None = None
    supporting_signal_ids: list[str] = Field(default_factory=list)
    supporting_research_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationResultPayload(BaseModel):
    proposal_id: str
    validator_agent_id: str
    passed: bool
    checks: list[dict[str, Any]]
    reasons: list[str] = Field(default_factory=list)


class PortfolioEvaluationPayload(BaseModel):
    proposal_id: str
    action: DecisionAction
    recommended_quantity: float | None = None
    recommended_risk_pct_nav: float | None = None
    portfolio_impact: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class RiskDecisionPayload(BaseModel):
    proposal_id: str
    action: DecisionAction
    approved_quantity: float | None = None
    max_loss_pct_nav: float | None = None
    constraints_applied: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    veto: bool = False


class CapitalStewardDecisionPayload(BaseModel):
    proposal_id: str
    action: DecisionAction
    reasons: list[str] = Field(default_factory=list)
    quality_score: float | None = None
    veto: bool = False


class ExecutionOrderPayload(BaseModel):
    order_id: str
    proposal_id: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None
    authorized_by: list[str]
    paper: bool = True


class FillReportPayload(BaseModel):
    order_id: str
    fill_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    fees: float = 0.0
    slippage_bps: float | None = None
    filled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    paper: bool = True


class AttributionReportPayload(BaseModel):
    report_id: str
    proposal_id: str | None = None
    strategy_agent_id: str
    pnl: float
    alpha_attribution: dict[str, float] = Field(default_factory=dict)
    execution_quality: dict[str, float] = Field(default_factory=dict)
    lessons: list[str] = Field(default_factory=list)


class ImprovementProposalPayload(BaseModel):
    change_id: str
    target_agent_id: str
    description: str
    hypothesis: str
    evidence: list[str]
    proposed_diff_summary: str
    status: str = "documented"  # follows controlled learning chain
    environment: str = "experimental"
