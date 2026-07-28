"""Integration: full operating chain paper trade."""

from __future__ import annotations

from agent_fleet.schemas.enums import ApprovalStatus
from agent_fleet.workflow.pipeline import Organization


def test_paper_chain_produces_fill_for_momentum():
    org = Organization()
    result = org.ingest_market_event(
        symbol="AAPL",
        price=190.0,
        conviction=0.8,
        strategy_hint="STRAT-MOM-001",
    )
    assert result["fills"] >= 1
    assert result["positions"]
    assert result["audit_events"] > 0
    statuses = [d.get("status") for d in result["decisions"]]
    assert ApprovalStatus.APPROVED.value in statuses or ApprovalStatus.REDUCED.value in statuses


def test_low_edge_vetoed_by_capital_stewardship():
    org = Organization()
    # Directly craft a path with low edge via strategy propose + manual chain pieces
    from agent_fleet.agents.strategy import StrategyAgent
    from agent_fleet.schemas.enums import MarketRegime, Side

    strat = StrategyAgent("STRAT-MR-001")
    proposal = strat.propose(
        symbol="XYZ",
        side=Side.BUY,
        features={
            "close": 50,
            "ATR_14": 1,
            "force_setup": "MR-SETUP-01",
            "expected_edge_bps": 5,
            "confidence": 0.5,
            "suggested_size_pct_nav": 1.0,
        },
        current_regime=MarketRegime.RANGE_BOUND,
    )
    assert proposal is not None
    steward = org.agents["CAP-STEW-001"].review(
        proposal,
        __import__("agent_fleet.schemas.messages", fromlist=["RiskVerdict"]).RiskVerdict(
            proposal_id=proposal.proposal_id,
            risk_agent_id="PORT-RISK-001",
            action=__import__("agent_fleet.schemas.enums", fromlist=["ActionType"]).ActionType.APPROVE,
            approved_size_pct_nav=1.0,
            reasons=["ok"],
        ),
    )
    assert steward.veto is True


def test_strategy_send_permission_blocks_approval_messages():
    org = Organization()
    from agent_fleet.schemas.enums import MessageType, Stage
    from agent_fleet.schemas.messages import MessageEnvelope

    env = MessageEnvelope(
        message_type=MessageType.APPROVAL_DECISION,
        stage=Stage.RISK_APPROVAL,
        sender_id="STRAT-MOM-001",
        recipient_ids=["EXEC-OMS-001"],
        payload={},
    )
    try:
        org.bus.publish(env)
        assert False, "expected PermissionError"
    except PermissionError:
        pass


def test_live_org_init_blocked():
    try:
        Organization(live_execution_enabled=True)
        assert False, "expected PermissionError"
    except PermissionError:
        pass
