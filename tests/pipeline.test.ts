import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { BuilderPipeline } from "../src/core/pipeline.js";
import { JsonFileWorkspaceStore } from "../src/core/services/workspaceStore.js";
import type { RecommendationResult } from "../src/core/engines/recommendAndExport.js";

describe("BuilderPipeline acceptance slice", () => {
  const dirs: string[] = [];

  afterEach(() => {
    for (const d of dirs) {
      fs.rmSync(d, { recursive: true, force: true });
    }
  });

  it("demo imports and analysis blocks ineligible approve/export", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "af-ws-"));
    dirs.push(dir);
    const pipeline = new BuilderPipeline(new JsonFileWorkspaceStore(dir));

    const imported = await pipeline.importDemo();
    expect(imported.canonical.organization.name).toContain("Contoso");
    expect(imported.intent?.unresolvedQuestions.length).toBeGreaterThan(0);

    await pipeline.updateIntent(imported.organizationId, {
      mission: "Reliable claims summarization under human governance",
      successMeasures: ["usable draft rate >= 0.98"],
      constraints: ["human approval before notify"],
      riskTolerance: "low",
      preserveList: ["retrieval read-only authority"],
      confirmed: true,
    });

    const analyzed = await pipeline.runAnalysis(imported.organizationId);
    expect(analyzed.gapAnalysis).toBeTruthy();
    expect(
      (analyzed.candidates as { candidates: unknown[] }).candidates.length,
    ).toBeGreaterThanOrEqual(2);
    const rec = analyzed.recommendation as RecommendationResult;
    expect(rec.selectionStatus).toBe("BLOCKED_NO_ELIGIBLE_CANDIDATE");
    expect(rec.chosenCandidateId).toBeNull();

    await expect(
      pipeline.approveAndExport(imported.organizationId, "approved"),
    ).rejects.toThrow(/eligibility gate/i);
  });

  it("eligible fixture can complete approve/export", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "af-ws-"));
    dirs.push(dir);
    const pipeline = new BuilderPipeline(new JsonFileWorkspaceStore(dir));
    const imported = await pipeline.importFixture("eligible-org.yaml");
    await pipeline.updateIntent(imported.organizationId, {
      mission: "Reliable claims summarization under human governance",
      successMeasures: ["usable draft rate >= 0.98"],
      constraints: ["human approval before notify"],
      riskTolerance: "low",
      preserveList: ["retrieval read-only authority"],
      confirmed: true,
    });
    const analyzed = await pipeline.runAnalysis(imported.organizationId);
    const rec = analyzed.recommendation as RecommendationResult;
    expect(rec.selectionStatus).toBe("SELECTED");
    const exported = await pipeline.approveAndExport(
      imported.organizationId,
      "approved",
    );
    expect(exported.exports.length).toBe(1);
    expect(exported.exports[0].markdown).toContain("advisory-only");
    expect(exported.changeHistory[0].approvalState).toBe("exported");
    expect(exported.changeHistory[0].outcome).toMatch(/No deployment/);
  });
});
