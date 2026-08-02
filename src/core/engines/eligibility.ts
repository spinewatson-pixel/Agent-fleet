import type { GapFinding, GapAnalysisResult } from "./gapAnalysis.js";
import type { CandidateArchitecture } from "./candidateSynthesis.js";
import type { ValidationResult } from "./validation.js";
import type { ReviewResult } from "./review.js";

export type SelectionStatus =
  | "SELECTED"
  | "BLOCKED_NO_ELIGIBLE_CANDIDATE";

export interface EligibilityAssessment {
  candidateId: string;
  eligible: boolean;
  reasons: string[];
  failedValidationChecks: string[];
  unresolvedCriticalFindings: string[];
  reviewBlocked: boolean;
}

export interface EligibilityGateResult {
  assessments: EligibilityAssessment[];
  eligibleCandidateIds: string[];
  chosenCandidateId: string | null;
  selectionStatus: SelectionStatus;
  blockReasons: string[];
}

/**
 * Single eligibility gate for recommendation, review surfacing, approval, and export.
 * A candidate is eligible only when:
 * - validation has zero failed checks (overallPass),
 * - no unresolved critical gap findings remain for that candidate,
 * - independent review is not BLOCKED.
 */
export function assessCandidateEligibility(
  candidate: CandidateArchitecture,
  validation: ValidationResult,
  review: ReviewResult,
  gaps: GapAnalysisResult,
): EligibilityAssessment {
  const reasons: string[] = [];

  const failedValidationChecks = validation.checks
    .filter((c) => !c.pass)
    .map((c) => `${c.id} (${c.name})`);

  if (!validation.overallPass || failedValidationChecks.length > 0) {
    for (const f of failedValidationChecks) {
      reasons.push(`validation_failed: ${f}`);
    }
    if (!validation.overallPass && failedValidationChecks.length === 0) {
      reasons.push("validation_failed: overallPass=false");
    }
  }

  const unresolvedCritical = gaps.findings.filter(
    (f) => f.severity === "critical" && !isCriticalFindingRemediated(candidate, f),
  );
  const unresolvedCriticalFindings = unresolvedCritical.map((f) => f.id);
  for (const f of unresolvedCritical) {
    reasons.push(`unresolved_critical: ${f.id} — ${f.title}`);
  }

  const reviewBlocked = review.status === "BLOCKED" || review.blockers.length > 0;
  if (reviewBlocked) {
    if (review.blockers.length === 0) {
      reasons.push("review_blocked: status=BLOCKED");
    }
    for (const b of review.blockers) {
      reasons.push(`review_blocked: ${b}`);
    }
  }

  return {
    candidateId: candidate.id,
    eligible: reasons.length === 0,
    reasons,
    failedValidationChecks,
    unresolvedCriticalFindings,
    reviewBlocked,
  };
}

export function runEligibilityGate(input: {
  candidates: CandidateArchitecture[];
  validations: ValidationResult[];
  reviews: ReviewResult[];
  gaps: GapAnalysisResult;
}): EligibilityGateResult {
  const assessments = input.candidates.map((candidate) => {
    const validation = input.validations.find((v) => v.candidateId === candidate.id);
    const review = input.reviews.find((r) => r.candidateId === candidate.id);
    if (!validation || !review) {
      return {
        candidateId: candidate.id,
        eligible: false,
        reasons: ["missing_validation_or_review"],
        failedValidationChecks: [],
        unresolvedCriticalFindings: [],
        reviewBlocked: true,
      } satisfies EligibilityAssessment;
    }
    return assessCandidateEligibility(candidate, validation, review, input.gaps);
  });

  const eligible = assessments.filter((a) => a.eligible);
  const eligibleCandidateIds = eligible.map((a) => a.candidateId);

  // Rank eligible by review weighted score; never fall back to ineligible.
  const chosenCandidateId =
    eligible
      .map((a) => ({
        id: a.candidateId,
        score:
          input.reviews.find((r) => r.candidateId === a.candidateId)?.weightedScore ?? 0,
      }))
      .sort((a, b) => b.score - a.score)[0]?.id ?? null;

  const blockReasons =
    chosenCandidateId === null
      ? [
          "No eligible candidate: every candidate failed validation checks, left critical findings unresolved, and/or was review-blocked.",
          ...assessments.flatMap((a) =>
            a.reasons.map((r) => `[${a.candidateId}] ${r}`),
          ),
        ]
      : [];

  return {
    assessments,
    eligibleCandidateIds,
    chosenCandidateId,
    selectionStatus:
      chosenCandidateId === null ? "BLOCKED_NO_ELIGIBLE_CANDIDATE" : "SELECTED",
    blockReasons,
  };
}

/** Re-check a previously chosen id; used by approval/export to prevent stale invalid selection. */
export function assertEligibleForApprovalExport(input: {
  chosenCandidateId: string | null;
  gate: EligibilityGateResult;
}): { ok: true } | { ok: false; reasons: string[] } {
  if (!input.chosenCandidateId) {
    return {
      ok: false,
      reasons:
        input.gate.blockReasons.length > 0
          ? input.gate.blockReasons
          : ["No candidate selected; approval/export blocked."],
    };
  }
  const assessment = input.gate.assessments.find(
    (a) => a.candidateId === input.chosenCandidateId,
  );
  if (!assessment?.eligible) {
    return {
      ok: false,
      reasons: assessment?.reasons?.length
        ? assessment.reasons
        : [
            `Chosen candidate ${input.chosenCandidateId} is not eligible for approval/export.`,
          ],
    };
  }
  // Ensure gate ranking still includes this id (no stale bypass)
  if (!input.gate.eligibleCandidateIds.includes(input.chosenCandidateId)) {
    return {
      ok: false,
      reasons: [`Candidate ${input.chosenCandidateId} missing from eligibility gate.`],
    };
  }
  return { ok: true };
}

function isCriticalFindingRemediated(
  candidate: CandidateArchitecture,
  finding: GapFinding,
): boolean {
  if (finding.category === "contract") {
    return finding.entityIds.some((id) => candidate.affectedEntityIds.includes(id));
  }
  if (finding.category === "governance" || finding.id === "gap_approval_gate") {
    const text = `${candidate.summary} ${candidate.benefits.join(" ")}`.toLowerCase();
    return text.includes("approval gate") || text.includes("human approval");
  }
  // Unknown critical findings are not assumed remediated by candidate claims alone.
  return false;
}
