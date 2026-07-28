"""Factory helpers for complete Agent Operating Contracts."""

from __future__ import annotations

from agent_fleet.contracts.models import (
    AgentIOChannel,
    AgentOperatingContract,
    AgentRole,
    ApprovalAuthority,
    DataSourceRef,
    DeploymentStatus,
    Environment,
    FailureBehavior,
    HoldingPeriod,
    MarketRegime,
    PerformanceMetric,
    PositionSizingLimits,
    SelfImprovementGate,
    SetupRule,
    TradeRules,
)


def _fail_default() -> FailureBehavior:
    return FailureBehavior(
        on_data_outage="pause_new_proposals; keep existing positions under monitor",
        on_model_failure="disable agent; alert GOV-COMP-001 and SYS-ORCH-001",
        on_drawdown_breach="halt agent proposals; RISK-APPR-001 may force flatten",
        on_permission_violation="immediate shutdown; escalate to GOV-COMP-001",
        shutdown_triggers=[
            "permission_violation",
            "repeated_validation_failure>=5",
            "strategy_drawdown>=limit",
            "governance_halt",
        ],
        recovery_requires=[
            "incident_report",
            "RISK-APPR-001 approval",
            "GOV-COMP-001 approval",
            "contract_version_bump",
        ],
    )


def _improve_default(approvers: list[str] | None = None) -> SelfImprovementGate:
    return SelfImprovementGate(
        may_propose_changes=True,
        may_alter_production_rules=False,
        requires_approvers=approvers
        or ["RISK-APPR-001", "GOV-COMP-001", "SYS-ORCH-001"],
    )


def market_data_ref() -> DataSourceRef:
    return DataSourceRef(
        source_id="SRC-MKT-OHLCV",
        name="Normalized OHLCV",
        category="market_price",
        fields=["open", "high", "low", "close", "volume"],
        latency_sla_ms=1000,
        verified=True,
    )


def strategy_contract(
    *,
    agent_name: str,
    agent_id: str,
    rationale: str,
    assets: list[str],
    holding: HoldingPeriod,
    frequency: str,
    regimes: list[MarketRegime],
    indicators: list[str],
    setups: list[SetupRule],
    entries: list[SetupRule],
    exits: list[SetupRule],
    stops: list[SetupRule],
    invalidations: list[SetupRule],
    sizing: PositionSizingLimits,
    version: str = "0.1.0",
) -> AgentOperatingContract:
    return AgentOperatingContract(
        agent_name=agent_name,
        agent_id=agent_id,
        department="Strategy",
        supervisory_agent_id="SYS-ORCH-001",
        role=AgentRole.STRATEGY,
        strategy_and_rationale=rationale,
        assets_and_markets_permitted=assets,
        holding_period=holding,
        trading_frequency=frequency,
        valid_regimes=regimes,
        required_data_inputs=[market_data_ref()],
        indicators_features_models=indicators,
        setup_detection_rules=setups,
        trade_rules=TradeRules(
            entry=entries, exit=exits, stop_loss=stops, invalidation=invalidations
        ),
        position_sizing_and_exposure=sizing,
        information_received_from=[
            AgentIOChannel(
                agent_id="DATA-VAL-001",
                message_types=["data_validated"],
                description="Validated market/news context",
            ),
            AgentIOChannel(
                agent_id="RSH-FUND-001",
                message_types=["research_note", "signal"],
                required=False,
                description="Fundamental/event research signals",
            ),
            AgentIOChannel(
                agent_id="RSH-QUANT-001",
                message_types=["signal"],
                required=False,
                description="Quant feature signals",
            ),
            AgentIOChannel(
                agent_id="MON-REGIME-001",
                message_types=["alert"],
                description="Regime classification updates",
            ),
        ],
        outputs_sent_to=[
            AgentIOChannel(
                agent_id="SIG-VAL-001",
                message_types=["trade_proposal"],
                description="Proposals for independent validation",
            ),
        ],
        approval_requirements=[
            "SIG-VAL-001 must pass",
            "PORT-ALLOC-001 evaluation required",
            "RISK-APPR-001 approval required",
            "CAP-STEW-001 review for QUAL/long-term or elevated size",
        ],
        execution_permissions=[],  # strategy never executes
        authorities=[ApprovalAuthority.PROPOSE],
        monitoring_after_entry=[
            "Track invalidation rules each bar",
            "Emit alert on stop proximity",
            "Do not modify size without new approved proposal",
        ],
        memory_retained=[
            "proposals",
            "fired_setup_rules",
            "regime_at_entry",
            "outcomes_via_attribution_feed",
        ],
        performance_measurements=[
            PerformanceMetric(
                name="hit_rate",
                definition="winning_trades / closed_trades",
                gate=None,
            ),
            PerformanceMetric(
                name="profit_factor",
                definition="gross_wins / gross_losses",
                gate="profit_factor >= 1.2 after 40 trades",
            ),
            PerformanceMetric(
                name="max_drawdown",
                definition="peak-to-trough equity on strategy book",
                gate="max_drawdown <= contract limit",
            ),
            PerformanceMetric(
                name="proposal_accept_rate",
                definition="approved / proposed",
                target="informational",
            ),
        ],
        failure_and_shutdown=_fail_default(),
        testing_and_deployment_status=DeploymentStatus.DESIGN,
        strategy_version=version,
        self_improvement_conditions=_improve_default(),
        environment=Environment.PAPER,
    )


def infra_contract(
    *,
    agent_name: str,
    agent_id: str,
    department: str,
    supervisor: str,
    role: AgentRole,
    rationale: str,
    authorities: list[ApprovalAuthority],
    execution_permissions: list[str] | None = None,
    inputs: list[AgentIOChannel] | None = None,
    outputs: list[AgentIOChannel] | None = None,
    version: str = "0.1.0",
) -> AgentOperatingContract:
    return AgentOperatingContract(
        agent_name=agent_name,
        agent_id=agent_id,
        department=department,
        supervisory_agent_id=supervisor,
        role=role,
        strategy_and_rationale=rationale,
        assets_and_markets_permitted=["*"] if role != AgentRole.STRATEGY else [],
        holding_period=HoldingPeriod.POSITION_MONTHS,
        trading_frequency="continuous_service",
        valid_regimes=[MarketRegime.ANY],
        required_data_inputs=[],
        indicators_features_models=[],
        setup_detection_rules=[],
        trade_rules=TradeRules(entry=[], exit=[], stop_loss=[], invalidation=[]),
        position_sizing_and_exposure=PositionSizingLimits(
            method="n/a",
            max_position_pct_nav=0.0,
            max_risk_per_trade_pct_nav=0.0,
            max_gross_exposure_pct_nav=0.0,
            max_net_exposure_pct_nav=0.0,
            max_sector_pct_nav=0.0,
            max_correlated_group_pct_nav=0.0,
            notes="Non-strategy agent",
        ),
        information_received_from=inputs or [],
        outputs_sent_to=outputs or [],
        approval_requirements=[],
        execution_permissions=execution_permissions or [],
        authorities=authorities,
        monitoring_after_entry=[],
        memory_retained=["service_logs", "audit_events"],
        performance_measurements=[
            PerformanceMetric(
                name="availability",
                definition="uptime_ratio",
                gate="availability >= 0.995",
            )
        ],
        failure_and_shutdown=_fail_default(),
        testing_and_deployment_status=DeploymentStatus.DESIGN,
        strategy_version=version,
        self_improvement_conditions=_improve_default(),
        environment=Environment.PAPER,
    )
