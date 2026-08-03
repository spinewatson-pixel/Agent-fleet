import type {
  CanonicalOrganization,
  IntentProfile,
} from "../schemas/entities.js";
import type { Confidence } from "../schemas/common.js";

export type GapCategory =
  | "capability_coverage"
  | "topology"
  | "contract"
  | "governance"
  | "observability"
  | "recovery";

export type GapSeverity = "low" | "medium" | "high" | "critical";

export interface GapFinding {
  id: string;
  category: GapCategory;
  severity: GapSeverity;
  title: string;
  rationale: string;
  evidenceIds: string[];
  knowledgeIds: string[];
  evidenceConfidence: Confidence;
  entityIds: string[];
}

export interface GapAnalysisResult {
  objective: "reliability_capability_coverage";
  findings: GapFinding[];
  preserveList: string[];
  summary: string;
}

export function analyzeGaps(
  org: CanonicalOrganization,
  intent?: IntentProfile,
): GapAnalysisResult {
  const findings: GapFinding[] = [];
  const evidenceIds = org.evidence.map((e) => e.id);

  // Capability coverage
  for (const cap of org.capabilities) {
    if (cap.evaluationCriteria.length === 0) {
      findings.push({
        id: `gap_eval_${cap.id}`,
        category: "capability_coverage",
        severity: "high",
        title: `Missing evaluation criteria for ${cap.name}`,
        rationale:
          "Reliability/capability coverage cannot be verified without evaluation criteria.",
        evidenceIds: cap.evidenceIds.length ? cap.evidenceIds : evidenceIds.slice(0, 1),
        knowledgeIds: ["ko_delegation_contract_integrity"],
        evidenceConfidence: "medium",
        entityIds: [cap.id],
      });
    }
    if (cap.ownerIds.length === 0) {
      findings.push({
        id: `gap_owner_${cap.id}`,
        category: "governance",
        severity: "medium",
        title: `Absent owner for capability ${cap.name}`,
        rationale: "Unowned capabilities block operability, escalation, and human governance.",
        evidenceIds: cap.evidenceIds,
        knowledgeIds: ["ko_readonly_before_mutation"],
        evidenceConfidence: "high",
        entityIds: [cap.id],
      });
    }
    if (cap.failureModes.length === 0) {
      findings.push({
        id: `gap_fail_${cap.id}`,
        category: "recovery",
        severity: "medium",
        title: `No failure modes declared for ${cap.name}`,
        rationale: "Recovery planning requires explicit failure modes.",
        evidenceIds: cap.evidenceIds,
        knowledgeIds: ["ko_simulation_bounded"],
        evidenceConfidence: "medium",
        entityIds: [cap.id],
      });
    }
  }

  // Contracts
  for (const iface of org.interfaces) {
    if (!iface.contractSchema) {
      findings.push({
        id: `gap_contract_${iface.id}`,
        category: "contract",
        severity: "critical",
        title: `Broken/missing contract on ${iface.name}`,
        rationale:
          "Delegation boundaries without contracts lose context integrity (seeded defect).",
        evidenceIds: iface.evidenceIds.length ? iface.evidenceIds : evidenceIds.slice(0, 1),
        knowledgeIds: ["ko_delegation_contract_integrity"],
        evidenceConfidence: "high",
        entityIds: [iface.id],
      });
    }
  }

  // Governance / approval gate
  const highRisk =
    org.organization.criticality === "high" ||
    org.organization.criticality === "critical";
  const hasGate = org.governancePolicies.some((p) => p.requiresHumanApprovalGate);
  if (highRisk && !hasGate) {
    findings.push({
      id: "gap_approval_gate",
      category: "governance",
      severity: "critical",
      title: "Absent human approval gate",
      rationale:
        "High/critical workflows require an explicit human approval gate; none declared.",
      evidenceIds: evidenceIds.filter((id) =>
        org.evidence.find((e) => e.id === id && e.sourceType === "trace"),
      ),
      knowledgeIds: ["ko_critical_governance_blocks", "ko_readonly_before_mutation"],
      evidenceConfidence: "high",
      entityIds: org.governancePolicies.map((p) => p.id),
    });
  }

  // Topology: orphans and cycles
  for (const topo of org.topologies) {
    const connected = new Set<string>();
    for (const e of topo.edges) {
      connected.add(e.from);
      connected.add(e.to);
    }
    for (const n of topo.nodes) {
      if (!connected.has(n.id) && n.kind === "worker") {
        findings.push({
          id: `gap_orphan_${n.id}`,
          category: "topology",
          severity: "medium",
          title: `Orphaned worker node ${n.label}`,
          rationale: "Node has no communication/delegation edges in topology.",
          evidenceIds: topo.evidenceIds,
          knowledgeIds: ["ko_topology_no_universal_best"],
          evidenceConfidence: "high",
          entityIds: [n.refId],
        });
      }
    }

    if (hasCycle(topo.edges.map((e) => [e.from, e.to] as [string, string]))) {
      findings.push({
        id: `gap_cycle_${topo.id}`,
        category: "topology",
        severity: "high",
        title: `Circular dependency in topology ${topo.name}`,
        rationale: "Circular dependencies risk unbounded retry/ack loops.",
        evidenceIds: topo.evidenceIds,
        knowledgeIds: ["ko_topology_no_universal_best"],
        evidenceConfidence: "medium",
        entityIds: [topo.id],
      });
    }
  }

  // Observability: latency miss vs target
  for (const m of org.metrics) {
    if (
      m.dimension === "latency" &&
      typeof m.baseline === "number" &&
      typeof m.target === "number" &&
      m.baseline > m.target
    ) {
      findings.push({
        id: `gap_metric_${m.id}`,
        category: "observability",
        severity: "medium",
        title: `Latency baseline exceeds target (${m.name})`,
        rationale: "Observed latency baseline is worse than stated target.",
        evidenceIds: m.evidenceIds,
        knowledgeIds: ["ko_simulation_bounded"],
        evidenceConfidence: "medium",
        entityIds: [m.id],
      });
    }
  }

  // Intent unknowns become gaps against objective (not invented answers)
  if (!intent?.mission) {
    findings.push({
      id: "gap_intent_mission",
      category: "capability_coverage",
      severity: "high",
      title: "Mission unknown",
      rationale: "Cannot optimize reliability/capability coverage without stated mission.",
      evidenceIds: [],
      knowledgeIds: ["ko_readonly_before_mutation"],
      evidenceConfidence: "unknown",
      entityIds: [org.organization.id],
    });
  }

  const preserveList =
    intent?.preserveList?.length
      ? intent.preserveList
      : [
          "Existing retrieval tool read-only authority",
          "Claims intake summarization capability purpose",
          "Internal mTLS intake API auth reference",
        ];

  const critical = findings.filter((f) => f.severity === "critical").length;
  const high = findings.filter((f) => f.severity === "high").length;

  return {
    objective: "reliability_capability_coverage",
    findings: findings.sort(severitySort),
    preserveList,
    summary: `Found ${findings.length} gaps (${critical} critical, ${high} high) against reliability/capability coverage. Preserve list retained.`,
  };
}

function severitySort(a: GapFinding, b: GapFinding): number {
  const order: Record<GapSeverity, number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
  };
  return order[a.severity] - order[b.severity];
}

function hasCycle(edges: [string, string][]): boolean {
  const graph = new Map<string, string[]>();
  for (const [from, to] of edges) {
    if (!graph.has(from)) graph.set(from, []);
    graph.get(from)!.push(to);
  }
  const visiting = new Set<string>();
  const visited = new Set<string>();

  function dfs(node: string): boolean {
    if (visiting.has(node)) return true;
    if (visited.has(node)) return false;
    visiting.add(node);
    for (const next of graph.get(node) ?? []) {
      if (dfs(next)) return true;
    }
    visiting.delete(node);
    visited.add(node);
    return false;
  }

  for (const node of graph.keys()) {
    if (dfs(node)) return true;
  }
  return false;
}
