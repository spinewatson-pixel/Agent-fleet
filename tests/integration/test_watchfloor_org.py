"""Watchfloor registry and organization tests."""

from __future__ import annotations

import pytest

from agent_fleet.registry.watchfloor import (
    assert_separation_of_duties,
    hard_rules,
    load_watchfloor_registry,
    proposers,
)
from agent_fleet.schemas.enums import ApprovalStatus, Side
from agent_fleet.workflow.watchfloor_org import WatchfloorOrganization


def test_registry_loads_and_enforces_separation():
    reg = load_watchfloor_registry()
    assert reg["counts"]["total_agents"] >= 200
    assert reg["counts"]["executors"] == 1
    assert_separation_of_duties()
    assert hard_rules()["live_execution_enabled"] is False
    assert hard_rules()["paper_only"] is True


def test_proposers_cannot_execute():
    for agent in proposers():
        assert agent.get("can_self_approve") is False
        if agent["id"] != "EXEC-1":
            assert not agent.get("may_place_orders")


def test_watchfloor_paper_chain_fill():
    org = WatchfloorOrganization()
    result = org.ingest_market_event(symbol="AAPL", price=190.0, agent_id="AAPL-L")
    assert result["decision"]["status"] in {
        ApprovalStatus.APPROVED.value,
        ApprovalStatus.REDUCED.value,
    }
    assert result["decision"]["execution_authorized"] is True
    assert result["fill"] is not None
    assert result["fill"]["paper"] is True
    assert result["live_execution_enabled"] is False


def test_unknown_agent_cannot_propose():
    org = WatchfloorOrganization()
    with pytest.raises(PermissionError):
        org.propose_from_watchfloor_agent(
            "NOT-A-REAL-AGENT",
            symbol="AAPL",
            side=Side.BUY,
            price=100,
            thesis="should fail",
        )


def test_non_proposer_cannot_propose():
    org = WatchfloorOrganization()
    with pytest.raises(PermissionError):
        org.propose_from_watchfloor_agent(
            "GOV-CHAIR",
            symbol="AAPL",
            side=Side.BUY,
            price=100,
            thesis="council does not trade",
        )


def test_emergency_halt_blocks_new_trades():
    org = WatchfloorOrganization()
    org.emergency_halt(by_agent="SEC-HALT", reason="drill")
    result = org.propose_from_watchfloor_agent(
        "NVDA-L",
        symbol="NVDA",
        side=Side.BUY,
        price=100,
        thesis="should be rejected while halted",
        expected_edge_bps=50,
    )
    assert result["decision"]["status"] == ApprovalStatus.REJECTED.value
    assert result["fill"] is None
