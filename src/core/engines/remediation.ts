import type { GapFinding } from "./gapAnalysis.js";
import type { CandidateArchitecture } from "./candidateSynthesis.js";

/** Structured signals derived from candidate text — single source for gate/review/validation. */
export interface CandidateRemediationSignals {
  text: string;
  addsApprovalGate: boolean;
  remediatesOrphans: boolean;
  remediatesCycle: boolean;
  remediatesOwners: boolean;
  remediatesFreshness: boolean;
  addressesContractEntity: (entityId: string) => boolean;
}

export function getCandidateRemediationSignals(
  candidate: CandidateArchitecture,
): CandidateRemediationSignals {
  const text =
    `${candidate.summary} ${candidate.benefits.join(" ")} ${candidate.assumptions.join(" ")}`.toLowerCase();

  return {
    text,
    addsApprovalGate:
      text.includes("approval gate") || text.includes("human approval"),
    remediatesOrphans:
      candidate.template === "planner_worker_verifier" ||
      text.includes("retire orphan") ||
      text.includes("remove orphan"),
    remediatesCycle:
      candidate.template === "planner_worker_verifier" ||
      (text.includes("break") && text.includes("loop")) ||
      text.includes("bounded retry"),
    remediatesOwners:
      text.includes("assign owner") ||
      text.includes("absent owner") ||
      /\bownership\b/.test(text),
    remediatesFreshness:
      text.includes("freshness") ||
      text.includes("reindex") ||
      text.includes("stale knowledge"),
    addressesContractEntity: (entityId: string) =>
      candidate.affectedEntityIds.includes(entityId),
  };
}

/** Critical gap remediation used by eligibility gate and review (must stay identical). */
export function isCriticalFindingRemediated(
  candidate: CandidateArchitecture,
  finding: GapFinding,
): boolean {
  const signals = getCandidateRemediationSignals(candidate);
  if (finding.category === "contract") {
    return finding.entityIds.some((id) => signals.addressesContractEntity(id));
  }
  if (finding.category === "governance" || finding.id === "gap_approval_gate") {
    return signals.addsApprovalGate;
  }
  // Unknown critical findings are not assumed remediated by candidate claims alone.
  return false;
}

export function listUnresolvedCriticalFindings(
  candidate: CandidateArchitecture,
  findings: GapFinding[],
): GapFinding[] {
  return findings.filter(
    (f) => f.severity === "critical" && !isCriticalFindingRemediated(candidate, f),
  );
}
