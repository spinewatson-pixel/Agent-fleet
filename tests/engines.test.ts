import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ReadOnlyDiscoveryAdapter } from "../src/core/adapters/readOnlyDiscoveryAdapter.js";
import { evaluateIntentCompleteness } from "../src/core/services/intentCompleteness.js";
import { analyzeGaps } from "../src/core/engines/gapAnalysis.js";
import { synthesizeCandidates } from "../src/core/engines/candidateSynthesis.js";
import { validateAllCandidates, validateCandidate } from "../src/core/engines/validation.js";
import {
  reviewAll,
  reviewWithForcedHighScoresButGovernanceBlocker,
} from "../src/core/engines/review.js";
import {
  buildRecommendation,
  exportRecommendationArtifacts,
} from "../src/core/engines/recommendAndExport.js";
import { rejectMutation } from "../src/core/adapters/mutationGuard.js";

async function loadDemoOrg() {
  const adapter = new ReadOnlyDiscoveryAdapter();
  const demo = fs.readFileSync(
    path.resolve(process.cwd(), "fixtures/demo-org.yaml"),
    "utf8",
  );
  const org = await adapter.normalize(
    await adapter.discover(demo, { format: "yaml" }),
  );
  const intent = evaluateIntentCompleteness(org, {
    mission: "Reliable claims summarization with human governance",
    successMeasures: ["reliability >= 0.98"],
    constraints: ["human approval before notify"],
    riskTolerance: "low",
    preserveList: ["retrieval read-only authority"],
    confirmed: true,
  }).profile;
  return { org, intent };
}

describe("deterministic engines", () => {
  it("gap analysis identifies seeded defects with evidence links", async () => {
    const { org, intent } = await loadDemoOrg();
    const gaps = analyzeGaps(org, intent);
    expect(gaps.findings.some((f) => f.id.startsWith("gap_contract_"))).toBe(true);
    expect(gaps.findings.some((f) => f.id === "gap_approval_gate")).toBe(true);
    const contract = gaps.findings.find((f) => f.id.startsWith("gap_contract_"))!;
    expect(contract.evidenceIds.length).toBeGreaterThan(0);
    expect(gaps.preserveList.length).toBeGreaterThan(0);
  });

  it("synthesizes at least two candidates with trade-offs", async () => {
    const { org, intent } = await loadDemoOrg();
    const gaps = analyzeGaps(org, intent);
    const { candidates } = synthesizeCandidates(org, gaps, intent);
    expect(candidates.length).toBeGreaterThanOrEqual(2);
    expect(candidates[0].doNotUseWhen.length).toBeGreaterThan(0);
    expect(candidates[1].tradeOffs.cost).toBeDefined();
  });

  it("validation catches broken contract and absent approval-gate cases", async () => {
    const { org, intent } = await loadDemoOrg();
    const gaps = analyzeGaps(org, intent);
    const { candidates } = synthesizeCandidates(org, gaps, intent);

    // Current-org static view via a candidate that somehow does NOT mention approval
    // — use strengthen candidate but assert scenario check exists on seeded org path.
    const strengthen = candidates.find((c) => c.template === "strengthen_single_workflow")!;
    const result = validateCandidate(org, strengthen);
    const contractCheck = result.checks.find((c) => c.id === "static_missing_contracts")!;
    expect(contractCheck).toBeDefined();
    // Seeded missing contract is observed
    expect(
      contractCheck.observations.some((o) => o.toLowerCase().includes("missing contract")),
    ).toBe(true);

    // For a candidate stripped of approval language, approval scenario fails
    const bare = {
      ...strengthen,
      id: "cand_bare",
      summary: "No governance changes",
      benefits: ["minor cleanup"],
      affectedEntityIds: [],
    };
    const bareResult = validateCandidate(org, bare);
    const approval = bareResult.checks.find((c) => c.id === "scenario_escalation_approval")!;
    expect(approval.pass).toBe(false);
    const missingContracts = bareResult.checks.find((c) => c.id === "static_missing_contracts")!;
    expect(missingContracts.pass).toBe(false);
  });

  it("critical governance failure yields BLOCKED even with high other scores", async () => {
    const { org, intent } = await loadDemoOrg();
    const gaps = analyzeGaps(org, intent);
    const { candidates } = synthesizeCandidates(org, gaps, intent);
    const bare = {
      ...candidates[0],
      id: "cand_blocked",
      summary: "Cosmetic changes only",
      benefits: ["docs"],
      affectedEntityIds: [],
    };
    const validation = validateCandidate(org, bare);
    const review = reviewWithForcedHighScoresButGovernanceBlocker(
      reviewAll(org, [bare], gaps, [validation], intent)[0],
    );
    expect(review.averageScore).toBeGreaterThan(0.7);
    expect(review.status).toBe("BLOCKED");
    expect(review.blockers.length).toBeGreaterThan(0);
  });

  it("demo recommendation is blocked (no eligible fallback)", async () => {
    const { org, intent } = await loadDemoOrg();
    const gaps = analyzeGaps(org, intent);
    const { candidates } = synthesizeCandidates(org, gaps, intent);
    const validations = validateAllCandidates(org, candidates);
    const reviews = reviewAll(org, candidates, gaps, validations, intent);
    const recommendation = buildRecommendation(
      org,
      candidates,
      validations,
      reviews,
      gaps,
      intent,
    );
    expect(recommendation.chosenCandidateId).toBeNull();
    expect(recommendation.selectionStatus).toBe("BLOCKED_NO_ELIGIBLE_CANDIDATE");
    expect(() =>
      exportRecommendationArtifacts({
        org,
        intent,
        gaps,
        candidates,
        validations,
        reviews,
        recommendation,
      }),
    ).toThrow(/eligibility gate/i);
    expect(() => rejectMutation({})).toThrow(/read-only|Mutation/i);
  });

  it("export produces markdown + json with trace chain for eligible org", async () => {
    const adapter = new ReadOnlyDiscoveryAdapter();
    const eligibleYaml = fs.readFileSync(
      path.resolve(process.cwd(), "fixtures/eligible-org.yaml"),
      "utf8",
    );
    const org = await adapter.normalize(
      await adapter.discover(eligibleYaml, { format: "yaml" }),
    );
    const intent = evaluateIntentCompleteness(org, {
      mission: "Reliable claims summarization under human governance",
      successMeasures: ["reliability >= 0.98"],
      constraints: ["human approval before notify"],
      riskTolerance: "low",
      preserveList: ["retrieval read-only authority"],
      confirmed: true,
    }).profile;
    const gaps = analyzeGaps(org, intent);
    const { candidates } = synthesizeCandidates(org, gaps, intent);
    const validations = validateAllCandidates(org, candidates);
    const reviews = reviewAll(org, candidates, gaps, validations, intent);
    const recommendation = buildRecommendation(
      org,
      candidates,
      validations,
      reviews,
      gaps,
      intent,
    );
    expect(recommendation.selectionStatus).toBe("SELECTED");
    const artifact = exportRecommendationArtifacts({
      org,
      intent,
      gaps,
      candidates,
      validations,
      reviews,
      recommendation,
    });
    expect(artifact.markdown).toContain("Trace chain");
    expect(artifact.markdown).toContain("Eligibility gate");
    expect(artifact.json.traceChain).toEqual(recommendation.traceChain);
    expect(artifact.json.securityBoundaries).toMatchObject({
      readOnly: true,
      applyImplemented: false,
      liveMutationPath: false,
    });
  });
});
