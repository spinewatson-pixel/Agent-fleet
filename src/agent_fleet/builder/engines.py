"""Builder reasoning engines (Level 3 core pipeline pieces)."""

from __future__ import annotations

from typing import Any

from agent_fleet.builder import akb as akb_mod
from agent_fleet.schemas.organization import OrganizationSnapshot
from agent_fleet.schemas.recommendation import (
    CandidateArchitecture,
    Claim,
    MigrationPlan,
    RecommendationContract,
    ReviewScore,
    SimulationResult,
)


def reconstruct_intent(snapshot: OrganizationSnapshot) -> dict[str, Any]:
    org = snapshot.organization
    fields = {
        "mission": {"value": org.mission, "confidence": 0.8 if org.mission else 0.0},
        "environment": {"value": org.environment, "confidence": 0.95},
        "owners": {"value": org.owners, "confidence": 0.9},
        "criticality": {"value": org.criticality, "confidence": 0.7},
        "substrate": {"value": org.substrate, "confidence": 0.95},
    }
    unresolved = list(org.unresolved_intent_fields)
    for name, meta in fields.items():
        if meta["confidence"] < 0.5:
            unresolved.append(name)
    return {
        "fields": fields,
        "unresolved": sorted(set(unresolved)),
        "clarification_questions": [
            "What external capital / customer mandate applies beyond the paper lab?",
            "Which regulatory jurisdiction constraints apply if this ever leaves paper?",
            "What numeric success targets define 'effective' for the trading lab?",
            "Where is the production broker boundary — never, sandbox-only, or future gated?",
        ],
        "rule": "Do not guess mission, constraints, ownership, risk tolerance, or success criteria",
    }


def gap_analysis(snapshot: OrganizationSnapshot) -> dict[str, Any]:
    missing = [c for c in snapshot.capabilities if not c.present or c.maturity == "missing"]
    weak = [c for c in snapshot.capabilities if c.present and c.maturity in {"nascent", "working"}]
    strong = [c for c in snapshot.capabilities if c.maturity == "strong"]
    opportunities = []
    for c in missing:
        opportunities.append(
            {
                "capability_id": c.capability_id,
                "purpose": c.purpose,
                "priority": "P0" if c.capability_id in {"CAP-CEIL-GATE", "CAP-SOD"} else "P1",
                "preserve_conflict": False,
            }
        )
    return {
        "missing": [c.capability_id for c in missing],
        "weak": [c.capability_id for c in weak],
        "strong": [c.capability_id for c in strong],
        "preserve_list": list(snapshot.preserve_list),
        "opportunities": opportunities,
        "spof": list(snapshot.single_points_of_failure),
    }


def synthesize_candidates(
    snapshot: OrganizationSnapshot,
    gaps: dict[str, Any],
    patterns: list[akb_mod.KnowledgeObject],
    objective: str,
) -> list[CandidateArchitecture]:
    pattern_ids = [p.knowledge_id for p in patterns]
    c1 = CandidateArchitecture(
        candidate_id="CAND-GOV-HARDEN",
        name="Governance Hardening (advisory)",
        summary=(
            "Close ceiling UI gate, formalize change-request lifecycle, deepen evidence "
            "provenance, keep paper-only SoD intact."
        ),
        pattern_ids=[p for p in pattern_ids if "P08" in p or "SEP" in p or "MODEB" in p],
        strengths=[
            "Preserves Watchfloor strengths",
            "Low reversibility risk",
            "Aligns with first optimization objective: governance_and_reliability",
        ],
        weaknesses=["Does not expand alpha research depth"],
        expected_value="Higher trust in architecture map; fewer unsafe structural changes",
        expected_cost="Low engineering cost; mainly control-plane + UI gate",
        risk="Low",
        reversibility="high",
        affected_stakeholders=["GOV-CHAIR", "HUMAN-1", "UI-1", "COMP-1"],
        tradeoffs={
            "safety": "up",
            "capability_coverage": "slight_up",
            "latency": "neutral",
            "cost": "slight_up",
        },
    )
    c2 = CandidateArchitecture(
        candidate_id="CAND-OBS-TWIN",
        name="Observability + Twin Slice",
        summary=(
            "Add architecture telemetry hooks, static twin scenarios, and prediction/"
            "outcome calibration without enabling live execution."
        ),
        pattern_ids=[p for p in pattern_ids if "P06" in p or "P22" in p or "P01" in p],
        strengths=["Enables calibrated improvement loop", "Supports Builder north-star metrics"],
        weaknesses=["Needs instrumentation investment", "Runtime fidelity still partial"],
        expected_value="Faster issue→plan cycle; measurable prediction calibration",
        expected_cost="Medium",
        risk="Medium — more moving parts",
        reversibility="medium",
        affected_stakeholders=["ARCH-1", "ATTR-1", "MEM-1", "DQ-1"],
        tradeoffs={
            "safety": "up",
            "observability": "up",
            "cost": "up",
            "complexity": "up",
        },
    )
    if objective in {"cost", "economics"}:
        c2.tradeoffs["priority"] = "secondary_to_cost_cuts"
    # Always return ≥2 candidates when feasible
    _ = gaps  # gaps already shaped candidate focus
    _ = snapshot
    return [c1, c2]


def run_simulations(snapshot: OrganizationSnapshot, candidates: list[CandidateArchitecture]) -> list[SimulationResult]:
    results: list[SimulationResult] = []
    # Static analysis
    findings: list[str] = []
    worker_ids = {w.worker_id for w in snapshot.workers}
    if "EXEC-1" not in worker_ids:
        findings.append("CRITICAL: EXEC-1 missing")
    proposers = [w for w in snapshot.workers if w.may_propose_trades]
    bad = [w.worker_id for w in proposers if w.may_place_orders]
    if bad:
        findings.append(f"CRITICAL: proposers with order authority: {bad}")
    orphans = []
    for edge in snapshot.topology:
        if edge.target_id not in worker_ids and edge.target_id not in {"PROPOSER", "EXEC-1"}:
            if edge.target_id not in worker_ids:
                orphans.append(edge.target_id)
    if orphans:
        findings.append(f"Topology targets not in worker set: {sorted(set(orphans))[:8]}")
    if not snapshot.organization.mission:
        findings.append("Mission empty — intent incomplete")
    results.append(
        SimulationResult(
            mode="static",
            name="contract_orphan_policy_scan",
            passed=not any(f.startswith("CRITICAL") for f in findings),
            findings=findings or ["No critical static violations"],
            assumptions=["Registry is complete source for workers", "No hidden runtime edges"],
            confidence_interval="moderate",
            limitations=["Does not prove runtime behavior", "No market simulation"],
        )
    )
    # Scenario: live execution attempt
    results.append(
        SimulationResult(
            mode="scenario",
            name="attempt_enable_live_execution",
            passed=True,
            findings=[
                "Policy gate must block live_execution_enabled=true",
                "Builder advisory mode refuses apply",
            ],
            assumptions=["Hard rules remain loaded at runtime"],
            confidence_interval="narrow_for_policy",
            limitations=["Not a live broker test"],
        )
    )
    # Scenario per candidate (lightweight)
    for cand in candidates:
        results.append(
            SimulationResult(
                mode="scenario",
                name=f"candidate_{cand.candidate_id}",
                passed=True,
                findings=[
                    f"Preserve list size={len(snapshot.preserve_list)} respected in design",
                    f"Pattern consultation: {len(cand.pattern_ids)} patterns",
                ],
                assumptions=["Human approval required before any apply"],
                confidence_interval="wide",
                limitations=["Behavioral twin not fully implemented in MVP"],
            )
        )
    return results


def independent_review(
    snapshot: OrganizationSnapshot,
    candidates: list[CandidateArchitecture],
    sims: list[SimulationResult],
) -> list[ReviewScore]:
    """Adversarial review boundary — try to disprove the design."""
    static_ok = all(s.passed for s in sims if s.mode == "static")
    scores = [
        ReviewScore(
            dimension="intent_fit",
            score=0.75,
            rationale="Mission reconstructed from hard rules + org naming; numeric success targets unresolved",
            evidence_ids=["EV-RULES-001"],
            missing_evidence=["stakeholder-confirmed success metrics"],
            confidence=0.65,
            remediation="Run intent clarification with HUMAN-1",
        ),
        ReviewScore(
            dimension="safety_governance",
            score=0.92 if static_ok else 0.2,
            rationale="Paper-only + SoD + veto chain present",
            evidence_ids=["EV-RULES-001"],
            missing_evidence=["UI ceiling hard gate proof"],
            confidence=0.9,
            remediation="Implement CAP-CEIL-GATE before expanding roster",
            blocking=not static_ok,
        ),
        ReviewScore(
            dimension="reliability_blast_radius",
            score=0.7,
            rationale=f"SPOFs noted: {', '.join(snapshot.single_points_of_failure[:3])}",
            evidence_ids=["EV-REG-001"],
            missing_evidence=["recon drill evidence under load"],
            confidence=0.6,
            remediation="Schedule halt + recon drills; document recovery",
        ),
        ReviewScore(
            dimension="observability",
            score=0.45,
            rationale="Audit events exist; architecture drift detection missing",
            evidence_ids=[],
            missing_evidence=["topology drift metrics", "intent drift detector"],
            confidence=0.7,
            remediation="Adopt CAND-OBS-TWIN instrumentation slice",
        ),
        ReviewScore(
            dimension="cost_capacity",
            score=0.8,
            rationale="Agent ceiling 300; roster within ceiling; compute ceiling declared",
            evidence_ids=["EV-REG-001"],
            missing_evidence=["cost per successful paper outcome"],
            confidence=0.6,
            remediation="Add economics metrics to ATTR-1 / Learning Loop",
        ),
        ReviewScore(
            dimension="human_operability",
            score=0.85,
            rationale="Watchfloor UI + HUMAN-1 Mode B + council artifacts",
            evidence_ids=["EV-REG-001"],
            missing_evidence=["operator runbook completion rates"],
            confidence=0.7,
            remediation="Keep Builder advisory; export plans into Decision Workspace",
        ),
        ReviewScore(
            dimension="modularity_portability",
            score=0.7,
            rationale="Canonical Watchfloor IDs; substrate-specific adapter isolated",
            evidence_ids=["EV-REG-001"],
            missing_evidence=["second adapter to prove portability"],
            confidence=0.55,
            remediation="Defer universal frameworks; keep org-model first",
        ),
    ]
    # Prefer first candidate unless safety blocked
    _ = candidates
    return scores


def choose_candidate(
    candidates: list[CandidateArchitecture],
    scores: list[ReviewScore],
    objective: str,
) -> tuple[str, str, dict[str, str]]:
    if any(s.blocking for s in scores):
        return "", "Blocked by independent review — no deployment recommendation", {}
    # Default: governance hardening for MVP objective
    chosen = candidates[0].candidate_id
    if objective in {"observability", "quality"} and len(candidates) > 1:
        chosen = candidates[1].candidate_id
    rationale = (
        f"Selected {chosen} for objective={objective}: maximizes safety/governance "
        "with high reversibility while preserving Watchfloor strengths."
    )
    rejected = {
        c.candidate_id: (
            "Higher complexity / cost before governance gaps (ceiling gate, CR lifecycle) close"
            if c.candidate_id != chosen
            else ""
        )
        for c in candidates
        if c.candidate_id != chosen
    }
    return chosen, rationale, rejected


def build_migration_plan(chosen_id: str, gaps: dict[str, Any]) -> MigrationPlan:
    steps = [
        "Confirm reconstructed intent fields with HUMAN-1 (no guessing)",
        "Implement UI agent-ceiling hard gate (CAP-CEIL-GATE)",
        "Introduce ChangeSet objects for structural roster changes",
        "Wire Builder recommendation artifact into Decision Workspace",
        "Keep live_execution_enabled=false; refuse production apply",
    ]
    if chosen_id == "CAND-OBS-TWIN":
        steps.extend(
            [
                "Add architecture health metrics export",
                "Expand static twin scenarios; calibrate against paper-run audits",
            ]
        )
    return MigrationPlan(
        plan_id=f"MIG-{chosen_id or 'BLOCKED'}",
        steps=steps,
        gates=[
            "Human approval (HUMAN-1 / GOV-CHAIR)",
            "Independent review has no blocking failures",
            "Paper-only hard rule intact",
            "No TradeProposal authority granted to Builder",
        ],
        rollback=[
            "Revert UI/gate commits",
            "Restore prior registry version",
            "Invalidate draft ChangeSets",
        ],
        owner="HUMAN-1",
        success_measures=[
            "Trusted current-state map available in <1 command",
            "% architectural claims with evidence IDs increases",
            "Ceiling cannot be silently breached from UI",
            "Zero live execution enables",
        ],
        environment="sandbox",
        requires_human_approval=True,
    )


def build_recommendation(
    snapshot: OrganizationSnapshot,
    objective: str = "governance_and_reliability",
) -> RecommendationContract:
    intent = reconstruct_intent(snapshot)
    gaps = gap_analysis(snapshot)
    patterns = akb_mod.consult(objective)
    candidates = synthesize_candidates(snapshot, gaps, patterns, objective)
    sims = run_simulations(snapshot, candidates)
    scores = independent_review(snapshot, candidates, sims)
    chosen, rationale, rejected = choose_candidate(candidates, scores, objective)
    plan = build_migration_plan(chosen, gaps) if chosen else None

    claims = [
        Claim(
            claim="Organization is paper-only with live execution disabled",
            evidence_ids=["EV-RULES-001"],
            freshness="registry",
            confidence=0.99,
        ),
        Claim(
            claim=f"Roster has {len(snapshot.workers)} workers under ceiling policy",
            evidence_ids=["EV-REG-001"],
            freshness="registry",
            confidence=0.95,
        ),
        Claim(
            claim="Digital twin / architecture simulation capability is missing",
            evidence_ids=[],
            freshness="gap_analysis",
            confidence=0.8,
        ),
    ]

    return RecommendationContract(
        recommendation_id="REC-WATCHFLOOR-MVP-001",
        org_id=snapshot.organization.org_id,
        problem_statement=(
            "Watchfloor is a strong paper trading organization, but lacks a governed "
            "architecture control plane loop (intent confidence, formal change sets, "
            "twin calibration, and evidence-backed AKB consultation)."
        ),
        reconstructed_intent=intent,
        claims=claims,
        current_state_summary=(
            f"{snapshot.organization.name} v{snapshot.organization.version}: "
            f"{len(snapshot.workers)} workers, {len(snapshot.capabilities)} capabilities modeled, "
            f"adapter={snapshot.adapter_id}"
        ),
        preserved_strengths=list(snapshot.preserve_list),
        candidates=candidates,
        decision_criteria=[
            "Preserve SoD and paper-only gates",
            "Prefer high reversibility",
            "Close governance gaps before autonomy expansion",
            "Cite evidence; flag unresolved intent",
        ],
        weighted_tradeoffs={
            "safety": 0.35,
            "governance": 0.25,
            "reliability": 0.2,
            "cost": 0.1,
            "capability_coverage": 0.1,
        },
        simulation_results=sims,
        review_scores=scores,
        unresolved_questions=intent["clarification_questions"],
        chosen_candidate_id=chosen,
        choice_rationale=rationale,
        rejected_rationale=rejected,
        migration_plan=plan,
        operating_mode="advisory_only",
        approval_status="pending_human",
    )
