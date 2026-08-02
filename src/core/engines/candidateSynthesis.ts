import type { CanonicalOrganization, IntentProfile } from "../schemas/entities.js";
import type { GapAnalysisResult } from "./gapAnalysis.js";

export interface CandidateArchitecture {
  id: string;
  name: string;
  template: "strengthen_single_workflow" | "planner_worker_verifier";
  summary: string;
  assumptions: string[];
  affectedEntityIds: string[];
  benefits: string[];
  costs: string[];
  risks: string[];
  reversibility: string;
  doNotUseWhen: string[];
  tradeOffs: {
    reliability: number;
    cost: number;
    latency: number;
    governance: number;
  };
  knowledgeIds: string[];
}

export interface CandidateSynthesisResult {
  candidates: CandidateArchitecture[];
  notes: string;
}

/**
 * Template-backed candidate generation. Always returns at least two options.
 * Does not claim any topology is universally better.
 */
export function synthesizeCandidates(
  org: CanonicalOrganization,
  gaps: GapAnalysisResult,
  intent?: IntentProfile,
): CandidateSynthesisResult {
  const criticalContracts = gaps.findings.filter((f) => f.category === "contract");
  const governanceGaps = gaps.findings.filter((f) => f.category === "governance");
  const preserve = gaps.preserveList;

  const strengthen: CandidateArchitecture = {
    id: "cand_strengthen_single",
    name: "Strengthen single-workflow topology",
    template: "strengthen_single_workflow",
    summary:
      "Keep the existing single intake workflow; add contracts, evaluation criteria, bounded retries, and a human approval gate before notify.",
    assumptions: [
      "Workload coupling remains linear (intake → retrieval → summary → notify).",
      "Owner will confirm risk tolerance and success measures before adoption.",
      intent?.mission
        ? `Mission confirmed: ${intent.mission}`
        : "Mission still unknown — candidate remains advisory draft only.",
    ],
    affectedEntityIds: [
      ...org.interfaces.filter((i) => !i.contractSchema).map((i) => i.id),
      ...org.governancePolicies.map((p) => p.id),
      ...org.capabilities.filter((c) => c.evaluationCriteria.length === 0).map((c) => c.id),
    ],
    benefits: [
      "Closes seeded missing-contract and absent-approval-gate gaps with minimal topology change.",
      "Preserves existing strengths: " + preserve.join("; "),
      "Lower operational novelty vs. multi-agent redesign.",
    ],
    costs: [
      "Adds approval latency on high-severity claims.",
      "Engineering effort to author contract schemas and evaluation harness.",
    ],
    risks: [
      "Single-workflow remains a bottleneck under burst load.",
      "Approval gate bypass if policy not enforced at runtime (not modeled in MVP).",
    ],
    reversibility: "High — feature flags can disable approval gate and new evaluations.",
    doNotUseWhen: [
      "Workload requires parallel specialized agents with distinct authority boundaries.",
      "Governance demands strict separation of planning, execution, and verification roles.",
    ],
    tradeOffs: {
      reliability: 0.78,
      cost: 0.7,
      latency: 0.55,
      governance: 0.85,
    },
    knowledgeIds: [
      "ko_topology_no_universal_best",
      "ko_delegation_contract_integrity",
      "ko_critical_governance_blocks",
    ],
  };

  const pwv: CandidateArchitecture = {
    id: "cand_planner_worker_verifier",
    name: "Planner–worker–verifier variant",
    template: "planner_worker_verifier",
    summary:
      "Introduce explicit planner, worker, and verifier roles with delegation contracts and independent verification before notify/escalation.",
    assumptions: [
      "Organization can staff or automate a verifier role with read authority.",
      "Cost/latency increase is acceptable as a trade-off for reliability coverage.",
      `Addresses ${criticalContracts.length} contract gap(s) and ${governanceGaps.length} governance gap(s).`,
    ],
    affectedEntityIds: [
      ...org.workers.map((w) => w.id),
      ...org.topologies.map((t) => t.id),
      ...org.interfaces.map((i) => i.id),
    ],
    benefits: [
      "Explicit delegation boundaries improve contract integrity.",
      "Verifier role provides independent check before side effects.",
      "Better fit when authority and evaluation must be separated.",
    ],
    costs: [
      "Higher cost (additional model/tool calls) and latency.",
      "More complex topology and runbooks.",
    ],
    risks: [
      "Over-partitioning a simple linear workflow.",
      "Verifier becomes rubber-stamp without evaluation criteria.",
    ],
    reversibility: "Medium — requires topology rollback and retirement of new roles.",
    doNotUseWhen: [
      "Team cannot operate three-role topology (human operability risk).",
      "Strict latency SLO cannot absorb verifier hop.",
      "Preserve list forbids introducing new agent roles.",
    ],
    tradeOffs: {
      reliability: 0.88,
      cost: 0.45,
      latency: 0.4,
      governance: 0.9,
    },
    knowledgeIds: [
      "ko_topology_no_universal_best",
      "ko_delegation_contract_integrity",
      "ko_simulation_bounded",
    ],
  };

  return {
    candidates: [strengthen, pwv],
    notes:
      "Candidates are template-backed drafts. Neither topology is universally better; selection depends on coupling, governance, and stated constraints.",
  };
}
