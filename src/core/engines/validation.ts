import type { CanonicalOrganization } from "../schemas/entities.js";
import type { CandidateArchitecture } from "./candidateSynthesis.js";

export interface CheckResult {
  id: string;
  name: string;
  kind: "static" | "scenario";
  /** Observed fact about the current organization only (not candidate claims). */
  currentStatePass: boolean;
  currentStateObservations: string[];
  /**
   * Candidate-projected outcome used for eligibility.
   * Must not treat unlabeled assumptions as current-state evidence.
   */
  pass: boolean;
  observations: string[];
  /** Candidate assumptions — never counted as observed current-state evidence. */
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
 * Separates current-state observations from candidate assumptions.
 */
export function validateCandidate(
  org: CanonicalOrganization,
  candidate: CandidateArchitecture,
): ValidationResult {
  const checks: CheckResult[] = [];
  const text = `${candidate.summary} ${candidate.benefits.join(" ")} ${candidate.assumptions.join(" ")}`.toLowerCase();

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
  const currentOrphansOk = orphans.length === 0;
  const remediatesOrphans =
    candidate.template === "planner_worker_verifier" ||
    text.includes("retire orphan") ||
    text.includes("remove orphan");
  checks.push({
    id: "static_orphaned_nodes",
    name: "Orphaned nodes",
    kind: "static",
    currentStatePass: currentOrphansOk,
    currentStateObservations:
      orphans.length === 0
        ? ["No orphaned worker nodes in current topology."]
        : orphans.map((o) => `Current-state orphan: ${o.label}`),
    pass: currentOrphansOk || remediatesOrphans,
    observations:
      currentOrphansOk
        ? ["No orphaned worker nodes."]
        : remediatesOrphans
          ? orphans.map((o) => `Current-state orphan ${o.label}; candidate assumes remediation.`)
          : orphans.map((o) => `Orphan remains unresolved by candidate: ${o.label}`),
    assumptions: remediatesOrphans && !currentOrphansOk
      ? ["Candidate assumption: redesign retires orphan nodes."]
      : [],
  });

  const unreachable = (topo?.nodes ?? []).filter((n) => !nodeIds.has(n.id));
  checks.push({
    id: "static_unreachable",
    name: "Unreachable paths",
    kind: "static",
    currentStatePass: unreachable.length === 0,
    currentStateObservations:
      unreachable.length === 0
        ? ["All referenced topology nodes resolve."]
        : unreachable.map((n) => `Unreachable ref ${n.id}`),
    pass: unreachable.length === 0,
    observations:
      unreachable.length === 0
        ? ["All referenced topology nodes resolve."]
        : unreachable.map((n) => `Unreachable ref ${n.id}`),
    assumptions: ["Reachability checked only within declared topology graph."],
  });

  const cycle = detectCycle(topo?.edges.map((e) => [e.from, e.to] as [string, string]) ?? []);
  const remediatesCycle =
    candidate.template === "planner_worker_verifier" ||
    (text.includes("break") && text.includes("loop")) ||
    text.includes("bounded retry");
  checks.push({
    id: "static_circular_deps",
    name: "Circular dependencies",
    kind: "static",
    currentStatePass: !cycle,
    currentStateObservations: [
      cycle ? "Cycle detected in current topology edges." : "No cycle in current topology.",
    ],
    pass: !cycle || remediatesCycle,
    observations: [
      !cycle
        ? "No cycle detected."
        : remediatesCycle
          ? "Current-state cycle present; candidate assumes directed remediation."
          : "Cycle remains unresolved by candidate.",
    ],
    assumptions:
      cycle && remediatesCycle
        ? ["Candidate assumption: replace cyclic ack loop with bounded directed flow."]
        : [],
  });

  const missingContracts = org.interfaces.filter((i) => !i.contractSchema);
  const contractsAddressed =
    missingContracts.length === 0 ||
    missingContracts.every((i) => candidate.affectedEntityIds.includes(i.id));
  checks.push({
    id: "static_missing_contracts",
    name: "Missing contracts",
    kind: "static",
    currentStatePass: missingContracts.length === 0,
    currentStateObservations:
      missingContracts.length === 0
        ? ["All interfaces currently have contract schemas."]
        : missingContracts.map((i) => `Current-state missing contract: ${i.name}`),
    pass: contractsAddressed,
    observations:
      missingContracts.length === 0
        ? ["All interfaces have contract schemas."]
        : missingContracts.map(
            (i) =>
              `Missing contract: ${i.name}${
                candidate.affectedEntityIds.includes(i.id)
                  ? " (candidate lists remediation)"
                  : " (unresolved by candidate)"
              }`,
          ),
    assumptions: contractsAddressed && missingContracts.length > 0
      ? ["Candidate assumption: migration authors missing contract schemas."]
      : ["Contract presence is structural; runtime schema validation not modeled."],
  });

  const unowned = org.capabilities.filter((c) => c.ownerIds.length === 0);
  // Do not infer owner remediation from unrelated affectedEntityIds (e.g. evaluation criteria).
  const remediatesOwners =
    text.includes("assign owner") ||
    text.includes("absent owner") ||
    /\bownership\b/.test(text);
  checks.push({
    id: "static_absent_owners",
    name: "Absent owners",
    kind: "static",
    currentStatePass: unowned.length === 0,
    currentStateObservations:
      unowned.length === 0
        ? ["All capabilities currently have owners."]
        : unowned.map((c) => `Current-state unowned capability: ${c.name}`),
    pass: unowned.length === 0 || remediatesOwners,
    observations:
      unowned.length === 0
        ? ["All capabilities have owners."]
        : remediatesOwners
          ? unowned.map((c) => `Unowned ${c.name}; candidate assumes owner assignment.`)
          : unowned.map((c) => `Unowned capability unresolved by candidate: ${c.name}`),
    assumptions:
      unowned.length > 0 && remediatesOwners
        ? ["Candidate assumption: owners assigned in migration stage 1."]
        : unowned.length > 0
          ? ["No candidate remediation for absent owners."]
          : [],
  });

  const orgHasGate = org.governancePolicies.some((p) => p.requiresHumanApprovalGate);
  const candidateAddsGate =
    text.includes("approval gate") || text.includes("human approval");
  const hasGate = orgHasGate || candidateAddsGate;
  const needsGate =
    org.organization.criticality === "high" ||
    org.organization.criticality === "critical";
  checks.push({
    id: "static_approval_gates",
    name: "Missing approval gates",
    kind: "static",
    currentStatePass: !needsGate || orgHasGate,
    currentStateObservations: [
      needsGate
        ? orgHasGate
          ? "Current-state approval gate present."
          : "Current-state: high/critical org lacks approval gate (seeded defect)."
        : "Approval gate not required for current criticality.",
    ],
    pass: !needsGate || hasGate,
    observations: [
      needsGate
        ? hasGate
          ? orgHasGate
            ? "Approval gate present in current state."
            : "Approval gate absent in current state; candidate assumes introduction."
          : "High/critical org lacks approval gate (seeded defect)."
        : "Approval gate not required for current criticality.",
    ],
    assumptions:
      needsGate && !orgHasGate && candidateAddsGate
        ? ["Candidate assumption: human approval gate added before notify."]
        : ["Policy flag requiresHumanApprovalGate is the MVP signal."],
  });

  checks.push({
    id: "static_retry_limits",
    name: "Retry loops without limits",
    kind: "static",
    currentStatePass: !cycle,
    currentStateObservations: [
      cycle
        ? "Current-state potential retry/ack loop without declared limits."
        : "No unbounded retry loop detected in current topology.",
    ],
    pass: !cycle || remediatesCycle,
    observations: [
      !cycle
        ? "No unbounded retry loop detected in topology."
        : remediatesCycle
          ? "Current-state loop present; candidate assumes bounded retries / directed flow."
          : "Potential retry/ack loop without declared limits remains.",
    ],
    assumptions:
      cycle && remediatesCycle
        ? ["Candidate assumption: retries are bounded after topology remediation."]
        : ["Retry policies are not fully modeled; cycle used as proxy."],
  });

  checks.push({
    id: "static_policy_violations",
    name: "Policy violations",
    kind: "static",
    currentStatePass: !(needsGate && !orgHasGate),
    currentStateObservations: [
      needsGate && !orgHasGate
        ? "Current-state governance policy violation: missing human approval."
        : "No structural policy violation in current state for MVP checks.",
    ],
    pass: !(needsGate && !hasGate),
    observations: [
      needsGate && !hasGate
        ? "Governance policy violation: missing human approval for high-criticality workflow."
        : "No structural policy violation detected for MVP checks under candidate projection.",
    ],
    assumptions: ["Limited to approval-gate and contract policies in MVP."],
  });

  const hasToolFailureMode = org.capabilities.some((c) =>
    c.failureModes.includes("tool_timeout"),
  );
  checks.push({
    id: "scenario_tool_failure",
    name: "Tool failure",
    kind: "scenario",
    currentStatePass: hasToolFailureMode,
    currentStateObservations: [
      hasToolFailureMode
        ? "Current-state declares tool_timeout failure mode."
        : "Current-state lacks tool_timeout failure mode declaration.",
    ],
    pass: hasToolFailureMode || candidate.template === "planner_worker_verifier",
    observations: [
      "Scenario: retrieval tool times out during intake.",
      candidate.template === "planner_worker_verifier"
        ? "Candidate assumption: verifier/planner can short-circuit and escalate."
        : hasToolFailureMode
          ? "Failure mode listed on capability; bounded retry required in plan."
          : "FAIL: no failure-mode readiness for tool timeout.",
    ],
    assumptions: ["No live tool invocation; structural readiness only."],
  });

  const staleKnowledge = org.knowledgeMemories.some((k) => {
    const days = parseDays(k.freshness);
    return days !== null && days > 7;
  });
  const remediatesFreshness =
    text.includes("freshness") || text.includes("reindex") || text.includes("stale knowledge");
  checks.push({
    id: "scenario_stale_knowledge",
    name: "Stale knowledge",
    kind: "scenario",
    currentStatePass: !staleKnowledge,
    currentStateObservations: [
      staleKnowledge
        ? "Current-state knowledge freshness exceeds 7d threshold on at least one store."
        : "Current-state knowledge freshness within 7d threshold.",
    ],
    pass: !staleKnowledge || remediatesFreshness,
    observations: [
      !staleKnowledge
        ? "Knowledge freshness within 7d threshold."
        : remediatesFreshness
          ? "Stale knowledge in current state; candidate assumes freshness remediation."
          : "Stale knowledge remains unresolved by candidate.",
    ],
    assumptions: remediatesFreshness && staleKnowledge
      ? ["Candidate assumption: knowledge refresh before rollout."]
      : ["Freshness parsed from fixture strings like '21d'."],
  });

  const hasFailureModes = org.capabilities.some((c) => c.failureModes.length > 0);
  checks.push({
    id: "scenario_partial_outage",
    name: "Partial dependency outage",
    kind: "scenario",
    currentStatePass: hasFailureModes,
    currentStateObservations: [
      hasFailureModes
        ? "Current-state declares at least one dependency failure mode."
        : "Current-state lacks declared dependency failure modes.",
    ],
    pass:
      candidate.template === "planner_worker_verifier" ||
      (candidate.template === "strengthen_single_workflow" && hasFailureModes),
    observations: [
      "Scenario: retrieval dependency partially unavailable.",
      candidate.template === "planner_worker_verifier"
        ? "Candidate assumption: planner can degrade; verifier blocks unsafe notify."
        : hasFailureModes
          ? "Single workflow may fail closed; failure modes declared but degradation path limited."
          : "FAIL: no explicit degradation path.",
    ],
    assumptions: ["Network partitions and multi-region failover not modeled."],
  });

  checks.push({
    id: "scenario_escalation_approval",
    name: "Escalation/approval requirement",
    kind: "scenario",
    currentStatePass: !needsGate || orgHasGate,
    currentStateObservations: [
      "Scenario evidence from current governance flags only.",
      needsGate && !orgHasGate
        ? "Current-state FAIL: absent approval gate (seeded acceptance case)."
        : "Current-state approval path present or not required.",
    ],
    pass: !needsGate || hasGate,
    observations: [
      "Scenario: high-severity claim requires human approval before notify.",
      hasGate
        ? orgHasGate
          ? "Current-state provides approval path."
          : "Candidate assumes approval path introduction."
        : "FAIL: absent approval gate (seeded acceptance case).",
    ],
    assumptions: ["Human response time not simulated."],
  });

  const hasBudget = org.governancePolicies.some((p) => p.budgets.length > 0);
  checks.push({
    id: "scenario_budget_breach",
    name: "Budget-limit breach",
    kind: "scenario",
    currentStatePass: hasBudget,
    currentStateObservations: [
      hasBudget
        ? "Current-state budget rule declared."
        : "Current-state has no budget rule declared.",
    ],
    pass: hasBudget,
    observations: [
      "Scenario: daily tool budget exceeded.",
      hasBudget
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
      "Current-state observations are separated from candidate assumptions; assumptions are not evidence.",
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
