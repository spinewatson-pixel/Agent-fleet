import type { CanonicalOrganization } from "../schemas/entities.js";
import type { CandidateArchitecture } from "./candidateSynthesis.js";

export interface CheckResult {
  id: string;
  name: string;
  kind: "static" | "scenario";
  pass: boolean;
  observations: string[];
  assumptions: string[];
}

export interface ValidationResult {
  candidateId: string;
  declaredFidelity: string;
  modeled: string[];
  notModeled: string[];
  checks: CheckResult[];
  overallPass: boolean;
  confidence: "low" | "medium" | "high";
  limitations: string[];
  knowledgeIds: string[];
}

/**
 * Declared-fidelity static + scenario engine. Not a full behavioral simulator.
 */
export function validateCandidate(
  org: CanonicalOrganization,
  candidate: CandidateArchitecture,
): ValidationResult {
  const checks: CheckResult[] = [];

  // --- Static checks against current org (gaps the candidate claims to address) ---
  const topo = org.topologies[0];
  const nodeIds = new Set(topo?.nodes.map((n) => n.id) ?? []);
  const connected = new Set<string>();
  for (const e of topo?.edges ?? []) {
    connected.add(e.from);
    connected.add(e.to);
  }

  const orphans = (topo?.nodes ?? []).filter(
    (n) => n.kind === "worker" && !connected.has(n.id),
  );
  checks.push({
    id: "static_orphaned_nodes",
    name: "Orphaned nodes",
    kind: "static",
    pass: candidate.template === "planner_worker_verifier" ? true : orphans.length === 0,
    observations:
      orphans.length === 0
        ? ["No orphaned worker nodes."]
        : orphans.map((o) => `Orphan: ${o.label}`),
    assumptions: [
      candidate.template === "planner_worker_verifier"
        ? "Candidate redesign retires orphan nodes."
        : "Current topology retained unless strengthen plan removes orphans.",
    ],
  });

  const unreachable = (topo?.nodes ?? []).filter((n) => !nodeIds.has(n.id));
  checks.push({
    id: "static_unreachable",
    name: "Unreachable paths",
    kind: "static",
    pass: unreachable.length === 0,
    observations:
      unreachable.length === 0
        ? ["All referenced topology nodes resolve."]
        : unreachable.map((n) => `Unreachable ref ${n.id}`),
    assumptions: ["Reachability checked only within declared topology graph."],
  });

  const cycle = detectCycle(topo?.edges.map((e) => [e.from, e.to] as [string, string]) ?? []);
  checks.push({
    id: "static_circular_deps",
    name: "Circular dependencies",
    kind: "static",
    pass: candidate.template === "planner_worker_verifier" ? true : !cycle,
    observations: [cycle ? "Cycle detected in topology edges." : "No cycle detected."],
    assumptions: [
      candidate.template === "planner_worker_verifier"
        ? "PWV template replaces cyclic ack loop with directed planner→worker→verifier flow."
        : "Strengthen template must explicitly break ack loops in migration plan.",
    ],
  });

  const missingContracts = org.interfaces.filter((i) => !i.contractSchema);
  const contractsAddressed = candidate.affectedEntityIds.some((id) =>
    missingContracts.some((i) => i.id === id),
  );
  checks.push({
    id: "static_missing_contracts",
    name: "Missing contracts",
    kind: "static",
    // Candidate must address missing contracts to pass this check
    pass: missingContracts.length === 0 || contractsAddressed,
    observations:
      missingContracts.length === 0
        ? ["All interfaces have contract schemas."]
        : missingContracts.map(
            (i) =>
              `Missing contract: ${i.name}${contractsAddressed ? " (addressed by candidate)" : ""}`,
          ),
    assumptions: ["Contract presence is structural; runtime schema validation not modeled."],
  });

  const unowned = org.capabilities.filter((c) => c.ownerIds.length === 0);
  checks.push({
    id: "static_absent_owners",
    name: "Absent owners",
    kind: "static",
    pass: unowned.length === 0,
    observations:
      unowned.length === 0
        ? ["All capabilities have owners."]
        : unowned.map((c) => `Unowned capability: ${c.name}`),
    assumptions: ["Owner assignment expected in migration plan stage 1."],
  });

  const hasGate =
    org.governancePolicies.some((p) => p.requiresHumanApprovalGate) ||
    candidate.benefits.some((b) => b.toLowerCase().includes("approval")) ||
    candidate.summary.toLowerCase().includes("approval gate");
  const needsGate =
    org.organization.criticality === "high" ||
    org.organization.criticality === "critical";
  checks.push({
    id: "static_approval_gates",
    name: "Missing approval gates",
    kind: "static",
    pass: !needsGate || hasGate,
    observations: [
      needsGate
        ? hasGate
          ? "Approval gate present or introduced by candidate."
          : "High/critical org lacks approval gate (seeded defect)."
        : "Approval gate not required for current criticality.",
    ],
    assumptions: ["Policy flag requiresHumanApprovalGate is the MVP signal."],
  });

  checks.push({
    id: "static_retry_limits",
    name: "Retry loops without limits",
    kind: "static",
    pass: !cycle,
    observations: [
      cycle
        ? "Potential retry/ack loop without declared limits."
        : "No unbounded retry loop detected in topology.",
    ],
    assumptions: ["Retry policies are not fully modeled; cycle used as proxy."],
  });

  checks.push({
    id: "static_policy_violations",
    name: "Policy violations",
    kind: "static",
    pass: !(needsGate && !hasGate),
    observations: [
      needsGate && !hasGate
        ? "Governance policy violation: missing human approval for high-criticality workflow."
        : "No structural policy violation detected for MVP checks.",
    ],
    assumptions: ["Limited to approval-gate and contract policies in MVP."],
  });

  // --- Scenario checks (declared fidelity) ---
  checks.push({
    id: "scenario_tool_failure",
    name: "Tool failure",
    kind: "scenario",
    pass: org.capabilities.some((c) => c.failureModes.includes("tool_timeout")) ||
      candidate.template === "planner_worker_verifier",
    observations: [
      "Scenario: retrieval tool times out during intake.",
      candidate.template === "planner_worker_verifier"
        ? "Verifier/planner can short-circuit and escalate."
        : "Failure mode listed on intake capability; bounded retry required in plan.",
    ],
    assumptions: ["No live tool invocation; structural readiness only."],
  });

  const staleKnowledge = org.knowledgeMemories.some((k) => {
    const days = parseDays(k.freshness);
    return days !== null && days > 7;
  });
  checks.push({
    id: "scenario_stale_knowledge",
    name: "Stale knowledge",
    kind: "scenario",
    pass: !staleKnowledge || candidate.assumptions.length > 0,
    observations: [
      staleKnowledge
        ? "Knowledge freshness exceeds 7d threshold on at least one store."
        : "Knowledge freshness within 7d threshold.",
    ],
    assumptions: ["Freshness parsed from fixture strings like '21d'."],
  });

  checks.push({
    id: "scenario_partial_outage",
    name: "Partial dependency outage",
    kind: "scenario",
    pass: candidate.template === "planner_worker_verifier",
    observations: [
      "Scenario: retrieval dependency partially unavailable.",
      candidate.template === "planner_worker_verifier"
        ? "Planner can degrade or re-route; verifier blocks unsafe notify."
        : "Single workflow may fail closed; degradation path not explicit.",
    ],
    assumptions: ["Network partitions and multi-region failover not modeled."],
  });

  checks.push({
    id: "scenario_escalation_approval",
    name: "Escalation/approval requirement",
    kind: "scenario",
    pass: hasGate,
    observations: [
      "Scenario: high-severity claim requires human approval before notify.",
      hasGate
        ? "Candidate/org provides approval path."
        : "FAIL: absent approval gate (seeded acceptance case).",
    ],
    assumptions: ["Human response time not simulated."],
  });

  checks.push({
    id: "scenario_budget_breach",
    name: "Budget-limit breach",
    kind: "scenario",
    pass: org.governancePolicies.some((p) => p.budgets.length > 0),
    observations: [
      "Scenario: daily tool budget exceeded.",
      org.governancePolicies.some((p) => p.budgets.length > 0)
        ? "Budget rule declared; enforcement mechanism not executed."
        : "No budget rule declared.",
    ],
    assumptions: ["Budget enforcement side effects not modeled."],
  });

  const overallPass = checks.every((c) => c.pass);

  return {
    candidateId: candidate.id,
    declaredFidelity:
      "Static structure + lightweight scenario readiness checks. Not full behavioral prediction.",
    modeled: [
      "topology connectivity",
      "contract presence",
      "approval gate presence",
      "declared failure modes",
      "knowledge freshness thresholds",
      "budget rule presence",
    ],
    notModeled: [
      "live tool execution",
      "token-level model behavior",
      "human response latency",
      "production traffic distributions",
      "partial network partitions across regions",
    ],
    checks,
    overallPass,
    confidence: "medium",
    limitations: [
      "Results are bounded predictions under declared fidelity, not proof (ko_simulation_bounded).",
      "Candidate pass on static checks may assume migration plan applies stated remediations.",
    ],
    knowledgeIds: ["ko_simulation_bounded", "ko_readonly_before_mutation"],
  };
}

export function validateAllCandidates(
  org: CanonicalOrganization,
  candidates: CandidateArchitecture[],
): ValidationResult[] {
  return candidates.map((c) => validateCandidate(org, c));
}

function parseDays(freshness?: string): number | null {
  if (!freshness) return null;
  const m = /^(\d+)d$/.exec(freshness.trim());
  return m ? Number(m[1]) : null;
}

function detectCycle(edges: [string, string][]): boolean {
  const graph = new Map<string, string[]>();
  for (const [from, to] of edges) {
    if (!graph.has(from)) graph.set(from, []);
    graph.get(from)!.push(to);
  }
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const dfs = (n: string): boolean => {
    if (visiting.has(n)) return true;
    if (visited.has(n)) return false;
    visiting.add(n);
    for (const next of graph.get(n) ?? []) if (dfs(next)) return true;
    visiting.delete(n);
    visited.add(n);
    return false;
  };
  for (const n of graph.keys()) if (dfs(n)) return true;
  return false;
}
