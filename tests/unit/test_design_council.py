"""Institutional Design Council enhance-fleet tests."""

from __future__ import annotations

import json
from pathlib import Path

from agent_fleet.cli import main
from agent_fleet.council import InstitutionalDesignCouncil, plan_to_markdown
from agent_fleet.council.design_council import FindingKind, Priority


def test_council_has_nine_specialty_teams_plus_chief_decisions():
    council = InstitutionalDesignCouncil()
    assert len(council.teams) == 9
    assert {t.team_id for t in council.teams} == {
        "IDC-PALANTIR",
        "IDC-BLOOMBERG",
        "IDC-NVIDIA",
        "IDC-BLACKROCK",
        "IDC-CITADEL",
        "IDC-RENTECH",
        "IDC-GOLDMAN",
        "IDC-JPM",
        "IDC-BERKSHIRE",
    }
    veto_teams = {t.team_id for t in council.teams if t.has_veto}
    assert veto_teams == {"IDC-BLACKROCK", "IDC-JPM", "IDC-BERKSHIRE"}


def test_enhance_run_emits_prioritized_plan():
    plan = InstitutionalDesignCouncil().run()
    assert plan.organization
    assert plan.findings
    assert plan.decisions
    assert any(d.team_id == "IDC-CHIEF" for d in plan.decisions)
    assert "P0" in plan.tasks_by_priority
    assert plan.tasks_by_priority["P0"], "P0 tasks required before paper hardening"
    # Council designs/supervises — never emits trade proposals
    blob = json.dumps(plan.to_dict())
    assert "TradeProposal" not in blob or "IDC-* agents out of TradeProposal" in blob
    md = plan_to_markdown(plan)
    assert "Enhancement Plan" in md
    assert "Implementation tasks by priority" in md


def test_standing_live_execution_veto():
    from agent_fleet.council.design_council import Finding

    council = InstitutionalDesignCouncil()
    bad = Finding(
        team_id="IDC-CITADEL",
        team_name="Trading Operations",
        kind=FindingKind.IMPROVEMENT,
        title="Enable live brokerage",
        detail="Should enable live execution now",
        priority=Priority.P3,
        implementation_task="Set live_execution_enabled=true",
    )
    surviving, vetoes = council.apply_vetoes([bad])
    assert surviving[0].vetoed is True
    assert any(v.kind == FindingKind.VETO for v in vetoes)


def test_cli_enhance_writes_artifacts(tmp_path: Path):
    out = tmp_path / "council"
    rc = main(["enhance", "--out-dir", str(out)])
    assert rc == 0
    assert (out / "enhancement_plan.json").exists()
    assert (out / "enhancement_plan.md").exists()
    data = json.loads((out / "enhancement_plan.json").read_text(encoding="utf-8"))
    assert data["tasks_by_priority"]["P0"]
    assert data["agent_counts"]["total_agents"] >= 200
