"""Acceptance tests for Phase 0–1 paper organization gate."""

from __future__ import annotations

from agent_fleet.workflow.pipeline import Organization


REQUIRED_AGENTS = [
    "ARCH-CHIEF-001",
    "SYS-INTEL-001",
    "MKT-INFO-001",
    "AI-INFRA-001",
    "PORT-RISK-001",
    "TRADE-OPS-001",
    "QUANT-RES-001",
    "FUND-RES-001",
    "GOV-OPS-001",
    "CAP-STEW-001",
    "VAL-IND-001",
    "EXEC-OMS-001",
    "MON-LIVE-001",
    "ATTR-001",
    "LEARN-001",
    "STRAT-MOM-001",
    "STRAT-MR-001",
    "STRAT-EARN-001",
    "STRAT-MACRO-001",
    "STRAT-FACTOR-001",
    "STRAT-VALUE-001",
    "STRAT-VOL-001",
    "STRAT-SECTOR-001",
]


def test_phase1_agent_roster_complete():
    org = Organization()
    for aid in REQUIRED_AGENTS:
        assert aid in org.agents


def test_phase1_operating_chain_stages_owned():
    org = Organization()
    owned = set()
    for agent in org.agents.values():
        owned.update(agent.contract.owns_stages)
    required_stages = {
        "data_ingestion",
        "information_validation",
        "research",
        "signal_generation",
        "strategy_proposal",
        "independent_validation",
        "portfolio_evaluation",
        "risk_approval",
        "execution",
        "live_monitoring",
        "post_trade_attribution",
        "controlled_improvement",
    }
    assert required_stages.issubset(owned)


def test_phase1_authority_map_has_vetoes():
    org = Organization()
    amap = org.authority_map()
    assert "PORT-RISK-001" in amap["veto_agents"]
    assert "GOV-OPS-001" in amap["veto_agents"]
    assert "CAP-STEW-001" in amap["veto_agents"]
    assert amap["live_execution_enabled"] is False
