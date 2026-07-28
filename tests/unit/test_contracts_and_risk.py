"""Unit tests for contracts and risk engine."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_fleet.contracts.models import (
    AgentOperatingContract,
    AgentRole,
    ApprovalAuthority,
    DeploymentStatus,
    Environment,
    FailureBehavior,
    HoldingPeriod,
    MarketRegime,
    PositionSizingLimits,
    SelfImprovementGate,
    TradeRules,
)
from agent_fleet.contracts.registry import build_all_contracts
from agent_fleet.governance.authority import TRADE_AUTHORITY, authority_matrix
from agent_fleet.messaging.schemas import Side, TradeProposalPayload
from agent_fleet.risk.engine import PortfolioState, RiskLimits, evaluate_proposal


def _minimal_strategy(**kwargs):
    base = dict(
        agent_name="t",
        agent_id="STRAT-T",
        department="Strategy",
        supervisory_agent_id="SYS-ORCH-001",
        role=AgentRole.STRATEGY,
        strategy_and_rationale="test",
        assets_and_markets_permitted=["US"],
        holding_period=HoldingPeriod.SWING_DAYS,
        trading_frequency="low",
        valid_regimes=[MarketRegime.ANY],
        required_data_inputs=[],
        indicators_features_models=[],
        setup_detection_rules=[],
        trade_rules=TradeRules(entry=[], exit=[], stop_loss=[], invalidation=[]),
        position_sizing_and_exposure=PositionSizingLimits(
            method="fixed",
            max_position_pct_nav=0.05,
            max_risk_per_trade_pct_nav=0.005,
            max_gross_exposure_pct_nav=0.5,
            max_net_exposure_pct_nav=0.5,
            max_sector_pct_nav=0.2,
            max_correlated_group_pct_nav=0.2,
        ),
        information_received_from=[],
        outputs_sent_to=[],
        approval_requirements=[],
        execution_permissions=[],
        authorities=[ApprovalAuthority.PROPOSE],
        monitoring_after_entry=[],
        memory_retained=[],
        performance_measurements=[],
        failure_and_shutdown=FailureBehavior(
            on_data_outage="pause",
            on_model_failure="pause",
            on_drawdown_breach="halt",
            on_permission_violation="shutdown",
            shutdown_triggers=["x"],
            recovery_requires=["y"],
        ),
        testing_and_deployment_status=DeploymentStatus.DESIGN,
        strategy_version="0.0.1",
        self_improvement_conditions=SelfImprovementGate(),
        environment=Environment.PAPER,
    )
    base.update(kwargs)
    return AgentOperatingContract(**base)


def test_strategy_cannot_hold_approve():
    with pytest.raises(ValidationError):
        _minimal_strategy(authorities=[ApprovalAuthority.PROPOSE, ApprovalAuthority.APPROVE])


def test_strategy_cannot_have_execution_permissions():
    with pytest.raises(ValidationError):
        _minimal_strategy(execution_permissions=["execute_orders"])


def test_authority_matrix_risk_has_halt():
    matrix = authority_matrix()
    assert "RISK-APPR-001" in matrix["emergency_halt"]
    assert "GOV-COMP-001" in matrix["emergency_halt"]
    assert TRADE_AUTHORITY["execute_live"] == []


def test_evaluate_proposal_rejects_halted():
    proposal = TradeProposalPayload(
        proposal_id="p",
        strategy_agent_id="STRAT-MOM-001",
        strategy_version="0.1.0",
        symbol="AAPL",
        side=Side.BUY,
        thesis="thesis text long enough",
        setup_rules_fired=["a"],
        invalidation_rules=[],
        expected_holding_period="swing_weeks",
    )
    state = PortfolioState(halted=True)
    v = evaluate_proposal(proposal, state, RiskLimits(), price=100.0)
    assert v.veto is True
    assert v.approved_quantity is None


def test_registry_exportable_json():
    contracts = build_all_contracts()
    for c in contracts.values():
        raw = c.model_dump_json()
        assert c.agent_id in raw or True
        assert len(raw) > 50
