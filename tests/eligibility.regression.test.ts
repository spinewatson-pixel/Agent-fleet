import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { BuilderPipeline } from "../src/core/pipeline.js";
import { JsonFileWorkspaceStore } from "../src/core/services/workspaceStore.js";
import type { RecommendationResult } from "../src/core/engines/recommendAndExport.js";
import type { ValidationResult } from "../src/core/engines/validation.js";
import type { EligibilityGateResult } from "../src/core/engines/eligibility.js";
import { evaluateIntentCompleteness } from "../src/core/services/intentCompleteness.js";
import { ReadOnlyDiscoveryAdapter } from "../src/core/adapters/readOnlyDiscoveryAdapter.js";

describe("eligibility gate regressions (release-blocking)", () => {
  const dirs: string[] = [];

  afterEach(() => {
    for (const d of dirs) fs.rmSync(d, { recursive: true, force: true });
  });

  function pipeline() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "af-elig-"));
    dirs.push(dir);
    return new BuilderPipeline(new JsonFileWorkspaceStore(dir));
  }

  async function analyzeDemo(p: BuilderPipeline) {
    const imported = await p.importDemo();
    await p.updateIntent(imported.organizationId, {
      mission: "Reliable claims summarization under human governance",
      successMeasures: ["usable draft rate >= 0.98"],
      constraints: ["human approval before notify"],
      riskTolerance: "low",
      preserveList: ["retrieval read-only authority"],
      confirmed: true,
    });
    return p.runAnalysis(imported.organizationId);
  }

  it("(1) demo failing candidates cannot be approved/exported", async () => {
    const p = pipeline();
    const analyzed = await analyzeDemo(p);
    const rec = analyzed.recommendation as RecommendationResult;
    const validations = analyzed.validationResults as ValidationResult[];
    const gate = analyzed.eligibility as EligibilityGateResult;

    expect(validations.every((v) => v.overallPass === false)).toBe(true);
    expect(gate.selectionStatus).toBe("BLOCKED_NO_ELIGIBLE_CANDIDATE");
    expect(rec.chosenCandidateId).toBeNull();
    expect(rec.selectionStatus).toBe("BLOCKED_NO_ELIGIBLE_CANDIDATE");
    expect(gate.blockReasons.length).toBeGreaterThan(0);

    // Explicitly prove neither demo candidate id can be approved even if forced.
    for (const cand of (
      analyzed.candidates as { candidates: Array<{ id: string }> }
    ).candidates) {
      await expect(
        p.approveAndExport(analyzed.organizationId, "approved"),
      ).rejects.toThrow(/eligibility gate/i);
      expect(cand.id).toMatch(/^cand_/);
    }

    const after = await p.getStore().get(analyzed.organizationId);
    expect(after?.exports.length ?? 0).toBe(0);
  });

  it("(2) an eligible validated candidate can be approved/exported", async () => {
    const p = pipeline();
    const imported = await p.importFixture("eligible-org.yaml");
    await p.updateIntent(imported.organizationId, {
      mission: "Reliable claims summarization under human governance",
      successMeasures: ["usable draft rate >= 0.98"],
      constraints: ["human approval before notify"],
      riskTolerance: "low",
      preserveList: ["retrieval read-only authority"],
      confirmed: true,
    });
    const analyzed = await p.runAnalysis(imported.organizationId);
    const rec = analyzed.recommendation as RecommendationResult;
    const gate = analyzed.eligibility as EligibilityGateResult;
    const validations = analyzed.validationResults as ValidationResult[];

    expect(gate.selectionStatus).toBe("SELECTED");
    expect(rec.chosenCandidateId).toBeTruthy();
    expect(
      validations.find((v) => v.candidateId === rec.chosenCandidateId)?.overallPass,
    ).toBe(true);
    expect(
      gate.assessments.find((a) => a.candidateId === rec.chosenCandidateId)?.eligible,
    ).toBe(true);

    const exported = await p.approveAndExport(imported.organizationId, "approved");
    expect(exported.exports.length).toBe(1);
    expect(exported.exports[0].markdown).toContain("Eligibility gate");
    expect(exported.changeHistory[0].approvalState).toBe("exported");
    expect(exported.changeHistory[0].candidateId).toBe(rec.chosenCandidateId);
  });

  it("(3) no-candidate condition blocks cleanly with reasons", async () => {
    const p = pipeline();
    const analyzed = await analyzeDemo(p);
    const rec = analyzed.recommendation as RecommendationResult;
    const gate = analyzed.eligibility as EligibilityGateResult;

    expect(rec.chosenCandidateId).toBeNull();
    expect(rec.selectionStatus).toBe("BLOCKED_NO_ELIGIBLE_CANDIDATE");
    expect(gate.eligibleCandidateIds).toEqual([]);
    expect(gate.blockReasons.some((r) => /No eligible candidate/i.test(r))).toBe(true);
    expect(rec.rationale).toMatch(/BLOCKED_NO_ELIGIBLE_CANDIDATE/);
    expect(rec.changeSet.outcome).toMatch(/Blocked\/no-selection/i);

    await expect(
      p.approveAndExport(analyzed.organizationId, "approved"),
    ).rejects.toThrow(/No eligible candidate|eligibility gate/i);

    // Rejection still records without exporting a recommendation artifact.
    const rejected = await p.approveAndExport(analyzed.organizationId, "rejected");
    expect(rejected.exports.length).toBe(0);
    expect(rejected.changeHistory.at(-1)?.approvalState).toBe("rejected");
  });

  it("owner assertions are not labeled high-confidence without corroboration", async () => {
    const adapter = new ReadOnlyDiscoveryAdapter();
    const demo = fs.readFileSync(
      path.resolve(process.cwd(), "fixtures/demo-org.yaml"),
      "utf8",
    );
    const org = await adapter.normalize(
      await adapter.discover(demo, { format: "yaml" }),
    );
    const result = evaluateIntentCompleteness(org, {
      mission: "Owner-stated mission only",
      successMeasures: ["x"],
      constraints: ["y"],
      riskTolerance: "low",
      preserveList: ["z"],
      confirmed: true,
    });
    expect(result.profile.fieldConfidence.mission).toBe("medium");
    expect(result.profile.fieldConfidence.riskTolerance).toBe("medium");
    expect(result.profile.fieldConfidence.mission).not.toBe("high");

    const p = pipeline();
    const imported = await p.importDemo();
    const updated = await p.updateIntent(imported.organizationId, {
      mission: "Owner assertion",
      successMeasures: ["m"],
      constraints: ["c"],
      riskTolerance: "low",
      preserveList: ["p"],
      confirmed: true,
    });
    const assertion = updated.canonical.evidence.find(
      (e) => e.sourceType === "owner_statement",
    );
    expect(assertion?.status).toBe("assertion");
    expect(assertion?.confidence).toBe("medium");
  });

  it("validation separates current-state observations from candidate assumptions", async () => {
    const p = pipeline();
    const analyzed = await analyzeDemo(p);
    const validations = analyzed.validationResults as ValidationResult[];
    const strengthen = validations.find((v) => v.candidateId === "cand_strengthen_single")!;
    const orphan = strengthen.checks.find((c) => c.id === "static_orphaned_nodes")!;
    expect(orphan.currentStatePass).toBe(false);
    expect(orphan.currentStateObservations.some((o) => /Current-state orphan/i.test(o))).toBe(
      true,
    );
    expect(orphan.pass).toBe(false);
  });
});
