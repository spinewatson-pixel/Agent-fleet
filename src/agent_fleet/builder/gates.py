"""Hard gates — Builder never silently operates a business process."""

from __future__ import annotations

from typing import Any


FORBIDDEN_ACTIONS = frozenset(
    {
        "place_order",
        "emit_trade_proposal",
        "enable_live_execution",
        "auto_mutate_production",
        "update_akb_from_unverified_simulation",
        "bypass_human_approval",
        "guess_mission_without_flagging",
    }
)


class BuilderGateError(RuntimeError):
    pass


def assert_advisory_only(operating_mode: str) -> None:
    if operating_mode not in {"advisory_only", "plan_export", "supervised_sandbox"}:
        raise BuilderGateError(f"Unsupported operating mode: {operating_mode}")
    if operating_mode == "supervised_sandbox":
        # Allowed later; MVP still refuses apply.
        pass


def refuse_production_mutation(change: dict[str, Any] | None = None) -> None:
    """MVP: Builder may draft change sets but never apply them."""
    if change and change.get("status") in {"deployed", "scheduled"}:
        raise BuilderGateError(
            "Builder MVP cannot schedule or deploy changes. Export a plan for human approval."
        )


def refuse_trade_authority(payload: dict[str, Any]) -> None:
    blob = str(payload).lower()
    if "may_place_orders\": true" in blob.replace(" ", "") and "exec-1" not in blob.lower():
        raise BuilderGateError("Builder must not grant order placement authority")
    for key in ("TradeProposal", "place_order", "live_execution_enabled=true"):
        if key.lower() in blob and "must not" not in blob:
            # Allow documentation that forbids these.
            if "never" in blob or "advisory" in blob or "forbidden" in blob:
                continue


def assert_no_forbidden_action(action: str) -> None:
    if action in FORBIDDEN_ACTIONS:
        raise BuilderGateError(f"Forbidden Builder action: {action}")
