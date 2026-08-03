import { describe, expect, it } from "vitest";
import {
  getCandidateRemediationSignals,
  isCriticalFindingRemediated,
} from "../src/core/engines/remediation.js";
import type { CandidateArchitecture } from "../src/core/engines/candidateSynthesis.js";
import type { GapFinding } from "../src/core/engines/gapAnalysis.js";

function candidate(
  partial: Partial<CandidateArchitecture> & Pick<CandidateArchitecture, "id" | "template">,
): CandidateArchitecture {
  return {
    name: partial.name ?? partial.id,
    summary: partial.summary ?? "",
    assumptions: partial.assumptions ?? [],
    affectedEntityIds: partial.affectedEntityIds ?? [],
    benefits: partial.benefits ?? [],
    costs: [],
    risks: [],
    reversibility: "high",
    doNotUseWhen: [],
    tradeOffs: { reliability: 0.5, cost: 0.5, latency: 0.5, governance: 0.5 },
    knowledgeIds: [],
    ...partial,
  };
}

describe("shared remediation helper", () => {
  it("detects approval-gate remediation for critical governance findings", () => {
    const c = candidate({
      id: "c1",
      template: "strengthen_single_workflow",
      summary: "Add a human approval gate before notify",
      affectedEntityIds: ["iface_x"],
    });
    const finding: GapFinding = {
      id: "gap_approval_gate",
      category: "governance",
      severity: "critical",
      title: "Absent human approval gate",
      rationale: "test",
      evidenceIds: [],
      knowledgeIds: [],
      evidenceConfidence: "high",
      entityIds: [],
    };
    expect(isCriticalFindingRemediated(c, finding)).toBe(true);
    expect(getCandidateRemediationSignals(c).addsApprovalGate).toBe(true);
  });

  it("does not treat unrelated affectedEntityIds as owner remediation", () => {
    const c = candidate({
      id: "c2",
      template: "strengthen_single_workflow",
      summary: "Add contracts and evaluation criteria",
      affectedEntityIds: ["cap_intake"],
    });
    expect(getCandidateRemediationSignals(c).remediatesOwners).toBe(false);
  });

  it("requires contract entity ids for contract critical findings", () => {
    const c = candidate({
      id: "c3",
      template: "strengthen_single_workflow",
      summary: "contracts",
      affectedEntityIds: ["iface_retrieval"],
    });
    const finding: GapFinding = {
      id: "gap_contract_iface_retrieval",
      category: "contract",
      severity: "critical",
      title: "Broken contract",
      rationale: "test",
      evidenceIds: [],
      knowledgeIds: [],
      evidenceConfidence: "high",
      entityIds: ["iface_retrieval"],
    };
    expect(isCriticalFindingRemediated(c, finding)).toBe(true);
    expect(
      isCriticalFindingRemediated(c, { ...finding, entityIds: ["iface_other"] }),
    ).toBe(false);
  });
});
