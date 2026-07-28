"""Acceptance tests — Phase 0 gates."""

from __future__ import annotations

import pytest

from agent_fleet import LIVE_EXECUTION_ENABLED
from agent_fleet.contracts.models import AgentRole, ApprovalAuthority
from agent_fleet.contracts.registry import build_all_contracts
from agent_fleet.execution.paper_broker import LiveExecutionDisabledError, PaperBroker
from agent_fleet.memory.learning import ChangeRequest, LearningStage
from agent_fleet.messaging.schemas import ExecutionOrderPayload, OrderType, Side, TradeProposalPayload
from agent_fleet.pipeline.organization import OperatingOrganization
from agent_fleet.risk.engine import RiskLimits


@pytest.mark.acceptance
def test_live_execution_flag_disabled():
    assert LIVE_EXECUTION_ENABLED is False


@pytest.mark.acceptance
def test_all_contracts_present_and_strategy_separation():
    contracts = build_all_contracts()
    required = {
        "SYS-ORCH-001",
        "DATA-MKT-001",
        "DATA-NEWS-001",
        "DATA-VAL-001",
        "RSH-FUND-001",
        "RSH-QUANT-001",
        "SIG-VAL-001",
        "PORT-ALLOC-001",
        "RISK-APPR-001",
        "CAP-STEW-001",
        "EXEC-PAPER-001",
        "EXEC-LIVE-001",
        "MON-LIVE-001",
        "MON-REGIME-001",
        "REV-ATTR-001",
        "LEARN-CTRL-001",
        "GOV-COMP-001",
        "AI-INFRA-001",
        "STRAT-MOM-001",
        "STRAT-MR-001",
        "STRAT-EVT-001",
        "STRAT-MACRO-001",
        "STRAT-QUAL-001",
        "STRAT-SECROT-001",
        "STRAT-PAIRS-001",
    }
    assert required.issubset(contracts.keys())
    for cid, c in contracts.items():
        if c.role == AgentRole.STRATEGY:
            assert ApprovalAuthority.APPROVE not in c.authorities
            assert ApprovalAuthority.PROPOSE in c.authorities
            assert c.execution_permissions == []
            assert c.outputs_sent_to[0].agent_id == "SIG-VAL-001"


@pytest.mark.acceptance
def test_paper_chain_approves_valid_momentum_proposal():
    org = OperatingOrganization(nav=100_000.0)
    org.set_price("AAPL", 190.0, sector="Technology")
    proposal = TradeProposalPayload(
        proposal_id="t-ok",
        strategy_agent_id="STRAT-MOM-001",
        strategy_version=org.contracts["STRAT-MOM-001"].strategy_version,
        symbol="AAPL",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        limit_price=190.0,
        stop_price=180.0,
        thesis="Trend continuation with volume-confirmed SMA cross",
        setup_rules_fired=["MOM-SETUP-1"],
        invalidation_rules=["MOM-INV-1"],
        expected_holding_period="swing_weeks",
        risk_per_trade_pct_nav_request=0.004,
    )
    result = org.run_proposal_chain(proposal)
    assert result.approved is True
    assert "strategy_proposal" in result.stages
    assert "independent_validation" in result.stages
    assert "portfolio_evaluation" in result.stages
    assert "risk_approval" in result.stages
    assert "capital_stewardship" in result.stages
    assert "execution" in result.stages
    assert result.fill is not None
    assert result.fill["paper"] is True


@pytest.mark.acceptance
def test_validator_rejects_missing_setup_rules():
    org = OperatingOrganization()
    org.set_price("AAPL", 190.0)
    proposal = TradeProposalPayload(
        proposal_id="t-bad",
        strategy_agent_id="STRAT-MOM-001",
        strategy_version="0.1.0",
        symbol="AAPL",
        side=Side.BUY,
        thesis="Enough thesis text here",
        setup_rules_fired=[],
        invalidation_rules=[],
        expected_holding_period="swing_weeks",
    )
    result = org.run_proposal_chain(proposal)
    assert result.approved is False
    assert result.rejected_by == "SIG-VAL-001"


@pytest.mark.acceptance
def test_steward_rejects_empty_thesis():
    org = OperatingOrganization()
    org.set_price("AAPL", 190.0, sector="Technology")
    proposal = TradeProposalPayload(
        proposal_id="t-stew",
        strategy_agent_id="STRAT-MOM-001",
        strategy_version="0.1.0",
        symbol="AAPL",
        side=Side.BUY,
        stop_price=180.0,
        thesis="short",  # < 10 chars after strip... "short" is 5
        setup_rules_fired=["MOM-SETUP-1"],
        invalidation_rules=[],
        expected_holding_period="swing_weeks",
    )
    result = org.run_proposal_chain(proposal)
    assert result.approved is False
    assert result.rejected_by == "CAP-STEW-001"


@pytest.mark.acceptance
def test_risk_rejects_when_drawdown_breached():
    org = OperatingOrganization(nav=100_000.0)
    org.state.drawdown_pct = 0.15
    org.set_price("AAPL", 190.0, sector="Technology")
    proposal = TradeProposalPayload(
        proposal_id="t-dd",
        strategy_agent_id="STRAT-MOM-001",
        strategy_version="0.1.0",
        symbol="AAPL",
        side=Side.BUY,
        stop_price=180.0,
        thesis="Trend continuation proposal with adequate thesis length",
        setup_rules_fired=["MOM-SETUP-1"],
        invalidation_rules=[],
        expected_holding_period="swing_weeks",
    )
    result = org.run_proposal_chain(proposal)
    assert result.approved is False
    assert result.rejected_by == "RISK-APPR-001"


@pytest.mark.acceptance
def test_live_broker_order_blocked():
    broker = PaperBroker()
    order = ExecutionOrderPayload(
        order_id="x",
        proposal_id="p",
        symbol="AAPL",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        quantity=1,
        authorized_by=["RISK-APPR-001"],
        paper=False,
    )
    with pytest.raises(LiveExecutionDisabledError):
        broker.execute(order, last_price=100.0)


@pytest.mark.acceptance
def test_learning_cannot_skip_stages():
    change = ChangeRequest(
        change_id="c1",
        target_agent_id="STRAT-MOM-001",
        hypothesis="ATR stop 2.0 better than 2.5",
        description="Tighten stop",
    )
    with pytest.raises(ValueError):
        change.advance(LearningStage.PAPER_TRADE)
    change.advance(LearningStage.STATISTICAL_TEST)
    change.advance(LearningStage.OUT_OF_SAMPLE)
    change.advance(LearningStage.PAPER_TRADE)
    change.advance(LearningStage.RISK_REVIEW, approver="RISK-APPR-001")
    change.advance(LearningStage.VERSIONED)
    change.production_rules_touched = True
    with pytest.raises(PermissionError):
        change.advance(LearningStage.APPROVED, approver="RISK-APPR-001")
        change.advance(LearningStage.GRADUAL_DEPLOY)


@pytest.mark.acceptance
def test_emergency_halt_blocks_new_approvals():
    org = OperatingOrganization()
    org.set_price("AAPL", 190.0, sector="Technology")
    org.emergency_halt("test halt")
    proposal = TradeProposalPayload(
        proposal_id="t-halt",
        strategy_agent_id="STRAT-MOM-001",
        strategy_version="0.1.0",
        symbol="AAPL",
        side=Side.BUY,
        stop_price=180.0,
        thesis="Trend continuation proposal with adequate thesis length",
        setup_rules_fired=["MOM-SETUP-1"],
        invalidation_rules=[],
        expected_holding_period="swing_weeks",
    )
    # After halt, publishing non-governance may fail; risk path also rejects halted state
    # Use direct evaluate via chain — bus may raise. Catch either halt or risk reject.
    try:
        result = org.run_proposal_chain(proposal)
        assert result.approved is False
        assert result.rejected_by == "RISK-APPR-001"
    except RuntimeError as e:
        assert "halted" in str(e).lower()


@pytest.mark.acceptance
def test_risk_reduces_or_rejects_huge_risk_request():
    org = OperatingOrganization(nav=100_000.0, risk_limits=RiskLimits(max_risk_per_trade_pct_nav=0.005))
    org.set_price("AAPL", 100.0, sector="Technology")
    # stop very tight -> large qty from risk formula, then position cap should bind
    proposal = TradeProposalPayload(
        proposal_id="t-size",
        strategy_agent_id="STRAT-MOM-001",
        strategy_version="0.1.0",
        symbol="AAPL",
        side=Side.BUY,
        stop_price=99.5,
        thesis="Trend continuation proposal with adequate thesis length",
        setup_rules_fired=["MOM-SETUP-1"],
        invalidation_rules=[],
        expected_holding_period="swing_weeks",
        risk_per_trade_pct_nav_request=0.05,  # above firm cap; engine must clip
    )
    result = org.run_proposal_chain(proposal)
    assert result.approved is True
    # notional should respect max position 5%
    notional = result.fill["quantity"] * result.fill["price"]
    assert notional <= 100_000 * 0.05 * 1.01  # slippage tolerance
