import type { CanonicalOrganization } from "../schemas/entities.js";
import type { GapAnalysisResult } from "./gapAnalysis.js";
import type { CandidateArchitecture } from "./candidateSynthesis.js";
import type { ValidationResult } from "./validation.js";
import type { ReviewResult } from "./review.js";

export interface BaselineSnapshot {
  label: "current_baseline";
  criticalGapCount: number;
  highGapCount: number;
  missingContracts: number;
  hasApprovalGate: boolean;
  orphanWorkerNodes: number;
  circularDependency: boolean;
  summary: string;
}

export interface ProposalDelta {
  candidateId: string;
  name: string;
  remediates: string[];
  residualRisks: string[];
  validationOverallPass: boolean;
  reviewStatus: "PASS" | "BLOCKED";
  weightedScore: number;
  tradeOffs: CandidateArchitecture["tradeOffs"];
  vsBaseline: string;
}

export interface BaselineProposalComparison {
  baseline: BaselineSnapshot;
  proposals: ProposalDelta[];
  notes: string;
}

/** Compare current org (baseline) to each candidate proposal — advisory only. */
export function compareBaselineToProposals(
  org: CanonicalOrganization,
  gaps: GapAnalysisResult,
  candidates: CandidateArchitecture[],
  validations: ValidationResult[],
  reviews: ReviewResult[],
): BaselineProposalComparison {
  const missingContracts = org.interfaces.filter((i) => !i.contractSchema).length;
  const hasApprovalGate = org.governancePolicies.some((p) => p.requiresHumanApprovalGate);
  const topo = org.topologies[0];
  const connected = new Set<string>();
  for (const e of topo?.edges ?? []) {
    connected.add(e.from);
    connected.add(e.to);
  }
  const orphanWorkerNodes = (topo?.nodes ?? []).filter(
    (n) => n.kind === "worker" && !connected.has(n.id),
  ).length;
  const circularDependency = gaps.findings.some((f) => f.id.startsWith("gap_cycle_"));

  const baseline: BaselineSnapshot = {
    label: "current_baseline",
    criticalGapCount: gaps.findings.filter((f) => f.severity === "critical").length,
    highGapCount: gaps.findings.filter((f) => f.severity === "high").length,
    missingContracts,
    hasApprovalGate,
    orphanWorkerNodes,
    circularDependency,
    summary: `Baseline retains ${gaps.preserveList.length} preserve-list items and ${gaps.findings.length} open gaps.`,
  };

  const proposals: ProposalDelta[] = candidates.map((c) => {
    const val = validations.find((v) => v.candidateId === c.id);
    const rev = reviews.find((r) => r.candidateId === c.id);
    const remediates: string[] = [];
    if (c.affectedEntityIds.some((id) => org.interfaces.some((i) => i.id === id && !i.contractSchema))) {
      remediates.push("missing interface contracts");
    }
    if (c.summary.toLowerCase().includes("approval gate")) {
      remediates.push("absent human approval gate");
    }
    if (c.template === "planner_worker_verifier") {
      remediates.push("orphan nodes / cyclic ack loop via topology redesign");
    }
    if (c.template === "strengthen_single_workflow") {
      remediates.push("evaluation criteria and bounded retries on single workflow");
    }

    const residualRisks = [
      ...c.risks,
      ...(rev?.blockers ?? []).map((b) => `review blocker: ${b}`),
    ];

    const vsBaseline = [
      `critical gaps baseline=${baseline.criticalGapCount}`,
      `contracts missing baseline=${baseline.missingContracts}`,
      `approvalGate baseline=${baseline.hasApprovalGate}`,
      `proposal review=${rev?.status ?? "n/a"} weighted=${(rev?.weightedScore ?? 0).toFixed(2)}`,
      `reliability trade-off ${c.tradeOffs.reliability} (cost ${c.tradeOffs.cost}, latency ${c.tradeOffs.latency})`,
    ].join("; ");

    return {
      candidateId: c.id,
      name: c.name,
      remediates,
      residualRisks,
      validationOverallPass: val?.overallPass ?? false,
      reviewStatus: rev?.status ?? "BLOCKED",
      weightedScore: rev?.weightedScore ?? 0,
      tradeOffs: c.tradeOffs,
      vsBaseline,
    };
  });

  return {
    baseline,
    proposals,
    notes:
      "Baseline is the imported canonical organization. Proposals are advisory drafts; neither is universally better.",
  };
}
