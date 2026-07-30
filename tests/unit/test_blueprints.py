"""Eight-layer agent blueprint coverage."""

from __future__ import annotations

from pathlib import Path

from agent_fleet.agents.blueprints import (
    all_blueprints,
    blueprint_for,
    incomplete_blueprint_ids,
)
from agent_fleet.cli import main
from agent_fleet.registry.watchfloor import load_watchfloor_registry


REQUIRED_LAYERS = [
    "identity",
    "goal",
    "responsibilities",
    "functions",
    "tools",
    "capabilities",
    "memory",
    "knowledge_base",
]


def test_every_agent_has_complete_eight_layer_blueprint():
    load_watchfloor_registry.cache_clear()
    from agent_fleet.agents.blueprints import clear_blueprint_cache

    clear_blueprint_cache()
    reg = load_watchfloor_registry()
    bps = all_blueprints()
    assert len(bps) == reg["counts"]["total_agents"]
    assert incomplete_blueprint_ids() == []
    for aid, bp in bps.items():
        d = bp.to_dict()
        for layer in REQUIRED_LAYERS:
            assert d[layer], f"{aid} missing {layer}"
        assert bp.paper_only is True
        assert bp.live_enabled is False
        if bp.may_propose_trades:
            assert bp.may_place_orders is False


def test_new_expert_seats_present():
    ids = {a["id"] for a in load_watchfloor_registry()["agents"]}
    for need in ["RECON-1", "ACT-1", "ADV-1", "EVID-1", "FORE-2", "SIG-1"]:
        assert need in ids
        bp = blueprint_for(next(a for a in load_watchfloor_registry()["agents"] if a["id"] == need))
        assert bp.identity and bp.goal


def test_cli_blueprints_export(tmp_path: Path):
    out = tmp_path / "bp.json"
    assert main(["blueprints", "--out", str(out)]) == 0
    assert out.exists()
