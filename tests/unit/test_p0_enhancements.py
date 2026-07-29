"""P0/P1 enhancement coverage: contracts, ceiling, sizing, regime."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_fleet.agents.watchfloor_contracts import (
    all_proposer_contracts,
    contract_is_complete,
    incomplete_proposer_ids,
)
from agent_fleet.cli import main
from agent_fleet.core.events import EventStore
from agent_fleet.core.regime import RegimeService
from agent_fleet.registry.watchfloor import hard_rules, load_watchfloor_registry
from agent_fleet.schemas.enums import ApprovalStatus, MarketRegime, Side
from agent_fleet.workflow.watchfloor_org import WatchfloorOrganization


def test_all_proposers_have_complete_contracts():
    contracts = all_proposer_contracts()
    assert len(contracts) >= 100
    assert incomplete_proposer_ids() == []
    for aid, contract in contracts.items():
        assert contract_is_complete(contract), aid
        assert contract.execution.may_place_orders is False
        assert contract.approval.can_self_approve is False


def test_agent_ceiling_covers_roster():
    reg = load_watchfloor_registry()
    assert reg["hard_rules"]["agent_ceiling"] >= reg["counts"]["total_agents"]
    assert hard_rules()["live_execution_enabled"] is False
    assert any(a["id"] == "RECON-1" for a in reg["agents"])


def test_fixed_dollar_cohort_sizing_on_fill(tmp_path: Path):
    org = WatchfloorOrganization(event_store=EventStore(path=tmp_path / "events.jsonl"))
    result = org.ingest_market_event(symbol="AAPL", price=190.0, agent_id="AAPL-L")
    assert result["decision"]["status"] in {
        ApprovalStatus.APPROVED.value,
        ApprovalStatus.REDUCED.value,
    }
    assert result["sizing_usd"] == pytest.approx(1.5, rel=1e-6)
    assert result["fill"] is not None
    assert 0 < result["fill"]["filled_qty"] < 1
    assert (tmp_path / "events.jsonl").exists()


def test_quant_requires_evidence_package():
    org = WatchfloorOrganization(event_store=EventStore())
    rt = next(
        a
        for a in org.registry["agents"]
        if a["id"].startswith("RT-") and a.get("may_propose_trades")
    )
    rejected = org.propose_from_watchfloor_agent(
        rt["id"],
        symbol="SPY",
        side=Side.BUY,
        price=500,
        thesis="quant path",
        expected_edge_bps=40,
        evidence_package_id=None,
    )
    assert rejected["decision"]["status"] == ApprovalStatus.REJECTED.value
    assert "evidence_package_present" in rejected["decision"]["reasons"]

    ok = org.propose_from_watchfloor_agent(
        rt["id"],
        symbol="SPY",
        side=Side.BUY,
        price=500,
        thesis="quant path",
        expected_edge_bps=40,
        evidence_package_id="EVID-TEST-1",
    )
    assert ok["decision"]["status"] in {
        ApprovalStatus.APPROVED.value,
        ApprovalStatus.REDUCED.value,
    }


def test_regime_service_blocks_invalid_regime():
    svc = RegimeService(current=MarketRegime.RISK_OFF)
    assert svc.admits([MarketRegime.TRENDING_BULL], [MarketRegime.RISK_OFF]) is False
    assert svc.admits([MarketRegime.RISK_OFF], []) is True


def test_brk_trader_requires_moat_metadata():
    org = WatchfloorOrganization(event_store=EventStore())
    brk = next(
        a
        for a in org.registry["agents"]
        if a["id"].startswith("BRK-TRD") and a.get("may_propose_trades")
    )
    bad = org.propose_from_watchfloor_agent(
        brk["id"],
        symbol="BRK.B",
        side=Side.BUY,
        price=400,
        thesis="quality compounder without scores",
        expected_edge_bps=50,
    )
    assert bad["decision"]["status"] == ApprovalStatus.REJECTED.value

    good = org.propose_from_watchfloor_agent(
        brk["id"],
        symbol="BRK.B",
        side=Side.BUY,
        price=400,
        thesis="quality compounder with scores",
        expected_edge_bps=50,
        metadata={"moat_score": 0.8, "margin_of_safety": 0.25},
    )
    assert good["decision"]["status"] in {
        ApprovalStatus.APPROVED.value,
        ApprovalStatus.REDUCED.value,
    }


def test_export_watchfloor_contracts(tmp_path: Path):
    out = tmp_path / "wf.json"
    rc = main(["export-contracts", "--watchfloor", "--out", str(out)])
    assert rc == 0
    assert out.exists()
