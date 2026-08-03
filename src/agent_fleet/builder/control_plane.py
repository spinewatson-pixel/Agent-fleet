"""Builder control plane — organizations-first architecture service.

Human Command Layer is cross-cutting: every stage surfaces evidence,
questions, diffs, and approval boundaries. AKB is consulted before
synthesis and never updated from unverified simulation alone.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_fleet.builder import akb as akb_mod
from agent_fleet.builder.adapters.watchfloor import WatchfloorReadOnlyAdapter
from agent_fleet.builder.decisions import decisions_as_dict
from agent_fleet.builder.engines import (
    build_recommendation,
    gap_analysis,
    reconstruct_intent,
)
from agent_fleet.builder.gates import (
    assert_advisory_only,
    refuse_production_mutation,
)
from agent_fleet.schemas.organization import OrganizationSnapshot
from agent_fleet.schemas.recommendation import RecommendationContract


class BuilderControlPlane:
    """Architecture control plane for AI organizations (MVP)."""

    def __init__(self, operating_mode: str = "advisory_only") -> None:
        assert_advisory_only(operating_mode)
        self.operating_mode = operating_mode
        self.adapter = WatchfloorReadOnlyAdapter()
        self.decisions = decisions_as_dict()

    def discover(self) -> OrganizationSnapshot:
        raw = self.adapter.discover()
        snapshot = self.adapter.normalize(raw)
        issues = self.adapter.validate(snapshot)
        snapshot.fidelity_notes = list(snapshot.fidelity_notes) + [
            f"validation:{i}" for i in issues
        ]
        return snapshot

    def analyze(self, snapshot: OrganizationSnapshot | None = None) -> dict[str, Any]:
        snap = snapshot or self.discover()
        patterns = [p.to_dict() for p in akb_mod.consult(self.decisions["first_optimization_objective"])]
        return {
            "organization": snap.organization.model_dump(mode="json"),
            "intent": reconstruct_intent(snap),
            "gaps": gap_analysis(snap),
            "akb_consultation": patterns,
            "akb_write_policy": akb_mod.refuse_unverified_akb_write("pre_outcome"),
            "preserve_list": snap.preserve_list,
            "fidelity_notes": snap.fidelity_notes,
            "evidence_count": len(snap.evidence),
            "worker_count": len(snap.workers),
            "human_command_layer": {
                "role": "cross_cutting",
                "surfaces": [
                    "state",
                    "evidence",
                    "questions",
                    "diffs",
                    "approvals",
                    "rollback_options",
                ],
            },
        }

    def recommend(
        self,
        snapshot: OrganizationSnapshot | None = None,
        objective: str | None = None,
    ) -> RecommendationContract:
        snap = snapshot or self.discover()
        obj = objective or self.decisions["first_optimization_objective"]
        rec = build_recommendation(snap, objective=obj)
        refuse_production_mutation({"status": "draft"})
        return rec

    def run(self, objective: str | None = None, out_dir: str | Path = "docs/builder") -> dict[str, Any]:
        """Full advisory loop → artifacts. Never deploys."""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        snapshot = self.discover()
        analysis = self.analyze(snapshot)
        recommendation = self.recommend(snapshot, objective=objective)

        snap_path = out / "organization_snapshot.json"
        analysis_path = out / "analysis.json"
        rec_path = out / "recommendation.json"
        md_path = out / "recommendation.md"
        decisions_path = out / "settled_decisions.json"

        snap_path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
        analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        rec_path.write_text(json.dumps(recommendation.to_dict(), indent=2), encoding="utf-8")
        md_path.write_text(recommendation_to_markdown(recommendation, analysis), encoding="utf-8")
        decisions_path.write_text(json.dumps(self.decisions, indent=2), encoding="utf-8")

        # Registry update of Builder view (not Watchfloor trading registry mutation)
        builder_reg = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "org_id": snapshot.organization.org_id,
            "version": snapshot.organization.version,
            "adapter_id": snapshot.adapter_id,
            "operating_mode": self.operating_mode,
            "recommendation_id": recommendation.recommendation_id,
            "approval_status": recommendation.approval_status,
            "chosen_candidate_id": recommendation.chosen_candidate_id,
            "blocked": recommendation.blocked(),
        }
        (out / "builder_registry.json").write_text(
            json.dumps(builder_reg, indent=2), encoding="utf-8"
        )

        return {
            "wrote": [
                str(snap_path),
                str(analysis_path),
                str(rec_path),
                str(md_path),
                str(decisions_path),
                str(out / "builder_registry.json"),
            ],
            "org_id": snapshot.organization.org_id,
            "workers": len(snapshot.workers),
            "evidence": len(snapshot.evidence),
            "chosen_candidate_id": recommendation.chosen_candidate_id,
            "approval_status": recommendation.approval_status,
            "operating_mode": self.operating_mode,
            "blocked": recommendation.blocked(),
            "apply": self.adapter.apply({"change_id": "none"}),
        }


def recommendation_to_markdown(rec: RecommendationContract, analysis: dict[str, Any]) -> str:
    lines = [
        f"# Builder Recommendation — `{rec.recommendation_id}`",
        "",
        f"**Org:** `{rec.org_id}`  ",
        f"**Mode:** `{rec.operating_mode}`  ",
        f"**Approval:** `{rec.approval_status}`  ",
        f"**Chosen:** `{rec.chosen_candidate_id or 'NONE (blocked)'}`",
        "",
        "## Positioning",
        "",
        "> A governed architecture control plane that turns AI systems into "
        "explainable, testable, evolvable organizations.",
        "",
        "## Problem",
        "",
        rec.problem_statement,
        "",
        "## Current state",
        "",
        rec.current_state_summary,
        "",
        "## Preserved strengths",
        "",
    ]
    for s in rec.preserved_strengths:
        lines.append(f"- {s}")
    lines += ["", "## Reconstructed intent (unresolved flagged)", ""]
    for q in rec.unresolved_questions:
        lines.append(f"- [ ] {q}")
    lines += ["", "## Candidates", ""]
    for c in rec.candidates:
        mark = "✓" if c.candidate_id == rec.chosen_candidate_id else "•"
        lines += [
            f"### {mark} `{c.candidate_id}` — {c.name}",
            "",
            c.summary,
            "",
            f"- Value: {c.expected_value}",
            f"- Cost: {c.expected_cost}",
            f"- Risk: {c.risk}",
            f"- Reversibility: {c.reversibility}",
            "",
        ]
    lines += ["## Choice rationale", "", rec.choice_rationale or "_blocked_", ""]
    if rec.rejected_rationale:
        lines += ["## Why alternatives were not selected", ""]
        for cid, why in rec.rejected_rationale.items():
            lines.append(f"- `{cid}`: {why}")
        lines.append("")
    lines += ["## Simulation results (predictions, not facts)", ""]
    for s in rec.simulation_results:
        status = "PASS" if s.passed else "FAIL"
        lines.append(f"- **{s.mode}/{s.name}** — {status}: {'; '.join(s.findings[:3])}")
    lines += ["", "## Independent review", ""]
    for sc in rec.review_scores:
        block = " **BLOCKING**" if sc.blocking else ""
        lines.append(
            f"- **{sc.dimension}** `{sc.score:.2f}` (conf {sc.confidence:.2f}){block}: {sc.rationale}"
        )
    if rec.migration_plan:
        p = rec.migration_plan
        lines += ["", "## Migration plan (export only — no auto deploy)", "", f"Owner: `{p.owner}`", ""]
        lines.append("### Steps")
        for i, step in enumerate(p.steps, 1):
            lines.append(f"{i}. {step}")
        lines += ["", "### Gates"]
        for g in p.gates:
            lines.append(f"- {g}")
        lines += ["", "### Rollback"]
        for r in p.rollback:
            lines.append(f"- {r}")
        lines += ["", "### Success measures"]
        for m in p.success_measures:
            lines.append(f"- {m}")
    gaps = analysis.get("gaps") or {}
    lines += ["", "## Gap summary", ""]
    lines.append(f"- Missing: {', '.join(gaps.get('missing') or []) or 'none'}")
    lines.append(f"- Strong: {', '.join(gaps.get('strong') or []) or 'none'}")
    lines += [
        "",
        "## AKB policy",
        "",
        "- Consulted before synthesis",
        "- Never updated from unverified simulation/recommendation alone",
        "",
        "---",
        "_Builder serves organizations. Learning is a byproduct of verified improvement._",
        "",
    ]
    return "\n".join(lines)
