import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ReadOnlyDiscoveryAdapter } from "../src/core/adapters/readOnlyDiscoveryAdapter.js";
import { MutationRejectedError } from "../src/core/adapters/mutationGuard.js";

describe("ReadOnlyDiscoveryAdapter", () => {
  const adapter = new ReadOnlyDiscoveryAdapter();
  const demo = fs.readFileSync(
    path.resolve(process.cwd(), "fixtures/demo-org.yaml"),
    "utf8",
  );

  it("discovers, normalizes demo org into canonical model", async () => {
    const raw = await adapter.discover(demo, { format: "yaml", label: "demo" });
    const canonical = await adapter.normalize(raw);
    expect(canonical.organization.name).toBe("Contoso Claims Copilot");
    expect(canonical.workers.length).toBeGreaterThan(0);
    expect(canonical.evidence.some((e) => e.status === "observation")).toBe(true);
    expect(canonical.organization.mission).toBeUndefined();
  });

  it("validate flags seeded missing contract and approval gate", async () => {
    const raw = await adapter.discover(demo, { format: "yaml" });
    const canonical = await adapter.normalize(raw);
    const result = await adapter.validate(canonical);
    expect(result.gaps.some((g) => g.path.includes("contractSchema"))).toBe(true);
    expect(result.gaps.some((g) => g.path.includes("approvalGate"))).toBe(true);
    expect(result.unsupportedFeatures).toContain("live_mutation_apply");
  });

  it("apply always rejects mutation", async () => {
    await expect(adapter.apply({ any: "changeset" })).rejects.toBeInstanceOf(
      MutationRejectedError,
    );
  });
});
