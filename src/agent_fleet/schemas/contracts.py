"""Agent Operating Contract — enforceable specification for every agent.

Vague fields are forbidden. Each contract translates strategy into measurable
rules, required inputs, structured outputs, and permissions.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from agent_fleet.schemas.enums import AgentRole, DeploymentStatus, MarketRegime


class PositionSizingRules(BaseModel):
    method: str  # fixed_fraction | volatility_target | kelly_fraction_capped
    max_pct_nav: float
    min_pct_nav: float
    vol_target_ann: Optional[float] = None
    kelly_fraction_cap: Optional[float] = None
    max_concurrent_positions: int
    max_sector_pct: float
    notes: str = ""


class SetupDetectionRule(BaseModel):
    rule_id: str
    description: str
    expression: str  # measurable predicate, e.g. "close > sma_50 AND rsi_14 < 30"
    required_inputs: list[str]
    lookback: int


class EntryExitRules(BaseModel):
    entry_rules: list[str]
    exit_rules: list[str]
    stop_loss_rule: str
    take_profit_rule: Optional[str] = None
    invalidation_rules: list[str]
    time_stop_days: Optional[int] = None


class ApprovalRequirements(BaseModel):
    requires_independent_validation: bool = True
    requires_portfolio_evaluation: bool = True
    requires_risk_approval: bool = True
    requires_capital_stewardship_review: bool = True
    requires_governance_check: bool = True
    can_self_approve: bool = False
    can_self_execute: bool = False
    can_set_own_capital_limits: bool = False
    can_evaluate_own_performance: bool = False


class ExecutionPermissions(BaseModel):
    may_propose_trades: bool = False
    may_place_orders: bool = False
    may_cancel_orders: bool = False
    may_force_close: bool = False
    paper_only: bool = True
    live_enabled: bool = False
    max_notional_usd: float = 0.0


class FailureShutdownBehavior(BaseModel):
    on_data_gap: str
    on_model_error: str
    on_limit_breach: str
    on_repeated_rejects: str
    kill_switch_triggers: list[str]
    escalate_to: list[str]


class SelfImprovementGate(BaseModel):
    may_propose_changes: bool = True
    may_auto_apply_to_production: bool = False
    required_sequence: list[str] = Field(
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
    min_oos_sharpe: float = 0.5
    min_paper_days: int = 20
    max_parameter_change_pct: float = 20.0


class AgentOperatingContract(BaseModel):
    """Complete operating contract for one agent."""

    agent_name: str
    agent_id: str
    department: str
    supervisory_agent_id: str
    role: AgentRole

    strategy: str
    economic_rationale: str

    assets_permitted: list[str]
    markets_permitted: list[str]
    excluded_assets: list[str] = Field(default_factory=list)

    holding_period_days_min: int
    holding_period_days_max: int
    trading_frequency: str  # intraday | daily | weekly | event_driven | low_turnover

    valid_regimes: list[MarketRegime]
    invalid_regimes: list[MarketRegime] = Field(default_factory=list)

    required_data_inputs: list[str]
    data_sources: dict[str, str]  # input -> source system

    indicators_features_models: list[str]
    setup_detection_rules: list[SetupDetectionRule]
    entry_exit: EntryExitRules
    position_sizing: PositionSizingRules

    information_received_from: list[str]  # agent ids
    outputs_sent_to: list[str]

    approval: ApprovalRequirements
    execution: ExecutionPermissions

    monitoring_after_entry: list[str]
    memory_retained: list[str]
    performance_measurements: list[str]

    failure_shutdown: FailureShutdownBehavior

    testing_deployment_status: DeploymentStatus
    strategy_version: str
    self_improvement: SelfImprovementGate

    owns_stages: list[str] = Field(default_factory=list)
    authority_actions: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
