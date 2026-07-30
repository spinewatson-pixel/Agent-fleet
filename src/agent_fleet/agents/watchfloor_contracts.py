"""Generate measurable AgentOperatingContract stubs for Watchfloor proposers.

Role text in the registry is not enough for FIT-1. Every proposer needs
setup_detection_rules, entry/exit/stop, and invalidation fields before paper
proposals are admitted.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from agent_fleet.agents.contracts_factory import (
    build_strategy_contract,
    default_improvement,
    default_shutdown,
    strategy_approval,
    strategy_execution_perms,
)
from agent_fleet.registry.watchfloor import all_agents, hard_rules, proposers
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


def _ticker_from_agent(agent: dict[str, Any]) -> str | None:
    assets = agent.get("assets_permitted") or []
    if assets:
        return str(assets[0]).upper()
    tags = [t.upper() for t in (agent.get("tags") or [])]
    skip = {"PAPER TRADER", "LONG ONLY", "SHORT ONLY", "SWING", "SCOUT", "NOVEL"}
    for tag in tags:
        if tag not in skip and 1 <= len(tag) <= 5 and tag.isalpha():
            return tag
    return None


def _holding_bounds(agent: dict[str, Any]) -> tuple[int, int, str]:
    hp = (agent.get("holding_period") or "").lower()
    if hp == "intraday":
        return 0, 1, "intraday"
    if "1_to_5" in hp or "swing" in hp:
        cap = int(agent.get("holding_cap_days") or hard_rules().get("swing_hard_cap_days", 7))
        return 1, min(cap, 7), "daily"
    if agent.get("division") == "quant":
        return 1, 20, "daily"
    if agent.get("division") == "funds":
        return 5, 90, "weekly"
    return 0, int(agent.get("holding_cap_days") or 5), "daily"


def _regimes(agent: dict[str, Any]) -> tuple[list[MarketRegime], list[MarketRegime]]:
    tags = " ".join(agent.get("tags") or []).lower()
    role = (agent.get("role") or "").lower()
    if "short" in tags or "short" in role or agent.get("side_restriction") == "SHORT ONLY":
        return (
            [
                MarketRegime.TRENDING_BEAR,
                MarketRegime.HIGH_VOLATILITY,
                MarketRegime.RANGE_BOUND,
                MarketRegime.RISK_OFF,
            ],
            [MarketRegime.TRENDING_BULL],
        )
    if agent.get("division") == "quant":
        return (
            [
                MarketRegime.TRENDING_BULL,
                MarketRegime.TRENDING_BEAR,
                MarketRegime.RANGE_BOUND,
                MarketRegime.HIGH_VOLATILITY,
                MarketRegime.LOW_VOLATILITY,
                MarketRegime.RISK_ON,
                MarketRegime.RISK_OFF,
            ],
            [],
        )
    return (
        [
            MarketRegime.TRENDING_BULL,
            MarketRegime.LOW_VOLATILITY,
            MarketRegime.RANGE_BOUND,
            MarketRegime.RISK_ON,
        ],
        [MarketRegime.RISK_OFF],
    )


def _sizing(agent: dict[str, Any]) -> PositionSizingRules:
    sizing = agent.get("sizing") or "fixed_1_2_usd"
    rules = hard_rules()
    lo, hi = rules.get("default_sizing_usd", [1, 2])
    if sizing == "fixed_1_2_usd":
        return PositionSizingRules(
            method="fixed_dollar_cohort",
            max_pct_nav=0.01,  # bookkeeping ceiling; binding size is USD
            min_pct_nav=0.00005,
            max_concurrent_positions=3,
            max_sector_pct=5.0,
            notes=f"Comparable cohort size ${lo}-${hi} USD (binding)",
        )
    if sizing == "experimental_variable":
        return PositionSizingRules(
            method="fixed_fraction",
            max_pct_nav=1.0,
            min_pct_nav=0.05,
            max_concurrent_positions=5,
            max_sector_pct=10.0,
            notes="Group F sizing lab — still paper-only, RISK-1 clamps",
        )
    # desk_set / None (quant/funds)
    return PositionSizingRules(
        method="fixed_fraction",
        max_pct_nav=2.0,
        min_pct_nav=0.1,
        max_concurrent_positions=8,
        max_sector_pct=15.0,
        notes="Desk-set %NAV sleeve; not cohort $1–2",
    )


def _setup_rules(agent: dict[str, Any], ticker: str | None) -> list[SetupDetectionRule]:
    aid = agent["id"]
    sym = ticker or "UNIVERSE"
    division = agent.get("division")
    tags = " ".join(agent.get("tags") or []).lower()
    side = (agent.get("side_restriction") or "").upper()
    rules: list[SetupDetectionRule] = []

    if division == "quant":
        rules.append(
            SetupDetectionRule(
                rule_id=f"{aid}-OOS-01",
                description="Quant sleeve requires evidence package before proposal",
                expression="evidence_package_id IS NOT NULL AND oos_pass == true",
                required_inputs=["evidence_package_id", "feature_vector", "oos_metrics"],
                lookback=252,
            )
        )
        rules.append(
            SetupDetectionRule(
                rule_id=f"{aid}-SIG-01",
                description="Model signal crosses admission threshold",
                expression="abs(model_score) >= admission_threshold AND regime NOT IN {RISK_OFF}",
                required_inputs=["model_score", "admission_threshold", "regime"],
                lookback=60,
            )
        )
        return rules

    if "scout" in tags or aid.startswith("SCOUT"):
        rules.append(
            SetupDetectionRule(
                rule_id=f"{aid}-MR-01",
                description="Mean-reversion scout z-score extreme",
                expression=f"abs(zscore_20({sym})) >= 2.0 AND volume_ratio_20 >= 1.2",
                required_inputs=["close", "volume", "zscore_20", "volume_ratio_20"],
                lookback=20,
            )
        )
    elif "swing" in tags or (agent.get("holding_period") or "").startswith("1_to_5"):
        rules.append(
            SetupDetectionRule(
                rule_id=f"{aid}-SW-01",
                description="Swing continuation after pullback",
                expression=(
                    f"close({sym}) > sma_20({sym}) AND rsi_14({sym}) BETWEEN 40 AND 65 "
                    f"AND holding_days_projected <= {hard_rules().get('swing_hard_cap_days', 7)}"
                ),
                required_inputs=["close", "sma_20", "rsi_14"],
                lookback=20,
            )
        )
    elif side == "SHORT ONLY" or "short" in tags:
        rules.append(
            SetupDetectionRule(
                rule_id=f"{aid}-SH-01",
                description="Short-side breakdown / failed bounce",
                expression=(
                    f"close({sym}) < sma_20({sym}) AND rsi_14({sym}) < 45 "
                    f"AND thesis_logged == true"
                ),
                required_inputs=["close", "sma_20", "rsi_14", "thesis_log"],
                lookback=20,
            )
        )
    else:
        rules.append(
            SetupDetectionRule(
                rule_id=f"{aid}-LG-01",
                description="Long-side specialist tape confirmation",
                expression=(
                    f"close({sym}) > sma_10({sym}) AND volume_ratio_10 >= 1.0 "
                    f"AND thesis_logged == true"
                ),
                required_inputs=["close", "sma_10", "volume_ratio_10", "thesis_log"],
                lookback=10,
            )
        )

    if agent.get("thesis_required", True) and division != "quant":
        rules.append(
            SetupDetectionRule(
                rule_id=f"{aid}-TH-01",
                description="Discretionary thesis must be logged before entry",
                expression="len(thesis_text) >= 8 AND thesis_timestamp <= now()",
                required_inputs=["thesis_log"],
                lookback=1,
            )
        )
    return rules


def _entry_exit(agent: dict[str, Any], ticker: str | None) -> EntryExitRules:
    sym = ticker or "symbol"
    hold_min, hold_max, _ = _holding_bounds(agent)
    side = (agent.get("side_restriction") or "").upper()
    if side == "SHORT ONLY":
        stop = f"stop = entry + 2 * atr_14({sym})"
        entry = [f"enter_short({sym}) when setup_rules_fired"]
    else:
        stop = f"stop = entry - 2 * atr_14({sym})"
        entry = [f"enter_long({sym}) when setup_rules_fired"]
    return EntryExitRules(
        entry_rules=entry,
        exit_rules=[
            "exit on stop",
            "exit on thesis_break",
            f"time_stop after {hold_max} day(s)",
            "exit on SEC-HALT / org halt",
        ],
        stop_loss_rule=stop,
        take_profit_rule=f"optional_tp = entry ± 3 * atr_14({sym})",
        invalidation_rules=[
            "thesis_break",
            "mandate_breach",
            "halt",
            "regime_invalid",
            "contract_incomplete",
        ],
        time_stop_days=max(hold_max, 1),
    )


def contract_for_proposer(agent: dict[str, Any]) -> AgentOperatingContract:
    """Build a measurable stub contract from registry metadata."""
    ticker = _ticker_from_agent(agent)
    hold_min, hold_max, freq = _holding_bounds(agent)
    valid, invalid = _regimes(agent)
    assets = list(agent.get("assets_permitted") or ([ticker] if ticker else ["US_EQUITIES"]))
    supervisor = agent.get("supervisor_id") or "HEAD-TRADE"
    setup = _setup_rules(agent, ticker)
    if not setup:
        raise ValueError(f"{agent['id']} produced empty setup_detection_rules")

    contract = build_strategy_contract(
        agent_name=agent.get("nick") or agent["id"],
        agent_id=agent["id"],
        supervisory_agent_id=supervisor,
        strategy=(agent.get("role") or agent["id"])[:240],
        economic_rationale=(
            f"Watchfloor paper proposer ({agent.get('department')}) — "
            f"proposes only; RISK-1/GOV-CHAIR/EXEC-1 decide and execute."
        ),
        assets_permitted=assets,
        markets_permitted=["US_EQUITIES"],
        holding_period_days_min=hold_min,
        holding_period_days_max=hold_max,
        trading_frequency=freq,
        valid_regimes=valid,
        invalid_regimes=invalid,
        required_data_inputs=sorted(
            {inp for rule in setup for inp in rule.required_inputs} | {"regime", "contract_id"}
        ),
        data_sources={
            "tape": "MKT-1",
            "thesis_log": "MEM-1",
            "regime": "REG-1",
            "evidence_package_id": "FIT-1",
        },
        indicators_features_models=["sma", "rsi_14", "atr_14", "zscore_20", "volume_ratio"],
        setup_rules=setup,
        entry_exit=_entry_exit(agent, ticker),
        position_sizing=_sizing(agent),
        information_received_from=["MKT-1", "CORP-1", "FORE-1", "REG-1", "MEM-1"],
        outputs_sent_to=["FIT-1", "RISK-1", "MEM-1"],
        monitoring_after_entry=["stop_distance", "thesis_intact", "regime_valid"],
        strategy_version="watchfloor-0.4.0",
        department=agent.get("department") or agent.get("division") or "trade",
    )
    # Watchfloor escalate targets (not legacy PORT-RISK ids)
    contract.failure_shutdown = default_shutdown(
        [supervisor, "RISK-1", "GOV-CHAIR", "SEC-HALT"]
    )
    contract.approval = strategy_approval()
    contract.execution = strategy_execution_perms()
    contract.self_improvement = default_improvement()
    contract.testing_deployment_status = DeploymentStatus.PAPER
    contract.extra = {
        "sizing_mode": agent.get("sizing") or "fixed_1_2_usd",
        "watchfloor_division": agent.get("division"),
        "thesis_required": bool(agent.get("thesis_required", True)),
        "contract_completeness": "stub_measurable_v1",
    }
    return contract


def contract_is_complete(contract: AgentOperatingContract) -> bool:
    if contract.role == AgentRole.STRATEGY and contract.execution.may_propose_trades:
        return bool(
            contract.setup_detection_rules
            and contract.entry_exit.entry_rules
            and contract.entry_exit.stop_loss_rule
            and contract.entry_exit.invalidation_rules
            and contract.position_sizing.max_pct_nav > 0
        )
    # Support / control seats: mandate triggers + escalation path required
    return bool(
        contract.setup_detection_rules
        and contract.entry_exit.invalidation_rules
        and contract.failure_shutdown.escalate_to
        and contract.agent_id
    )


def _role_for_support(agent: dict[str, Any]) -> AgentRole:
    aid = agent["id"]
    kind = agent.get("kind") or ""
    division = agent.get("division") or ""
    if aid == "EXEC-1":
        return AgentRole.EXECUTION
    if aid in {"FIT-1", "COST-1", "STAT-1", "BACK-1"}:
        return AgentRole.VALIDATION
    if aid in {"ATTR-1", "CALIB-1"}:
        return AgentRole.ATTRIBUTION
    if aid in {"SYNTH-1", "LIFE-1", "ARCH-1", "AUDIT-1"}:
        return AgentRole.LEARNING_CONTROL
    if aid in {"COMP-1", "RECON-1"}:
        return AgentRole.MONITORING
    if aid in {"RISK-1", "CAP-1", "CORR-Q", "CIT-RISK", "CIT-ALLOC"}:
        return AgentRole.PORTFOLIO_RISK
    if aid in {"MKT-1", "ALT-1", "DQ-1"}:
        return AgentRole.MARKET_INFORMATION
    if aid in {"ML-ARCH", "ML-VIT", "ML-SEQ", "ML-CLS", "ML-PAT", "TOOL-1", "UI-1"}:
        return AgentRole.AI_INFRASTRUCTURE
    if aid in {"MEM-1"} or kind == "mind":
        return AgentRole.SYSTEMS_INTELLIGENCE
    if kind in {"gov", "sec", "control"} or division in {"ctrl", "sec"}:
        return AgentRole.GOVERNANCE
    if kind in {"intel", "disc"} or division in {"intel", "pred"}:
        return AgentRole.FUNDAMENTAL_RESEARCH
    if kind == "lab" or division == "lab":
        return AgentRole.QUANTITATIVE_RESEARCH
    if kind == "quant" or division == "quant":
        return AgentRole.QUANTITATIVE_RESEARCH
    if kind == "fund" or division == "funds":
        return AgentRole.CAPITAL_STEWARDSHIP
    if aid.startswith("BRK-"):
        return AgentRole.CAPITAL_STEWARDSHIP
    return AgentRole.SYSTEMS_INTELLIGENCE


def contract_for_support(agent: dict[str, Any]) -> AgentOperatingContract:
    """Operating contract for non-proposing Watchfloor seats."""
    supervisor = agent.get("supervisor_id") or "GOV-CHAIR"
    role = _role_for_support(agent)
    aid = agent["id"]
    mandate = SetupDetectionRule(
        rule_id=f"{aid}-MANDATE-01",
        description="Seat activates on matching org events within mandate",
        expression=(
            f"event.recipient_ids CONTAINS '{aid}' OR event.tags OVERLAP mandate_tags"
        ),
        required_inputs=["event_type", "payload", "correlation_id"],
        lookback=1,
    )
    may_execute = aid == "EXEC-1"
    return AgentOperatingContract(
        agent_name=agent.get("nick") or aid,
        agent_id=aid,
        department=agent.get("department") or agent.get("division") or "support",
        supervisory_agent_id=supervisor,
        role=role,
        strategy=(agent.get("role") or aid)[:240],
        economic_rationale=(
            f"Watchfloor {role.value} seat — does not propose trades; "
            f"owns mandate outputs and escalations only."
        ),
        assets_permitted=["N/A"],
        markets_permitted=["US_EQUITIES"],
        holding_period_days_min=0,
        holding_period_days_max=0,
        trading_frequency="event_driven",
        valid_regimes=list(MarketRegime),
        invalid_regimes=[],
        required_data_inputs=["org_events", "mem_1_namespace"],
        data_sources={"org_events": "MEM-1", "halt": "SEC-HALT"},
        indicators_features_models=[],
        setup_detection_rules=[mandate],
        entry_exit=EntryExitRules(
            entry_rules=[f"activate on mandate event for {aid}"],
            exit_rules=["release after output written to MEM-1"],
            stop_loss_rule="escalate_on_repeated_failure",
            invalidation_rules=["mandate_breach", "halt", "permission_denied"],
            time_stop_days=None,
        ),
        position_sizing=PositionSizingRules(
            method="fixed_fraction",
            max_pct_nav=0.0001,
            min_pct_nav=0.0,
            max_concurrent_positions=0,
            max_sector_pct=0.0,
            notes="Non-trading seat — no capital authority",
        ),
        information_received_from=["MEM-1", supervisor],
        outputs_sent_to=["MEM-1", supervisor, "GOV-CHAIR"],
        approval=ApprovalRequirements(
            requires_independent_validation=False,
            requires_portfolio_evaluation=False,
            requires_risk_approval=False,
            requires_capital_stewardship_review=False,
            requires_governance_check=True,
            can_self_approve=False,
            can_self_execute=False,
            can_set_own_capital_limits=False,
            can_evaluate_own_performance=False,
        ),
        execution=ExecutionPermissions(
            may_propose_trades=False,
            may_place_orders=may_execute,
            may_cancel_orders=may_execute,
            may_force_close=False,
            paper_only=True,
            live_enabled=False,
            max_notional_usd=0.0 if not may_execute else 1_000_000.0,
        ),
        monitoring_after_entry=["mandate_sla", "escalation_latency"],
        memory_retained=["outputs", "escalations", "rejects"],
        performance_measurements=["sla_hit_rate", "escalation_quality", "false_alarm_rate"],
        failure_shutdown=default_shutdown([supervisor, "GOV-CHAIR", "SEC-HALT"]),
        testing_deployment_status=DeploymentStatus.PAPER,
        strategy_version="watchfloor-0.4.0",
        self_improvement=default_improvement(),
        owns_stages=[],
        authority_actions=[],
        extra={
            "watchfloor_division": agent.get("division"),
            "watchfloor_kind": agent.get("kind"),
            "contract_completeness": "stub_measurable_v1",
            "non_trading": True,
        },
    )


def contract_for_agent(agent: dict[str, Any]) -> AgentOperatingContract:
    if agent.get("may_propose_trades"):
        return contract_for_proposer(agent)
    return contract_for_support(agent)


@lru_cache(maxsize=1)
def all_proposer_contracts() -> dict[str, AgentOperatingContract]:
    out: dict[str, AgentOperatingContract] = {}
    for agent in proposers():
        out[agent["id"]] = contract_for_proposer(agent)
    return out


@lru_cache(maxsize=1)
def all_agent_contracts() -> dict[str, AgentOperatingContract]:
    out: dict[str, AgentOperatingContract] = {}
    for agent in all_agents():
        out[agent["id"]] = contract_for_agent(agent)
    return out


def incomplete_proposer_ids() -> list[str]:
    return [
        aid
        for aid, contract in all_proposer_contracts().items()
        if not contract_is_complete(contract)
    ]


def incomplete_agent_ids() -> list[str]:
    return [
        aid
        for aid, contract in all_agent_contracts().items()
        if not contract_is_complete(contract)
    ]


def contracts_as_dicts(*, proposers_only: bool = False) -> dict[str, Any]:
    src = all_proposer_contracts() if proposers_only else all_agent_contracts()
    return {aid: c.model_dump(mode="json") for aid, c in src.items()}


def clear_contract_cache() -> None:
    all_proposer_contracts.cache_clear()
    all_agent_contracts.cache_clear()
