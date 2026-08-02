import type {
  CanonicalOrganization,
  ChangeSet,
  IntentProfile,
} from "../schemas/entities.js";
import { SCHEMA_VERSION } from "../schemas/common.js";
import { newId, nowIso } from "../util/ids.js";
import { KNOWLEDGE_OBJECTS } from "../knowledge/knowledgeObjects.js";
import type { GapAnalysisResult } from "./gapAnalysis.js";
import type { CandidateArchitecture } from "./candidateSynthesis.js";
import type { ValidationResult } from "./validation.js";
import type { ReviewResult } from "./review.js";
import type { BaselineProposalComparison } from "./baselineComparison.js";
import {
  assertEligibleForApprovalExport,
  runEligibilityGate,
  type EligibilityGateResult,
  type SelectionStatus,
} from "./eligibility.js";

export interface RecommendationResult {
  chosenCandidateId: string | null;
  rejectedCandidateIds: string[];
  selectionStatus: SelectionStatus;
  eligibility: EligibilityGateResult;
  rationale: string;
  uncertainty: string[];
  approvalState: ChangeSet["approvalState"];
  changeSet: ChangeSet;
  traceChain: string[];
}

export interface ExportArtifactContent {
  id: string;
  markdown: string;
  json: Record<string, unknown>;
}

export function buildRecommendation(
  org: CanonicalOrganization,
  candidates: CandidateArchitecture[],
  validations: ValidationResult[],
  reviews: ReviewResult[],
  gaps: GapAnalysisResult,
  intent?: IntentProfile,
): RecommendationResult {
  const eligibility = runEligibilityGate({
    candidates,
    validations,
    reviews,
    gaps,
  });

  const chosenCandidate = eligibility.chosenCandidateId
    ? candidates.find((c) => c.id === eligibility.chosenCandidateId) ?? null
    : null;

  // Never fall back to an ineligible / review-only PASS candidate.
  const rejected = candidates
    .filter((c) => c.id !== chosenCandidate?.id)
    .map((c) => c.id);

  const uncertainty = [
    ...(intent?.unresolvedQuestions ?? []),
    "Validation is declared-fidelity only; not proof of production behavior.",
    "Cost and latency are trade-offs, not automatic optimization targets.",
    "Owner assertions are not high-confidence without corroborating observation.",
  ];

  const ts = nowIso();
  const blocked = eligibility.selectionStatus === "BLOCKED_NO_ELIGIBLE_CANDIDATE";
  const changeSet: ChangeSet = {
    id: newId("change"),
    schemaVersion: SCHEMA_VERSION,
    createdAt: ts,
    updatedAt: ts,
    ownerIds: org.organization.owners,
    evidenceIds: org.evidence.map((e) => e.id).slice(0, 5),
    proposal: chosenCandidate
      ? `Adopt advisory recommendation: ${chosenCandidate.name}`
      : "BLOCKED: no eligible candidate — approval/export of a recommendation is not permitted.",
    affectedEntityIds: chosenCandidate?.affectedEntityIds ?? [],
    predictedImpact: chosenCandidate
      ? `Reliability trade-off ${chosenCandidate.tradeOffs.reliability}; cost ${chosenCandidate.tradeOffs.cost}; latency ${chosenCandidate.tradeOffs.latency}.`
      : "No selectable recommendation.",
    approvalState: "draft",
    rollout: chosenCandidate
      ? "Staged: (1) contracts+owners (2) approval gate (3) evaluations (4) topology changes if any"
      : undefined,
    rollback: chosenCandidate?.reversibility,
    outcome: blocked
      ? `Blocked/no-selection. Reasons: ${eligibility.blockReasons.slice(0, 5).join(" | ")}`
      : undefined,
    candidateId: chosenCandidate?.id,
    exportArtifactIds: [],
  };

  return {
    chosenCandidateId: chosenCandidate?.id ?? null,
    rejectedCandidateIds: rejected,
    selectionStatus: eligibility.selectionStatus,
    eligibility,
    rationale: chosenCandidate
      ? `Selected eligible candidate ${chosenCandidate.id} via eligibility gate (validation pass, no unresolved critical findings, review PASS). Weighted score ${(
          reviews.find((r) => r.candidateId === chosenCandidate.id)?.weightedScore ?? 0
        ).toFixed(2)}.`
      : `BLOCKED_NO_ELIGIBLE_CANDIDATE. ${eligibility.blockReasons[0] ?? "No eligible candidate."}`,
    uncertainty,
    approvalState: "draft",
    changeSet,
    traceChain: [
      "Mission",
      "Intent",
      "Evidence",
      "Knowledge",
      "Simulation/Validation",
      "Architecture Review",
      "Recommendation",
      "Approval/Outcome",
    ],
  };
}

export function exportRecommendationArtifacts(input: {
  org: CanonicalOrganization;
  intent?: IntentProfile;
  gaps: GapAnalysisResult;
  candidates: CandidateArchitecture[];
  validations: ValidationResult[];
  reviews: ReviewResult[];
  recommendation: RecommendationResult;
  baselineComparison?: BaselineProposalComparison;
}): ExportArtifactContent {
  const {
    org,
    intent,
    gaps,
    candidates,
    validations,
    reviews,
    recommendation,
    baselineComparison,
  } = input;

  const gateCheck = assertEligibleForApprovalExport({
    chosenCandidateId: recommendation.chosenCandidateId,
    gate: recommendation.eligibility,
  });
  if (!gateCheck.ok) {
    throw new Error(
      `Export blocked by eligibility gate: ${gateCheck.reasons.join("; ")}`,
    );
  }

  const chosen = candidates.find((c) => c.id === recommendation.chosenCandidateId);
  if (!chosen) {
    throw new Error("Export blocked: chosen eligible candidate missing from candidate set.");
  }

  const id = newId("export");

  const json: Record<string, unknown> = {
    artifactId: id,
    schemaVersion: SCHEMA_VERSION,
    generatedAt: nowIso(),
    operatingMode: "advisory_export_only",
    mutationAllowed: false,
    selectionStatus: recommendation.selectionStatus,
    eligibility: recommendation.eligibility,
    traceChain: recommendation.traceChain,
    problem: {
      organizationId: org.organization.id,
      name: org.organization.name,
      criticality: org.organization.criticality,
      scope: org.organization.scope,
    },
    reconstructedIntent: {
      mission: intent?.mission ?? null,
      successMeasures: intent?.successMeasures ?? [],
      constraints: intent?.constraints ?? [],
      riskTolerance: intent?.riskTolerance ?? "unknown",
      unresolvedQuestions: intent?.unresolvedQuestions ?? [],
      fieldConfidence: intent?.fieldConfidence ?? {},
      status: "owner_confirmed_or_incomplete",
    },
    evidence: org.evidence.map((e) => ({
      id: e.id,
      sourceType: e.sourceType,
      status: e.status,
      summary: e.summary,
      collectedAt: e.collectedAt,
      freshness: e.freshness,
      confidence: e.confidence,
      lineage: e.lineage,
    })),
    knowledgeCitations: KNOWLEDGE_OBJECTS.filter((k) =>
      [
        ...gaps.findings.flatMap((f) => f.knowledgeIds),
        ...chosen.knowledgeIds,
        ...reviews.flatMap((r) => r.knowledgeIds),
      ].includes(k.id),
    ),
    currentStatePreserveList: gaps.preserveList,
    gapFindings: gaps.findings,
    baselineComparison: baselineComparison ?? null,
    candidates: candidates.map((c) => ({
      ...c,
      review: reviews.find((r) => r.candidateId === c.id),
      validation: validations.find((v) => v.candidateId === c.id),
      eligibility: recommendation.eligibility.assessments.find(
        (a) => a.candidateId === c.id,
      ),
    })),
    recommendation: {
      chosenCandidateId: recommendation.chosenCandidateId,
      rejectedCandidateIds: recommendation.rejectedCandidateIds,
      selectionStatus: recommendation.selectionStatus,
      rationale: recommendation.rationale,
      uncertainty: recommendation.uncertainty,
      approvalState: recommendation.approvalState,
    },
    migrationPlan: {
      stages: [
        {
          stage: 1,
          name: "Contracts and ownership",
          owner: org.organization.owners[0] ?? "owner_platform",
          actions: [
            "Author missing interface contract schemas",
            "Assign owners to unowned capabilities",
          ],
          successMetrics: ["All interfaces have contractSchema", "No unowned capabilities"],
        },
        {
          stage: 2,
          name: "Approval gate",
          owner: org.organization.owners[0] ?? "owner_platform",
          actions: [
            "Enable requiresHumanApprovalGate on governance policy",
            "Wire notify path behind human approval",
          ],
          successMetrics: ["Approval scenario check passes"],
          approvalGate: "Human architecture owner must approve before stage 3",
        },
        {
          stage: 3,
          name: "Evaluation and recovery",
          owner: "owner_platform",
          actions: [
            "Add evaluation criteria to capabilities",
            "Bound retries; break cyclic ack loops",
          ],
          successMetrics: ["Reliability target progress", "No unbounded retry loops"],
        },
        {
          stage: 4,
          name: chosen.template === "planner_worker_verifier" ? "Topology split" : "Stabilize",
          owner: "owner_platform",
          actions:
            chosen.template === "planner_worker_verifier"
              ? ["Introduce planner/worker/verifier roles", "Retire orphan nodes"]
              : ["Monitor metrics", "Keep single workflow with new gates"],
          successMetrics: ["Review status remains PASS", "Preserve list intact"],
          rollback: chosen.reversibility,
        },
      ],
      rollback: chosen.reversibility,
      successMetrics: intent?.successMeasures ?? [],
    },
    securityBoundaries: {
      readOnly: true,
      applyImplemented: false,
      secretsStored: false,
      liveMutationPath: false,
    },
    changeSet: recommendation.changeSet,
  };

  const md = renderMarkdown({
    org,
    intent,
    gaps,
    candidates,
    validations,
    reviews,
    recommendation,
    chosen,
    baselineComparison,
    json,
  });

  return { id, markdown: md, json };
}

function renderMarkdown(args: {
  org: CanonicalOrganization;
  intent?: IntentProfile;
  gaps: GapAnalysisResult;
  candidates: CandidateArchitecture[];
  validations: ValidationResult[];
  reviews: ReviewResult[];
  recommendation: RecommendationResult;
  chosen: CandidateArchitecture;
  baselineComparison?: BaselineProposalComparison;
  json: Record<string, unknown>;
}): string {
  const {
    org,
    intent,
    gaps,
    candidates,
    validations,
    reviews,
    recommendation,
    chosen,
    baselineComparison,
  } = args;

  const lines: string[] = [];
  lines.push(`# Architecture Recommendation — ${org.organization.name}`);
  lines.push("");
  lines.push("**Operating mode:** advisory-only / export-only. No deployment or mutation.");
  lines.push(`**Selection status:** ${recommendation.selectionStatus}`);
  lines.push("");
  lines.push("## Trace chain");
  lines.push(recommendation.traceChain.join(" → "));
  lines.push("");
  lines.push("## Problem & reconstructed intent");
  lines.push(`- Organization: ${org.organization.name} (${org.organization.criticality ?? "criticality unknown"})`);
  lines.push(`- Mission: ${intent?.mission ?? "_unknown — owner must state_"}`);
  lines.push(`- Risk tolerance: ${intent?.riskTolerance ?? "unknown"}`);
  lines.push(`- Success measures: ${(intent?.successMeasures ?? []).join("; ") || "_none stated_"}`);
  lines.push(`- Constraints: ${(intent?.constraints ?? []).join("; ") || "_none stated_"}`);
  if ((intent?.unresolvedQuestions ?? []).length) {
    lines.push("- Unresolved questions:");
    for (const q of intent!.unresolvedQuestions) lines.push(`  - ${q}`);
  }
  lines.push("");
  lines.push("## Evidence citations");
  for (const e of org.evidence) {
    lines.push(
      `- \`[${e.status}]\` ${e.id} — ${e.summary} (confidence=${e.confidence}, freshness=${e.freshness ?? "n/a"}, collected=${e.collectedAt})`,
    );
  }
  lines.push("");
  lines.push("## Current state & preserve list");
  for (const p of gaps.preserveList) lines.push(`- Preserve: ${p}`);
  lines.push("");
  lines.push("## Gap findings");
  for (const f of gaps.findings) {
    lines.push(
      `- **[${f.severity}/${f.category}]** ${f.title} — ${f.rationale} (evidence: ${f.evidenceIds.join(", ") || "none"}; knowledge: ${f.knowledgeIds.join(", ")})`,
    );
  }
  lines.push("");
  if (baselineComparison) {
    lines.push("## Baseline vs proposals");
    lines.push(
      `- Baseline: critical=${baselineComparison.baseline.criticalGapCount}, missingContracts=${baselineComparison.baseline.missingContracts}, approvalGate=${baselineComparison.baseline.hasApprovalGate}`,
    );
    for (const p of baselineComparison.proposals) {
      lines.push(
        `- Proposal \`${p.candidateId}\` review=${p.reviewStatus}: ${p.vsBaseline}`,
      );
    }
    lines.push("");
  }
  lines.push("## Eligibility gate");
  for (const a of recommendation.eligibility.assessments) {
    lines.push(
      `- \`${a.candidateId}\` eligible=${a.eligible}${
        a.reasons.length ? ` — ${a.reasons.join("; ")}` : ""
      }`,
    );
  }
  lines.push("");
  lines.push("## Candidate comparison");
  for (const c of candidates) {
    const rev = reviews.find((r) => r.candidateId === c.id);
    const val = validations.find((v) => v.candidateId === c.id);
    lines.push(`### ${c.name} (\`${c.id}\`)`);
    lines.push(c.summary);
    lines.push(`- Trade-offs: reliability=${c.tradeOffs.reliability}, cost=${c.tradeOffs.cost}, latency=${c.tradeOffs.latency}, governance=${c.tradeOffs.governance}`);
    lines.push(`- Do not use when: ${c.doNotUseWhen.join("; ")}`);
    lines.push(`- Validation overallPass=${val?.overallPass}; limitations: ${val?.limitations.join(" ")}`);
    lines.push(`- Review status=**${rev?.status}** weighted=${rev?.weightedScore.toFixed(2)} blockers=${rev?.blockers.length ?? 0}`);
    if (rev?.blockers.length) {
      for (const b of rev.blockers) lines.push(`  - BLOCKER: ${b}`);
    }
    lines.push("");
  }
  lines.push("## Recommendation");
  lines.push(recommendation.rationale);
  lines.push(`- Chosen: ${recommendation.chosenCandidateId ?? "_none_"}`);
  lines.push(`- Rejected: ${recommendation.rejectedCandidateIds.join(", ") || "_none_"}`);
  lines.push(`- Approval state: ${recommendation.approvalState} (human review required; no approval = no deployment)`);
  lines.push("");
  lines.push("## Uncertainty & simulation limitations");
  for (const u of recommendation.uncertainty) lines.push(`- ${u}`);
  lines.push("- Declared fidelity: static structure + scenario readiness only.");
  lines.push("- Current-state observations are distinct from candidate assumptions.");
  lines.push("");
  lines.push("## Staged migration plan");
  lines.push("1. **Contracts and ownership** — owner: platform — success: all contracts present.");
  lines.push("2. **Approval gate** — human approval required before notify; gate before stage 3.");
  lines.push("3. **Evaluation and recovery** — criteria + bounded retries.");
  lines.push(
    `4. **${chosen.template === "planner_worker_verifier" ? "Topology split" : "Stabilize"}** — rollback: ${chosen.reversibility}`,
  );
  lines.push("");
  lines.push("## Security boundaries");
  lines.push("- Read-only discovery only; `apply` rejected.");
  lines.push("- No secrets stored; no live mutation path.");
  lines.push("- Eligibility gate blocks approve/export of invalid candidates.");
  lines.push("");
  return lines.join("\n");
}
