"""Unit tests for authority, memory, and contracts."""

from __future__ import annotations

import pytest

from agent_fleet.agents.strategy import StrategyAgent, STRATEGY_CONTRACTS
from agent_fleet.core.authority import AuthorityResolver
from agent_fleet.core.memory import MemoryStore
from agent_fleet.schemas.enums import ActionType, ApprovalStatus, Environment, MarketRegime, Side
from agent_fleet.schemas.messages import (
    PortfolioVerdict,
    RiskVerdict,
    TradeProposal,
    ValidationResult,
)
from agent_fleet.paper.broker import PaperBroker


def _proposal(**kwargs):
    base = dict(
        strategy_agent_id="STRAT-MOM-001",
        strategy_version="0.1.0",
        symbol="AAPL",
        side=Side.BUY,
        thesis="test",
        setup_rules_fired=["MOM-SETUP-01"],
        entry_price_target=100.0,
        stop_loss=95.0,
        invalidation_rules=["regime_break"],
        suggested_size_pct_nav=2.0,
        holding_period_days_min=5,
        holding_period_days_max=60,
        valid_regimes=[MarketRegime.TRENDING_BULL],
        current_regime=MarketRegime.TRENDING_BULL,
        required_data_inputs=["daily_ohlcv"],
        confidence=0.7,
        expected_edge_bps=40,
    )
    base.update(kwargs)
    return TradeProposal(**base)


def test_strategy_cannot_self_approve_or_execute():
    for aid in STRATEGY_CONTRACTS:
        agent = StrategyAgent(aid)
        c = agent.contract
        assert c.approval.can_self_approve is False
        assert c.approval.can_self_execute is False
        assert c.approval.can_set_own_capital_limits is False
        assert c.approval.can_evaluate_own_performance is False
        assert c.execution.may_place_orders is False
        assert c.execution.live_enabled is False


def test_authority_rejects_failed_validation():
    auth = AuthorityResolver()
    proposal = _proposal()
    validation = ValidationResult(
        proposal_id=proposal.proposal_id,
        validator_agent_id="VAL-IND-001",
        passed=False,
        checks={"has_setup_rules": False},
        defects=["has_setup_rules"],
    )
    portfolio = PortfolioVerdict(
        proposal_id=proposal.proposal_id,
        portfolio_agent_id="PORT-RISK-001",
        action=ActionType.APPROVE,
        approved_size_pct_nav=2.0,
        reasons=["ok"],
    )
    risk = RiskVerdict(
        proposal_id=proposal.proposal_id,
        risk_agent_id="PORT-RISK-001",
        action=ActionType.APPROVE,
        approved_size_pct_nav=2.0,
        reasons=["ok"],
    )
    decision = auth.resolve(proposal, validation, portfolio, risk)
    assert decision.status == ApprovalStatus.REJECTED
    assert decision.execution_authorized is False


def test_veto_blocks_execution():
    auth = AuthorityResolver()
    proposal = _proposal()
    validation = ValidationResult(
        proposal_id=proposal.proposal_id,
        validator_agent_id="VAL-IND-001",
        passed=True,
        checks={"ok": True},
    )
    portfolio = PortfolioVerdict(
        proposal_id=proposal.proposal_id,
        portfolio_agent_id="PORT-RISK-001",
        action=ActionType.APPROVE,
        approved_size_pct_nav=2.0,
        reasons=["ok"],
    )
    risk = RiskVerdict(
        proposal_id=proposal.proposal_id,
        risk_agent_id="PORT-RISK-001",
        action=ActionType.APPROVE,
        approved_size_pct_nav=2.0,
        reasons=["ok"],
    )
    steward = RiskVerdict(
        proposal_id=proposal.proposal_id,
        risk_agent_id="CAP-STEW-001",
        action=ActionType.REJECT,
        reasons=["activity_veto"],
        veto=True,
    )
    decision = auth.resolve(proposal, validation, portfolio, risk, steward)
    assert decision.status == ApprovalStatus.REJECTED
    assert decision.execution_authorized is False


def test_experimental_memory_cannot_write_production_rules():
    mem = MemoryStore()
    with pytest.raises(PermissionError):
        mem.learn(
            key="rule1",
            category="production_rule",
            data={"x": 1},
            agent_id="LEARN-001",
            environment=Environment.EXPERIMENTAL,
        )


def test_paper_broker_rejects_live_flag():
    with pytest.raises(PermissionError):
        PaperBroker(live_execution_enabled=True)


def test_all_strategy_contracts_have_measurable_setup_rules():
    for aid in STRATEGY_CONTRACTS:
        c = StrategyAgent(aid).contract
        assert c.setup_detection_rules
        for rule in c.setup_detection_rules:
            assert rule.expression
            assert rule.required_inputs
        assert c.entry_exit.stop_loss_rule
        assert c.entry_exit.invalidation_rules
