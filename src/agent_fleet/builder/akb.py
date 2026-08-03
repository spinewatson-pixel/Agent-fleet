"""Architecture Knowledge Base consultation (Level 2).

AKB is updated only after reviewed, evidence-backed outcomes — never
directly from an unverified recommendation or simulation alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ASSET_TYPES = [
    "Engineering Principles",
    "Design Patterns",
    "Anti-Patterns",
    "Decision Trees",
    "Checklists",
    "Evaluation Rubrics",
    "Trade-off Matrices",
    "Failure Modes",
    "Recovery Strategies",
    "Implementation Templates",
    "Simulation Scenarios",
    "Validation Tests",
    "Metrics",
    "Case Studies",
    "References",
]

PHASES = [
    (1, "AI_Organization_Patterns"),
    (2, "Capability_Engineering"),
    (3, "Memory_Systems"),
    (4, "Communication_Coordination"),
    (5, "Architecture_Engineering"),
    (6, "Digital_Twins_Simulation"),
    (7, "Decision_Science"),
    (8, "Governance_Safety"),
    (9, "Reliability_Observability"),
    (10, "Economics_Optimization"),
    (11, "Knowledge_Engineering"),
    (12, "Architecture_Pattern_Library"),
    (13, "Intent_Reconstruction"),
    (14, "Gap_Analysis_Methodologies"),
    (15, "Architecture_Synthesis"),
    (16, "Implementation_Planning"),
    (17, "Continuous_Improvement"),
    (18, "Metrics_Evaluation"),
    (19, "Learning_from_Experience"),
    (20, "Organizational_Evolution"),
    (21, "Scientific_Discovery_Systems"),
    (22, "Financial_Trading_Systems"),
    (23, "Software_Engineering_Organizations"),
    (24, "Robotics_Physical_Systems"),
    (25, "Healthcare_Clinical_Organizations"),
    (26, "Cybersecurity_Organizations"),
    (27, "Manufacturing_Industrial"),
    (28, "Research_Innovation_Management"),
    (29, "Human_AI_Collaboration"),
    (30, "Future_AI_Architectures"),
]


@dataclass
class KnowledgeObject:
    knowledge_id: str
    phase: int
    asset_type: str
    title: str
    summary: str
    applicability: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    confidence: float = 0.6
    evidence: list[str] = field(default_factory=list)
    version: str = "0.1.0"
    owner: str = "AKB-STEWARD"
    status: str = "draft"  # draft | published | deprecated | retired

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "phase": self.phase,
            "asset_type": self.asset_type,
            "title": self.title,
            "summary": self.summary,
            "applicability": self.applicability,
            "counterexamples": self.counterexamples,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "version": self.version,
            "owner": self.owner,
            "status": self.status,
        }


def akb_root() -> Path:
    return Path(__file__).resolve().parents[3] / "AKB"


def seed_patterns() -> list[KnowledgeObject]:
    """MVP seed patterns consulted during synthesis (not auto-promoted)."""
    return [
        KnowledgeObject(
            knowledge_id="AKB-P01-SEP-DUTY",
            phase=1,
            asset_type="Design Patterns",
            title="Propose ≠ Approve ≠ Execute",
            summary=(
                "Trading organizations must separate proposal, approval, and execution "
                "into distinct workers with veto paths."
            ),
            applicability=["trading", "high_risk_automation"],
            counterexamples=["single-agent self-trading bots without governance"],
            confidence=0.95,
            evidence=["Watchfloor hard_rules", "institutional SoD"],
            status="published",
        ),
        KnowledgeObject(
            knowledge_id="AKB-P01-HITL-MODEB",
            phase=1,
            asset_type="Design Patterns",
            title="Human-in-the-loop Mode B thresholds",
            summary=(
                "Auto-approve below thresholds; hard escalate above. Human retains veto."
            ),
            applicability=["enterprise_ai_orgs", "trading_labs"],
            confidence=0.9,
            evidence=["HUMAN-1 Mode B"],
            status="published",
        ),
        KnowledgeObject(
            knowledge_id="AKB-P08-PAPER-FIRST",
            phase=8,
            asset_type="Engineering Principles",
            title="Paper-first with live hard-disabled",
            summary="Do not enable live execution until rollback, recon, and audit prove readiness.",
            applicability=["financial_trading"],
            confidence=0.95,
            evidence=["live_execution_enabled=false"],
            status="published",
        ),
        KnowledgeObject(
            knowledge_id="AKB-P08-CHANGE-CR",
            phase=8,
            asset_type="Implementation Templates",
            title="Change request lifecycle",
            summary="draft → review → approved → scheduled → deployed → verified → closed/rollback",
            applicability=["all_orgs"],
            confidence=0.85,
            evidence=["Builder blueprint §4D"],
            status="published",
        ),
        KnowledgeObject(
            knowledge_id="AKB-P22-EVIDENCE-PROMOTE",
            phase=22,
            asset_type="Design Patterns",
            title="Evidence package before quant promotion",
            summary=(
                "Quant/Rentec-style seats require OOS evidence packages before promotion; "
                "builders never self-certify."
            ),
            applicability=["financial_trading", "quant_research"],
            confidence=0.88,
            evidence=["EVID-1", "FIT-1", "RT-FORGE-1 never self-certifies"],
            status="published",
        ),
        KnowledgeObject(
            knowledge_id="AKB-P06-STATIC-FIRST",
            phase=6,
            asset_type="Simulation Scenarios",
            title="Static analysis before behavioral simulation",
            summary="Run contract/orphan/cycle/policy checks before expensive twin scenarios.",
            applicability=["all_orgs"],
            confidence=0.8,
            evidence=["Builder MVP recommendation"],
            status="published",
        ),
        KnowledgeObject(
            knowledge_id="AKB-P01-NO-BEST-TOPOLOGY",
            phase=1,
            asset_type="Anti-Patterns",
            title="Universal best topology myth",
            summary="No topology is universally best; select by intent, cost, failure modes.",
            applicability=["all_orgs"],
            confidence=0.9,
            evidence=["Builder blueprint Phase 1"],
            status="published",
        ),
    ]


def consult(objective: str = "governance_and_reliability") -> list[KnowledgeObject]:
    patterns = seed_patterns()
    if objective in {"governance_and_reliability", "governance", "safety"}:
        return [p for p in patterns if p.phase in {1, 8, 9, 22} or "Governance" in p.title]
    if objective in {"cost", "economics"}:
        return [p for p in patterns if p.phase in {1, 10, 22}]
    return patterns


def refuse_unverified_akb_write(source: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "reason": (
            "AKB updates require reviewed organizational outcomes with evidence, "
            "applicability bounds, version, and steward approval — not unverified "
            f"simulation/recommendation alone (source={source})."
        ),
    }
