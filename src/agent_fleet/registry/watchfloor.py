"""Load Watchfloor org registry — canonical agent source of truth."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _candidates() -> list[Path]:
    root = Path(__file__).resolve().parents[3]
    return [
        Path("config/watchfloor_registry.json"),
        root / "config" / "watchfloor_registry.json",
    ]


@lru_cache(maxsize=1)
def load_watchfloor_registry() -> dict[str, Any]:
    for path in _candidates():
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("config/watchfloor_registry.json not found")


def all_agents() -> list[dict[str, Any]]:
    return list(load_watchfloor_registry()["agents"])


def agent_by_id(agent_id: str) -> dict[str, Any] | None:
    for agent in all_agents():
        if agent["id"] == agent_id:
            return agent
    return None


def proposers() -> list[dict[str, Any]]:
    return [a for a in all_agents() if a.get("may_propose_trades")]


def veto_agents() -> list[str]:
    return list(load_watchfloor_registry()["veto_agents"])


def approval_chain() -> list[str]:
    return list(load_watchfloor_registry()["approval_chain"])


def hard_rules() -> dict[str, Any]:
    return dict(load_watchfloor_registry()["hard_rules"])


def institutional_council_map() -> dict[str, list[str]]:
    return dict(load_watchfloor_registry()["institutional_council_map"])


def assert_separation_of_duties() -> None:
    """Enforce Watchfloor + institutional non-negotiables."""
    rules = hard_rules()
    assert rules["paper_only"] is True
    assert rules["live_execution_enabled"] is False
    assert rules["strategies_cannot_self_approve"] is True
    assert rules["strategies_cannot_self_execute"] is True
    for agent in proposers():
        if agent.get("can_self_approve"):
            raise AssertionError(f"{agent['id']} illegally can_self_approve")
        if agent.get("may_place_orders") and not agent.get("execution_role"):
            raise AssertionError(f"{agent['id']} proposer cannot place orders")
    executors = [a for a in all_agents() if a.get("may_place_orders") or a.get("execution_role")]
    if len(executors) != 1 or executors[0]["id"] != "EXEC-1":
        raise AssertionError("Only EXEC-1 may place orders in paper org")
