import type { CanonicalOrganization, IntentProfile } from "../schemas/entities.js";
import type { CandidateArchitecture } from "./candidateSynthesis.js";
import type { GapAnalysisResult } from "./gapAnalysis.js";
import type { ValidationResult } from "./validation.js";
import { MVP_CONFIG } from "../schemas/common.js";
import { listUnresolvedCriticalFindings } from "./remediation.js";

export type ReviewDimension =
  | "intent_fit"
  | "contract_integrity"
  | "governance_safety"
  | "reliability_recovery"
  | "observability"
  | "cost_capacity"
  | "maintainability_portability"
  | "human_operability";

export interface DimensionScore {
  dimension: ReviewDimension;
  score: number; // 0..1
  notes: string;
  blocker: boolean;
  blockerReason?: string;
}

export interface ReviewResult {
  candidateId: string;
  dimensions: DimensionScore[];
  averageScore: number;
  weightedScore: number;
  blockers: string[];
  status: "PASS" | "BLOCKED";
  knowledgeIds: string[];
  summary: string;
}

/**
 * Independent pure review. Critical blockers are non-averaging:
 * any blocker yields BLOCKED regardless of overall score.
 */
export function reviewCandidate(
  org: CanonicalOrganization,
  candidate: CandidateArchitecture,
  gaps: GapAnalysisResult,
  validation: ValidationResult,
  intent?: IntentProfile,
): ReviewResult {
  const dimensions: DimensionScore[] = [];

  const missionKnown = Boolean(intent?.mission ?? org.organization.mission);
  dimensions.push({
    dimension: "intent_fit",
    score: missionKnown ? 0.75 : 0.35,
    notes: missionKnown
      ? "Candidate maps to stated/partial intent and capability coverage objective."
      : "Mission unknown — intent fit cannot be high-confidence.",
    blocker: false,
  });

  const missingContracts = org.interfaces.filter((i) => !i.contractSchema);
  const contractsFixed =
    missingContracts.length === 0 ||
    missingContracts.every((i) => candidate.affectedEntityIds.includes(i.id));
  dimensions.push({
    dimension: "contract_integrity",
    score: contractsFixed ? 0.85 : 0.3,
    notes: contractsFixed
      ? "Candidate addresses missing contracts at delegation boundaries."
      : "Missing contracts remain unaddressed.",
    blocker: !contractsFixed,
    blockerReason: !contractsFixed
      ? "Critical contract integrity failure: missing interface contracts not remediated."
      : undefined,
  });

  const needsGate =
    org.organization.criticality === "high" ||
    org.organization.criticality === "critical";
  const gateAddressed =
    !needsGate ||
    org.governancePolicies.some((p) => p.requiresHumanApprovalGate) ||
    candidate.summary.toLowerCase().includes("approval gate") ||
    candidate.benefits.some((b) => b.toLowerCase().includes("approval"));
  // For review, we also treat validation failure on approval scenario as blocker signal
  const approvalCheck = validation.checks.find((c) => c.id === "scenario_escalation_approval");
  const governanceBlocker = needsGate && !gateAddressed;
  dimensions.push({
    dimension: "governance_safety",
    score: gateAddressed ? 0.9 : 0.2,
    notes: gateAddressed
      ? "Human approval gate present or introduced; advisory path preserved."
      : "Critical governance failure: absent approval gate on high-criticality workflow.",
    blocker: governanceBlocker,
    blockerReason: governanceBlocker
      ? "Critical governance failure blocks recommendation (ko_critical_governance_blocks)."
      : undefined,
  });

  const reliabilityScore = candidate.tradeOffs.reliability;
  dimensions.push({
    dimension: "reliability_recovery",
    score: reliabilityScore,
    notes: `Template reliability trade-off ${reliabilityScore}; recovery depends on failure modes and retries.`,
    blocker: false,
  });

  const obsGaps = gaps.findings.filter((f) => f.category === "observability").length;
  dimensions.push({
    dimension: "observability",
    score: Math.max(0.2, 0.8 - obsGaps * 0.1),
    notes: `${obsGaps} observability-related gaps in current state.`,
    blocker: false,
  });

  dimensions.push({
    dimension: "cost_capacity",
    score: candidate.tradeOffs.cost,
    notes: "Cost recorded as trade-off, not automatic optimization target.",
    blocker: false,
  });

  dimensions.push({
    dimension: "maintainability_portability",
    score: candidate.template === "strengthen_single_workflow" ? 0.85 : 0.65,
    notes:
      candidate.template === "strengthen_single_workflow"
        ? "Lower structural novelty; easier rollback."
        : "Additional roles increase maintainability burden.",
    blocker: false,
  });

  const operabilityBlocker =
    candidate.template === "planner_worker_verifier" &&
    (intent?.constraints ?? []).some((c) =>
      c.toLowerCase().includes("no new agent roles"),
    );
  dimensions.push({
    dimension: "human_operability",
    score: candidate.template === "strengthen_single_workflow" ? 0.8 : 0.6,
    notes: "Human operability assessed from template complexity and constraints.",
    blocker: operabilityBlocker,
    blockerReason: operabilityBlocker
      ? "Constraint forbids new agent roles."
      : undefined,
  });

  // Inject explicit blocker if validation shows absent approval and candidate somehow scored high
  // without addressing it — belt and suspenders for acceptance criterion.
  if (approvalCheck && !approvalCheck.pass && !gateAddressed) {
    const gov = dimensions.find((d) => d.dimension === "governance_safety")!;
    gov.blocker = true;
    gov.blockerReason =
      "Critical governance failure: validation scenario escalation/approval failed.";
    gov.score = Math.min(gov.score, 0.2);
  }

  const blockers = dimensions
    .filter((d) => d.blocker)
    .map((d) => d.blockerReason ?? `${d.dimension} blocker`);

  // Eligibility-aligned: failed validation checks are non-averaging review blockers.
  if (!validation.overallPass) {
    const failed = validation.checks.filter((c) => !c.pass).map((c) => c.id);
    blockers.push(
      `Validation failed checks (ineligible): ${failed.join(", ") || "overallPass=false"}`,
    );
  }
  for (const f of listUnresolvedCriticalFindings(candidate, gaps.findings)) {
    blockers.push(`Unresolved critical finding: ${f.id} — ${f.title}`);
  }

  const averageScore =
    dimensions.reduce((s, d) => s + d.score, 0) / dimensions.length;

  const w = MVP_CONFIG.candidateComparisonWeights;
  const weightedScore =
    (dimensions.find((d) => d.dimension === "intent_fit")?.score ?? 0) * w.intentFit +
    (dimensions.find((d) => d.dimension === "reliability_recovery")?.score ?? 0) *
      w.reliability +
    (dimensions.find((d) => d.dimension === "governance_safety")?.score ?? 0) *
      w.governance +
    (dimensions.find((d) => d.dimension === "observability")?.score ?? 0) *
      w.observability +
    (dimensions.find((d) => d.dimension === "cost_capacity")?.score ?? 0) * w.cost +
    (dimensions.find((d) => d.dimension === "maintainability_portability")?.score ?? 0) *
      w.maintainability;

  const status: "PASS" | "BLOCKED" = blockers.length > 0 ? "BLOCKED" : "PASS";

  return {
    candidateId: candidate.id,
    dimensions,
    averageScore,
    weightedScore,
    blockers,
    status,
    knowledgeIds: ["ko_critical_governance_blocks", "ko_topology_no_universal_best"],
    summary:
      status === "BLOCKED"
        ? `BLOCKED despite average=${averageScore.toFixed(2)} / weighted=${weightedScore.toFixed(2)}. Blockers are non-averaging.`
        : `PASS with average=${averageScore.toFixed(2)} / weighted=${weightedScore.toFixed(2)}.`,
  };
}

export function reviewAll(
  org: CanonicalOrganization,
  candidates: CandidateArchitecture[],
  gaps: GapAnalysisResult,
  validations: ValidationResult[],
  intent?: IntentProfile,
): ReviewResult[] {
  return candidates.map((c) => {
    const v = validations.find((x) => x.candidateId === c.id)!;
    return reviewCandidate(org, c, gaps, v, intent);
  });
}

/**
 * Special helper for acceptance: review a proposal that still has a critical
 * governance failure even if other dimension scores are artificially high.
 */
export function reviewWithForcedHighScoresButGovernanceBlocker(
  base: ReviewResult,
): ReviewResult {
  const dimensions = base.dimensions.map((d) =>
    d.dimension === "governance_safety"
      ? {
          ...d,
          score: 0.1,
          blocker: true,
          blockerReason:
            "Critical governance failure blocks recommendation (ko_critical_governance_blocks).",
        }
      : { ...d, score: 0.95, blocker: false, blockerReason: undefined },
  );
  const averageScore =
    dimensions.reduce((s, d) => s + d.score, 0) / dimensions.length;
  const blockers = dimensions.filter((d) => d.blocker).map((d) => d.blockerReason!);
  return {
    ...base,
    dimensions,
    averageScore,
    blockers,
    status: blockers.length > 0 ? "BLOCKED" : "PASS",
    summary: `BLOCKED despite high average=${averageScore.toFixed(2)}. Critical blockers are non-averaging.`,
  };
}
