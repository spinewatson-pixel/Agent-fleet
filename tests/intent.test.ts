import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ReadOnlyDiscoveryAdapter } from "../src/core/adapters/readOnlyDiscoveryAdapter.js";
import { evaluateIntentCompleteness } from "../src/core/services/intentCompleteness.js";

describe("intent completeness", () => {
  it("emits unresolved questions and does not invent mission", async () => {
    const adapter = new ReadOnlyDiscoveryAdapter();
    const demo = fs.readFileSync(
      path.resolve(process.cwd(), "fixtures/demo-org.yaml"),
      "utf8",
    );
    const org = await adapter.normalize(
      await adapter.discover(demo, { format: "yaml" }),
    );
    const result = evaluateIntentCompleteness(org);
    expect(result.profile.mission).toBeUndefined();
    expect(result.unresolvedQuestions.length).toBeGreaterThan(0);
    expect(result.unresolvedQuestions.some((q) => q.toLowerCase().includes("mission"))).toBe(
      true,
    );
    expect(result.isComplete).toBe(false);
  });

  it("becomes complete only when owner supplies required fields", async () => {
    const adapter = new ReadOnlyDiscoveryAdapter();
    const demo = fs.readFileSync(
      path.resolve(process.cwd(), "fixtures/demo-org.yaml"),
      "utf8",
    );
    const org = await adapter.normalize(
      await adapter.discover(demo, { format: "yaml" }),
    );
    const result = evaluateIntentCompleteness(org, {
      mission: "Assist adjusters with reliable claim summaries",
      successMeasures: ["summary success rate >= 0.98"],
      constraints: ["human approval before notify"],
      riskTolerance: "low",
      preserveList: ["retrieval read-only authority"],
      confirmed: true,
    });
    expect(result.unresolvedQuestions).toEqual([]);
    expect(result.isComplete).toBe(true);
  });
});
