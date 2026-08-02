import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { GATE_CATEGORIES, validateManifest } from "../src/verification/index.js";
import { MANIFESTS, getManifest } from "../src/verification/manifests/index.js";

/**
 * Registry integrity. These are the tests that make the framework a standard
 * rather than a convention: a new ecosystem cannot be registered with a
 * half-declared manifest, because this fails first.
 */
describe("registered project manifests", () => {
  it("registers at least the two shipped ecosystems", () => {
    expect(MANIFESTS.length).toBeGreaterThanOrEqual(2);
    expect(getManifest("agent-fleet")).toBeDefined();
    expect(getManifest("nursing-ecosystem")).toBeDefined();
  });

  it("gives every project a unique id", () => {
    const ids = MANIFESTS.map((m) => m.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  for (const manifest of MANIFESTS) {
    describe(manifest.id, () => {
      it("is structurally valid", () => {
        expect(validateManifest(manifest)).toEqual([]);
      });

      it("covers every mandated category", () => {
        for (const category of GATE_CATEGORIES) {
          expect(
            manifest.gates.some((g) => g.category === category),
            `${manifest.id} has no ${category} gate`,
          ).toBe(true);
        }
      });

      it("declares regression rules so builds are compared, not just run", () => {
        expect(manifest.regressionRules.length).toBeGreaterThan(0);
      });

      it("holds every regression rule to a metric some gate can produce", () => {
        // Gate ids contain dots (`e2e.chains`), so match on the id prefix
        // rather than the first path segment.
        for (const rule of manifest.regressionRules) {
          const owner = manifest.gates.find((g) => rule.metric.startsWith(`${g.id}.`));
          expect(owner, `${rule.metric} names no known gate`).toBeDefined();
        }
      });

      it("sets a meaningful readiness bar", () => {
        expect(manifest.policy.minimumScore).toBeGreaterThanOrEqual(50);
        expect(manifest.policy.requireAllCategories).toBe(true);
      });

      it("makes the safety-critical categories required", () => {
        for (const category of ["e2e", "contracts", "governance"] as const) {
          const gates = manifest.gates.filter((g) => g.category === category);
          expect(gates.some((g) => g.required), `${category} must have a required gate`).toBe(
            true,
          );
        }
      });
    });
  }
});

describe("committed baselines", () => {
  const dir = path.resolve(process.cwd(), "verification", "baselines");

  it("stores a baseline per project so regression can run on a fresh clone", () => {
    for (const manifest of MANIFESTS) {
      const file = path.join(dir, `${manifest.id}.json`);
      expect(fs.existsSync(file), `missing baseline for ${manifest.id}`).toBe(true);
    }
  });

  it("never records a blocked build as a baseline", () => {
    for (const manifest of MANIFESTS) {
      const file = path.join(dir, `${manifest.id}.json`);
      if (!fs.existsSync(file)) continue;
      const baseline = JSON.parse(fs.readFileSync(file, "utf8")) as {
        verdict: string;
        metrics: Record<string, number>;
      };
      expect(baseline.verdict).not.toBe("BLOCKED");
      expect(Object.keys(baseline.metrics).length).toBeGreaterThan(0);
    }
  });
});
