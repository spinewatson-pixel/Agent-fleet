"""Builder control plane MVP tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_fleet.builder import BuilderControlPlane, decisions_as_dict
from agent_fleet.builder.akb import refuse_unverified_akb_write, seed_patterns
from agent_fleet.builder.gates import BuilderGateError, assert_no_forbidden_action, refuse_production_mutation
from agent_fleet.cli import main


def test_settled_decisions_are_advisory_watchfloor():
    d = decisions_as_dict()
    assert d["initial_operating_mode"] == "advisory_only"
    assert d["first_supported_substrate"] == "custom_python_watchfloor"
    assert d["first_adapter"] == "watchfloor_readonly"
    assert "human_governance_and_mission" in d["alignment_hierarchy"][0]


def test_gates_forbid_silent_ops():
    with pytest.raises(BuilderGateError):
        assert_no_forbidden_action("place_order")
    with pytest.raises(BuilderGateError):
        refuse_production_mutation({"status": "deployed"})
    assert refuse_unverified_akb_write("simulation")["accepted"] is False


def test_discover_normalizes_watchfloor_workers():
    plane = BuilderControlPlane()
    snap = plane.discover()
    assert snap.organization.org_id == "org-watchfloor-quant-lab"
    assert len(snap.workers) >= 200
    assert snap.adapter_id == "watchfloor_readonly"
    assert any(w.worker_id == "EXEC-1" and w.may_place_orders for w in snap.workers)
    proposers = [w for w in snap.workers if w.may_propose_trades]
    assert proposers
    assert all(not w.may_place_orders for w in proposers)
    assert snap.preserve_list
    assert snap.evidence


def test_recommend_emits_contract_with_two_candidates():
    rec = BuilderControlPlane().recommend()
    assert len(rec.candidates) >= 2
    assert rec.operating_mode == "advisory_only"
    assert rec.approval_status == "pending_human"
    assert rec.migration_plan is not None
    assert rec.migration_plan.requires_human_approval is True
    assert rec.simulation_results
    assert rec.review_scores
    assert "TradeProposal" not in json.dumps(rec.to_dict()) or "never" in json.dumps(rec.to_dict()).lower()
    blob = json.dumps(rec.to_dict()).lower()
    assert "advisory" in blob
    assert rec.chosen_candidate_id


def test_akb_seed_patterns_published():
    seeds = seed_patterns()
    ids = {s.knowledge_id for s in seeds}
    assert "AKB-P01-SEP-DUTY" in ids
    assert "AKB-P08-PAPER-FIRST" in ids
    assert all(s.status == "published" for s in seeds)


def test_builder_cli_run(tmp_path: Path):
    out = tmp_path / "builder_out"
    rc = main(["builder", "run", "--out-dir", str(out)])
    assert rc == 0
    assert (out / "recommendation.json").exists()
    assert (out / "recommendation.md").exists()
    assert (out / "organization_snapshot.json").exists()
    assert (out / "builder_registry.json").exists()
    reg = json.loads((out / "builder_registry.json").read_text())
    assert reg["operating_mode"] == "advisory_only"
    assert reg["approval_status"] == "pending_human"


def test_adapter_refuses_apply():
    plane = BuilderControlPlane()
    result = plane.adapter.apply({"change_id": "CHG-1"})
    assert result["status"] == "refused"
