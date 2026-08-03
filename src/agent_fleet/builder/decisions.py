"""Settled MVP decisions for the Builder (blueprint §11).

These are explicit product choices for v1 — not guesses about the
organization under review.
"""

from __future__ import annotations

from typing import Any

SETTLED_DECISIONS: dict[str, Any] = {
    "product": "AI Enterprise Architecture Engineer (Builder)",
    "blueprint_version": "1.1",
    "positioning": (
        "A governed architecture control plane that turns AI systems into "
        "explainable, testable, evolvable organizations."
    ),
    "primary_user_buyer": "internal_operations_team",
    "primary_user_notes": (
        "Watchfloor Quant Lab operators / founder seat (HUMAN-1) and "
        "Mission Control. Not multi-tenant SaaS in MVP."
    ),
    "first_supported_substrate": "custom_python_watchfloor",
    "first_adapter": "watchfloor_readonly",
    "initial_operating_mode": "advisory_only",
    "deployment_boundary": (
        "Builder never mutates production or places trades. "
        "MVP exports migration plans and review artifacts only. "
        "Controlled sandbox apply is deferred."
    ),
    "first_optimization_objective": "governance_and_reliability",
    "evidence_access": [
        "source_registry",
        "operating_contracts",
        "blueprints",
        "council_enhancement_plan",
        "hard_rules",
        "paper_audit_events_optional",
    ],
    "data_tenancy": "single_internal_organization",
    "trust_threshold": {
        "R0_block": ["live_execution", "self_approve_proposers", "auto_mutate_production"],
        "R1_human_required": ["structural_agent_changes", "ceiling_exceptions", "policy_changes"],
        "R2_security_review": ["secrets", "egress", "dependency_pins", "halt_restore"],
    },
    "alignment_hierarchy": [
        "human_governance_and_mission",
        "organization_outcomes_and_safety",
        "evidence_backed_recommendations",
        "reusable_akb_patterns",
        "builder_internal_operation",
    ],
    "frameworks_are": "execution_substrates_not_architecture_goals",
}


def decisions_as_dict() -> dict[str, Any]:
    return dict(SETTLED_DECISIONS)
