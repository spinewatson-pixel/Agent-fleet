"""Shared contract builders for institutional agents."""

from __future__ import annotations

from agent_fleet.schemas.contracts import (
    AgentOperatingContract,
    ApprovalRequirements,
    EntryExitRules,
    ExecutionPermissions,
    FailureShutdownBehavior,
    PositionSizingRules,
    SelfImprovementGate,
    SetupDetectionRule,
)
from agent_fleet.schemas.enums import AgentRole, DeploymentStatus, MarketRegime


def strategy_approval() -> ApprovalRequirements:
    return ApprovalRequirements(
        requires_independent_validation=True,
        requires_portfolio_evaluation=True,
        requires_risk_approval=True,
        requires_capital_stewardship_review=True,
        requires_governance_check=True,
        can_self_approve=False,
        can_self_execute=False,
        can_set_own_capital_limits=False,
        can_evaluate_own_performance=False,
    )


def strategy_execution_perms() -> ExecutionPermissions:
    return ExecutionPermissions(
        may_propose_trades=True,
        may_place_orders=False,
        may_cancel_orders=False,
        may_force_close=False,
        paper_only=True,
        live_enabled=False,
        max_notional_usd=0.0,
    )


def default_shutdown(escalate_to: list[str]) -> FailureShutdownBehavior:
    return FailureShutdownBehavior(
        on_data_gap="pause_new_proposals; alert GOV-OPS-001",
        on_model_error="disable_agent; escalate",
        on_limit_breach="halt_agent; notify PORT-RISK-001",
        on_repeated_rejects="reduce_proposal_rate; review after 10 rejects/day",
        kill_switch_triggers=[
            "daily_loss_halt",
            "drawdown_halt",
            "data_integrity_fail",
            "governance_shutdown",
        ],
        escalate_to=escalate_to,
    )


def default_improvement() -> SelfImprovementGate:
    return SelfImprovementGate()


def build_strategy_contract(
    *,
    agent_name: str,
    agent_id: str,
    supervisory_agent_id: str,
    strategy: str,
    economic_rationale: str,
    assets_permitted: list[str],
    markets_permitted: list[str],
    holding_period_days_min: int,
    holding_period_days_max: int,
    trading_frequency: str,
    valid_regimes: list[MarketRegime],
    invalid_regimes: list[MarketRegime],
    required_data_inputs: list[str],
    data_sources: dict[str, str],
    indicators_features_models: list[str],
    setup_rules: list[SetupDetectionRule],
    entry_exit: EntryExitRules,
    position_sizing: PositionSizingRules,
    information_received_from: list[str],
    outputs_sent_to: list[str],
    monitoring_after_entry: list[str],
    strategy_version: str = "0.1.0",
    department: str = "trading_operations",
) -> AgentOperatingContract:
    return AgentOperatingContract(
        agent_name=agent_name,
        agent_id=agent_id,
        department=department,
        supervisory_agent_id=supervisory_agent_id,
        role=AgentRole.STRATEGY,
        strategy=strategy,
        economic_rationale=economic_rationale,
        assets_permitted=assets_permitted,
        markets_permitted=markets_permitted,
        holding_period_days_min=holding_period_days_min,
        holding_period_days_max=holding_period_days_max,
        trading_frequency=trading_frequency,
        valid_regimes=valid_regimes,
        invalid_regimes=invalid_regimes,
        required_data_inputs=required_data_inputs,
        data_sources=data_sources,
        indicators_features_models=indicators_features_models,
        setup_detection_rules=setup_rules,
        entry_exit=entry_exit,
        position_sizing=position_sizing,
        information_received_from=information_received_from,
        outputs_sent_to=outputs_sent_to,
        approval=strategy_approval(),
        execution=strategy_execution_perms(),
        monitoring_after_entry=monitoring_after_entry,
        memory_retained=[
            "proposals",
            "fills_received",
            "rejects",
            "feature_snapshots",
            "regime_at_entry",
        ],
        performance_measurements=[
            "hit_rate",
            "avg_pnl_bps",
            "sharpe_paper",
            "max_drawdown_contrib",
            "slippage_vs_expected",
            "reject_rate",
        ],
        failure_shutdown=default_shutdown(
            [supervisory_agent_id, "PORT-RISK-001", "GOV-OPS-001"]
        ),
        testing_deployment_status=DeploymentStatus.PAPER,
        strategy_version=strategy_version,
        self_improvement=default_improvement(),
        owns_stages=["strategy_proposal"],
        authority_actions=[],
    )
