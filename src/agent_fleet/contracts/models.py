"""Agent Operating Contract and authority models.

Every runtime agent must have a complete, enforceable operating contract.
Strategy agents propose only; they never self-approve, self-size capital,
self-execute, or self-score for live decision authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentRole(str, Enum):
    ORCHESTRATION = "orchestration"
    DATA = "data"
    RESEARCH = "research"
    STRATEGY = "strategy"
    VALIDATION = "validation"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    CAPITAL_STEWARDSHIP = "capital_stewardship"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    ATTRIBUTION = "attribution"
    GOVERNANCE = "governance"
    LEARNING = "learning"
    INFRASTRUCTURE = "infrastructure"


class Environment(str, Enum):
    PRODUCTION = "production"
    EXPERIMENTAL = "experimental"
    PAPER = "paper"
    BACKTEST = "backtest"


class DeploymentStatus(str, Enum):
    DESIGN = "design"
    UNIT_TESTED = "unit_tested"
    BACKTESTED = "backtested"
    PAPER_ACTIVE = "paper_active"
    PAPER_PASSED = "paper_passed"
    LIVE_SHADOW = "live_shadow"
    LIVE_LIMITED = "live_limited"
    LIVE_FULL = "live_full"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"
    RETIRED = "retired"


class ApprovalAuthority(str, Enum):
    NONE = "none"
    PROPOSE = "propose"
    VALIDATE = "validate"
    REDUCE = "reduce"
    APPROVE = "approve"
    REJECT = "reject"
    PAUSE = "pause"
    CLOSE = "close"
    EMERGENCY_HALT = "emergency_halt"
    VERSION_APPROVE = "version_approve"


class HoldingPeriod(str, Enum):
    INTRADAY = "intraday"
    SWING_DAYS = "swing_days"
    SWING_WEEKS = "swing_weeks"
    POSITION_MONTHS = "position_months"
    LONG_TERM_YEARS = "long_term_years"


class MarketRegime(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    HIGH_VOL = "high_vol"
    LOW_VOL = "low_vol"
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    EVENT_DRIVEN = "event_driven"
    ILLIQUID = "illiquid"
    ANY = "any"


class DataSourceRef(BaseModel):
    source_id: str
    name: str
    category: str
    fields: list[str]
    latency_sla_ms: int | None = None
    verified: bool = False
    notes: str = ""


class SetupRule(BaseModel):
    rule_id: str
    description: str
    expression: str  # measurable predicate, e.g. "rsi_14 < 30 AND close > sma_200"
    required: bool = True


class TradeRules(BaseModel):
    entry: list[SetupRule]
    exit: list[SetupRule]
    stop_loss: list[SetupRule]
    invalidation: list[SetupRule]


class PositionSizingLimits(BaseModel):
    method: str  # e.g. "volatility_target", "fixed_fraction", "risk_per_trade"
    max_position_pct_nav: float = Field(ge=0, le=1)
    max_risk_per_trade_pct_nav: float = Field(ge=0, le=1)
    max_gross_exposure_pct_nav: float = Field(ge=0, le=5)
    max_net_exposure_pct_nav: float = Field(ge=0, le=2)
    max_sector_pct_nav: float = Field(ge=0, le=1)
    max_correlated_group_pct_nav: float = Field(ge=0, le=1)
    notes: str = ""

    @field_validator(
        "max_position_pct_nav",
        "max_risk_per_trade_pct_nav",
        "max_sector_pct_nav",
        "max_correlated_group_pct_nav",
    )
    @classmethod
    def non_strategy_self_approval(cls, v: float) -> float:
        return v


class AgentIOChannel(BaseModel):
    agent_id: str
    message_types: list[str]
    required: bool = True
    description: str = ""


class PerformanceMetric(BaseModel):
    name: str
    definition: str
    target: str | None = None
    gate: str | None = None  # hard gate expression if any


class FailureBehavior(BaseModel):
    on_data_outage: str
    on_model_failure: str
    on_drawdown_breach: str
    on_permission_violation: str
    shutdown_triggers: list[str]
    recovery_requires: list[str]


class SelfImprovementGate(BaseModel):
    """Controlled learning — never uncontrolled self-modification."""

    may_propose_changes: bool = True
    may_alter_production_rules: bool = False
    required_steps: list[str] = Field(
        default_factory=lambda: [
            "document",
            "statistical_test",
            "out_of_sample_test",
            "paper_trade",
            "risk_review",
            "version",
            "approve",
            "gradual_deploy",
        ]
    )
    min_oos_sharpe: float | None = None
    min_paper_days: int = 20
    requires_approvers: list[str] = Field(
        default_factory=lambda: ["RISK-APPR-001", "GOV-COMP-001", "SYS-ORCH-001"]
    )


class AgentOperatingContract(BaseModel):
    """Complete enforceable operating contract for one agent."""

    agent_name: str
    agent_id: str
    department: str
    supervisory_agent_id: str
    role: AgentRole
    strategy_and_rationale: str
    assets_and_markets_permitted: list[str]
    holding_period: HoldingPeriod
    trading_frequency: str
    valid_regimes: list[MarketRegime]
    required_data_inputs: list[DataSourceRef]
    indicators_features_models: list[str]
    setup_detection_rules: list[SetupRule]
    trade_rules: TradeRules
    position_sizing_and_exposure: PositionSizingLimits
    information_received_from: list[AgentIOChannel]
    outputs_sent_to: list[AgentIOChannel]
    approval_requirements: list[str]
    execution_permissions: list[str]
    authorities: list[ApprovalAuthority]
    monitoring_after_entry: list[str]
    memory_retained: list[str]
    performance_measurements: list[PerformanceMetric]
    failure_and_shutdown: FailureBehavior
    testing_and_deployment_status: DeploymentStatus
    strategy_version: str
    self_improvement_conditions: SelfImprovementGate
    environment: Environment = Environment.PAPER
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""

    @field_validator("authorities")
    @classmethod
    def strategy_cannot_self_approve(cls, v: list[ApprovalAuthority], info: Any) -> list[ApprovalAuthority]:
        role = info.data.get("role")
        if role == AgentRole.STRATEGY:
            forbidden = {
                ApprovalAuthority.APPROVE,
                ApprovalAuthority.EMERGENCY_HALT,
                ApprovalAuthority.VERSION_APPROVE,
            }
            overlap = forbidden.intersection(set(v))
            if overlap:
                raise ValueError(f"Strategy agents cannot hold authorities: {overlap}")
            if ApprovalAuthority.PROPOSE not in v:
                v = list(v) + [ApprovalAuthority.PROPOSE]
        return v

    @field_validator("execution_permissions")
    @classmethod
    def strategy_cannot_execute(cls, v: list[str], info: Any) -> list[str]:
        role = info.data.get("role")
        if role == AgentRole.STRATEGY:
            blocked = [p for p in v if "execute" in p.lower() or "order" in p.lower()]
            if blocked:
                raise ValueError(f"Strategy agents cannot have execution permissions: {blocked}")
        return v


class DecisionRecord(BaseModel):
    """Final architecture / risk / governance decision with dissent trail."""

    decision_id: str
    title: str
    decided_by: str
    reasoning: str
    supporting_evidence: list[str]
    dissenting_views: list[str] = Field(default_factory=list)
    vetoes: list[str] = Field(default_factory=list)
    implementation_priority: str  # P0 / P1 / P2
    status: str = "accepted"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
