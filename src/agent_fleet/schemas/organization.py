"""Canonical Organization Model for the Builder control plane.

Static design + runtime behavior. Every entity carries stable IDs,
ownership, timestamps, and evidence links — not free-form prose alone.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceKind(str, Enum):
    OBSERVED = "observed_fact"
    ASSERTION = "stakeholder_assertion"
    INFERENCE = "inference"
    SIMULATION = "simulation_output"
    RECOMMENDATION = "recommendation"


class ChangeStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    DEPLOYED = "deployed"
    VERIFIED = "verified"
    CLOSED = "closed"
    ROLLED_BACK = "rolled_back"


class EvidenceRef(BaseModel):
    evidence_id: str
    kind: EvidenceKind
    source: str
    collected_at: datetime = Field(default_factory=_now)
    integrity: str = "unverified"
    relevance: float = Field(ge=0.0, le=1.0, default=0.7)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    lineage: list[str] = Field(default_factory=list)
    summary: str = ""


class Organization(BaseModel):
    org_id: str
    name: str
    mission: str = ""
    scope: str = ""
    owners: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)
    lifecycle: str = "discovered"
    criticality: str = "high"
    environment: str = "paper"
    version: str = "0.1.0"
    substrate: str = "custom_python"
    evidence_ids: list[str] = Field(default_factory=list)
    unresolved_intent_fields: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=_now)


class Capability(BaseModel):
    capability_id: str
    org_id: str
    purpose: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    slos: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    evaluation_criteria: list[str] = Field(default_factory=list)
    present: bool = True
    maturity: str = "unknown"  # missing | nascent | working | strong
    evidence_ids: list[str] = Field(default_factory=list)
    version: str = "0.1.0"


class WorkerKind(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    WORKFLOW = "workflow"
    SERVICE = "service"
    TOOL = "tool"


class Worker(BaseModel):
    worker_id: str
    org_id: str
    kind: WorkerKind
    name: str
    responsibilities: list[str] = Field(default_factory=list)
    authority: list[str] = Field(default_factory=list)
    model_runtime: str = ""
    permissions: list[str] = Field(default_factory=list)
    cost_profile: str = ""
    division: str = ""
    department: str = ""
    supervisor_id: str = ""
    may_propose_trades: bool = False
    may_place_orders: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
    version: str = "0.1.0"


class Interface(BaseModel):
    interface_id: str
    org_id: str
    kind: str  # api | queue | file | ui | event | contract
    name: str
    schema_ref: str = ""
    rate_limits: str = ""
    authentication: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    version: str = "0.1.0"


class KnowledgeAsset(BaseModel):
    knowledge_id: str
    org_id: str
    source: str
    ownership: str = ""
    freshness: str = "unknown"
    retention: str = ""
    access_policy: str = ""
    provenance: str = ""
    retrieval_behavior: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    version: str = "0.1.0"


class GovernancePolicy(BaseModel):
    policy_id: str
    org_id: str
    name: str
    approval_rules: list[str] = Field(default_factory=list)
    risk_class: str = "standard"
    data_rules: list[str] = Field(default_factory=list)
    budgets: list[str] = Field(default_factory=list)
    escalation: list[str] = Field(default_factory=list)
    audit_requirements: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    version: str = "0.1.0"


class TopologyEdge(BaseModel):
    edge_id: str
    org_id: str
    source_id: str
    target_id: str
    kind: str  # orchestration | delegation | feedback | veto | data
    notes: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class MetricDef(BaseModel):
    metric_id: str
    org_id: str
    name: str
    definition: str
    baseline: str = ""
    target: str = ""
    sampling_method: str = ""
    dimensions: list[str] = Field(default_factory=list)  # quality|latency|cost|safety|reliability
    evidence_ids: list[str] = Field(default_factory=list)
    version: str = "0.1.0"


class ChangeSet(BaseModel):
    change_id: str
    org_id: str
    title: str
    proposal: str
    affected_entities: list[str] = Field(default_factory=list)
    predicted_impact: str = ""
    status: ChangeStatus = ChangeStatus.DRAFT
    approvals: list[str] = Field(default_factory=list)
    rollout: str = ""
    rollback: str = ""
    actual_outcome: str = ""
    risk_tier: str = "R1"
    evidence_ids: list[str] = Field(default_factory=list)
    version: str = "0.1.0"
    created_at: datetime = Field(default_factory=_now)


class OrganizationSnapshot(BaseModel):
    """Full canonical snapshot used by Builder engines."""

    organization: Organization
    capabilities: list[Capability] = Field(default_factory=list)
    workers: list[Worker] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    knowledge: list[KnowledgeAsset] = Field(default_factory=list)
    policies: list[GovernancePolicy] = Field(default_factory=list)
    topology: list[TopologyEdge] = Field(default_factory=list)
    metrics: list[MetricDef] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    change_sets: list[ChangeSet] = Field(default_factory=list)
    preserve_list: list[str] = Field(default_factory=list)
    single_points_of_failure: list[str] = Field(default_factory=list)
    adapter_id: str = ""
    fidelity_notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
