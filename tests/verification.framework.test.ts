import { describe, expect, it } from "vitest";
import {
  compareToBaseline,
  computeReadinessScore,
  decideVerdict,
  evaluateThresholds,
  flattenMetrics,
  lastJsonObject,
  parseGateOutput,
  runGate,
  validateManifest,
} from "../src/verification/index.js";
import type {
  Baseline,
  GateResult,
  GateSpec,
  ProjectManifest,
  RegressionRule,
} from "../src/verification/index.js";

function gateResult(over: Partial<GateResult> = {}): GateResult {
  return {
    gateId: "g",
    category: "build",
    description: "d",
    required: true,
    weight: 1,
    status: "pass",
    durationMs: 1,
    exitCode: 0,
    reasons: [],
    metrics: {},
    breaches: [],
    evidence: "",
    timedOut: false,
    ...over,
  };
}

function spec(over: Partial<GateSpec> = {}): GateSpec {
  return {
    id: "gate",
    category: "build",
    description: "d",
    command: "true",
    required: true,
    weight: 1,
    ...over,
  };
}

function manifest(over: Partial<ProjectManifest> = {}): ProjectManifest {
  const gates: GateSpec[] = [
    spec({ id: "b", category: "build" }),
    spec({ id: "d", category: "dependencies" }),
    spec({ id: "e", category: "e2e" }),
    spec({ id: "c", category: "contracts" }),
    spec({ id: "g", category: "governance" }),
    spec({ id: "p", category: "performance" }),
  ];
  return {
    id: "proj",
    name: "Proj",
    description: "",
    rootDir: process.cwd(),
    gates,
    regressionRules: [],
    policy: { minimumScore: 90, requireAllCategories: true, requireBaseline: false },
    ...over,
  };
}

describe("gate execution never turns a broken gate into a pass", () => {
  it("a non-zero exit is a failure", async () => {
    const result = await runGate(spec(), {
      rootDir: process.cwd(),
      execute: async () => ({ stdout: "", stderr: "boom", exitCode: 1, timedOut: false }),
    });
    expect(result.status).toBe("fail");
    expect(result.reasons.join(" ")).toContain("exited with code 1");
  });

  it("a timeout is a failure", async () => {
    const result = await runGate(spec({ timeoutMs: 10 }), {
      rootDir: process.cwd(),
      execute: async () => ({ stdout: "", stderr: "", exitCode: null, timedOut: true }),
    });
    expect(result.status).toBe("fail");
    expect(result.reasons.join(" ")).toMatch(/timed out/);
  });

  it("a gate that cannot be executed at all is a failure", async () => {
    const result = await runGate(spec(), {
      rootDir: process.cwd(),
      execute: async () => {
        throw new Error("spawn failed");
      },
    });
    expect(result.status).toBe("fail");
  });

  it("unparseable output is a failure even when the command exits 0", async () => {
    const result = await runGate(spec({ parser: { kind: "json" } }), {
      rootDir: process.cwd(),
      execute: async () => ({
        stdout: "everything is fine, trust me",
        stderr: "",
        exitCode: 0,
        timedOut: false,
      }),
    });
    expect(result.status).toBe("fail");
    expect(result.reasons.join(" ")).toContain("JSON");
  });

  it("a gate may downgrade itself but never upgrade itself", async () => {
    const claimsPass = await runGate(spec({ parser: { kind: "json" } }), {
      rootDir: process.cwd(),
      execute: async () => ({
        stdout: JSON.stringify({ status: "pass", metrics: { n: 1 } }),
        stderr: "",
        exitCode: 1,
        timedOut: false,
      }),
    });
    expect(claimsPass.status).toBe("fail");

    const claimsWarn = await runGate(spec({ parser: { kind: "json" } }), {
      rootDir: process.cwd(),
      execute: async () => ({
        stdout: JSON.stringify({ status: "warn", metrics: {} }),
        stderr: "",
        exitCode: 0,
        timedOut: false,
      }),
    });
    expect(claimsWarn.status).toBe("warn");
  });

  it("a required gate that reports skip is a failure", async () => {
    const result = await runGate(spec({ required: true, parser: { kind: "json" } }), {
      rootDir: process.cwd(),
      execute: async () => ({
        stdout: JSON.stringify({ status: "skip" }),
        stderr: "",
        exitCode: 0,
        timedOut: false,
      }),
    });
    expect(result.status).toBe("fail");
    expect(result.reasons.join(" ")).toContain("must actually run");
  });

  it("records duration as a metric so performance is always collected", async () => {
    const result = await runGate(spec(), {
      rootDir: process.cwd(),
      execute: async () => ({ stdout: "", stderr: "", exitCode: 0, timedOut: false }),
    });
    expect(typeof result.metrics.duration_ms).toBe("number");
  });
});

describe("thresholds", () => {
  it("treats a missing metric as a breach rather than a pass", () => {
    const breaches = evaluateThresholds(
      [{ metric: "coverage", operator: "gte", value: 80, severity: "fail" }],
      {},
    );
    expect(breaches).toHaveLength(1);
    expect(breaches[0].reason).toContain("not produced");
  });

  it("treats a non-numeric metric as a breach", () => {
    const breaches = evaluateThresholds(
      [{ metric: "coverage", operator: "gte", value: 80, severity: "fail" }],
      { coverage: "high" },
    );
    expect(breaches[0].reason).toContain("not numeric");
  });

  it("passes a satisfied threshold", () => {
    expect(
      evaluateThresholds(
        [{ metric: "coverage", operator: "gte", value: 80, severity: "fail" }],
        { coverage: 81 },
      ),
    ).toHaveLength(0);
  });
});

describe("parsers", () => {
  it("takes the last JSON object so a command may log before it", () => {
    const found = lastJsonObject('noise {"a":1} more {"b":{"c":2}} tail');
    expect(found).toBe('{"b":{"c":2}}');
  });

  it("ignores braces inside strings", () => {
    expect(lastJsonObject('{"a":"} not the end"}')).toBe('{"a":"} not the end"}');
  });

  it("reports missing regex captures instead of silently returning nothing", () => {
    const parsed = parseGateOutput(
      { kind: "regex", patterns: { tests: "Tests\\s+(\\d+) passed" } },
      { stdout: "no test summary here", stderr: "", exitCode: 0, timedOut: false },
    );
    expect(parsed.parseError).toContain("tests");
  });

  it("extracts numeric metrics from regex captures", () => {
    const parsed = parseGateOutput(
      { kind: "regex", patterns: { tests: "Tests\\s+(\\d+) passed" } },
      { stdout: "  Tests  22 passed (22)", stderr: "", exitCode: 0, timedOut: false },
    );
    expect(parsed.metrics.tests).toBe(22);
  });
});

describe("readiness scoring", () => {
  it("weights gates and charges for warnings", () => {
    const score = computeReadinessScore([
      gateResult({ gateId: "a", weight: 3, status: "pass" }),
      gateResult({ gateId: "b", weight: 1, status: "warn" }),
    ]);
    expect(score.score).toBe(90);
  });

  it("scores a failed gate at zero rather than skipping it", () => {
    const score = computeReadinessScore([
      gateResult({ gateId: "a", weight: 1, status: "pass" }),
      gateResult({ gateId: "b", weight: 1, status: "fail" }),
    ]);
    expect(score.score).toBe(50);
  });

  it("scores zero when nothing weighable ran — absence never rounds up", () => {
    expect(computeReadinessScore([]).score).toBe(0);
    expect(computeReadinessScore([gateResult({ status: "skip" })]).score).toBe(0);
  });

  it("namespaces metrics by gate id", () => {
    const flat = flattenMetrics([
      gateResult({ gateId: "e2e", metrics: { tests: 3, label: "x" } }),
    ]);
    expect(flat["e2e.tests"]).toBe(3);
    expect(flat["e2e.label"]).toBeUndefined();
  });
});

describe("regression against the previous successful build", () => {
  const baseline: Baseline = {
    runId: "run-1",
    projectId: "proj",
    recordedAt: "2026-01-01T00:00:00.000Z",
    commit: "abc",
    branch: "main",
    score: 100,
    verdict: "READY",
    metrics: { "suite.tests": 22, "build.bundle_kb": 100 },
  };

  const rules: RegressionRule[] = [
    { metric: "suite.tests", direction: "higher-is-better", tolerance: 0, severity: "fail" },
    { metric: "build.bundle_kb", direction: "lower-is-better", tolerance: 0.15, severity: "warn" },
  ];

  it("flags a shrinking test suite as a blocking regression", () => {
    const report = compareToBaseline({ "suite.tests": 21, "build.bundle_kb": 100 }, baseline, rules);
    expect(report.failures).toHaveLength(1);
    expect(report.failures[0].reason).toContain("22 to 21");
  });

  it("accepts growth on a higher-is-better metric", () => {
    const report = compareToBaseline({ "suite.tests": 30, "build.bundle_kb": 100 }, baseline, rules);
    expect(report.failures).toHaveLength(0);
  });

  it("allows drift inside tolerance and flags drift beyond it", () => {
    const inside = compareToBaseline(
      { "suite.tests": 22, "build.bundle_kb": 110 },
      baseline,
      rules,
    );
    expect(inside.warnings).toHaveLength(0);

    const outside = compareToBaseline(
      { "suite.tests": 22, "build.bundle_kb": 130 },
      baseline,
      rules,
    );
    expect(outside.warnings).toHaveLength(1);
  });

  it("treats a metric that stopped being reported as a regression", () => {
    const report = compareToBaseline({ "build.bundle_kb": 100 }, baseline, rules);
    expect(report.failures).toHaveLength(1);
    expect(report.failures[0].reason).toContain("absent now");
  });

  it("does not punish a metric the baseline never had", () => {
    const report = compareToBaseline(
      { "suite.tests": 22, "build.bundle_kb": 100, "new.metric": 5 },
      baseline,
      [
        ...rules,
        { metric: "new.metric", direction: "higher-is-better", tolerance: 0, severity: "fail" },
      ],
    );
    expect(report.failures).toHaveLength(0);
    expect(report.unmatchedRules).toContain("new.metric");
  });

  it("reports no comparison when there is no baseline at all", () => {
    const report = compareToBaseline({ "suite.tests": 22 }, null, rules);
    expect(report.baselineRunId).toBeNull();
    expect(report.comparedMetrics).toBe(0);
  });
});

describe("manifest validation", () => {
  it("rejects a manifest missing a mandated category", () => {
    const incomplete = manifest({
      gates: [spec({ id: "b", category: "build" })],
    });
    const problems = validateManifest(incomplete);
    const missing = problems.filter((p) => p.code === "missing_category");
    expect(missing.length).toBe(5);
    expect(missing.map((p) => p.detail).join(" ")).toContain("e2e");
  });

  it("rejects a gate with no command — it cannot verify anything", () => {
    const broken = manifest();
    broken.gates[0] = { ...broken.gates[0], command: undefined };
    expect(validateManifest(broken).some((p) => p.detail.includes("no command"))).toBe(true);
  });

  it("rejects duplicate gate ids", () => {
    const dupes = manifest();
    dupes.gates[1] = { ...dupes.gates[1], id: dupes.gates[0].id };
    expect(validateManifest(dupes).some((p) => p.detail.includes("duplicate"))).toBe(true);
  });

  it("accepts a complete manifest", () => {
    expect(validateManifest(manifest())).toHaveLength(0);
  });
});

describe("deployment verdict", () => {
  const clean = () =>
    manifest().gates.map((g) =>
      gateResult({ gateId: g.id, category: g.category, required: g.required, weight: g.weight }),
    );

  const emptyRegression = compareToBaseline({}, null, []);

  it("is READY when everything passes and there is nothing to warn about", () => {
    const results = clean();
    const out = decideVerdict({
      manifest: manifest(),
      results,
      regression: { ...emptyRegression, unmatchedRules: [] },
      readiness: computeReadinessScore(results),
      hasBaseline: true,
    });
    expect(out.verdict).toBe("READY");
    expect(out.blockReasons).toHaveLength(0);
  });

  it("BLOCKS when a required gate fails, whatever the score says", () => {
    const results = clean();
    results[0] = { ...results[0], status: "fail", reasons: ["compiler exploded"] };
    const out = decideVerdict({
      manifest: manifest({ policy: { minimumScore: 0, requireAllCategories: true, requireBaseline: false } }),
      results,
      regression: emptyRegression,
      readiness: computeReadinessScore(results),
      hasBaseline: true,
    });
    expect(out.verdict).toBe("BLOCKED");
    expect(out.blockReasons[0].code).toBe("required_gate_failed");
    expect(out.blockReasons[0].detail).toContain("compiler exploded");
  });

  it("does not block on an optional gate, but does warn", () => {
    const results = clean();
    results[0] = { ...results[0], status: "fail", required: false, reasons: ["flaky"] };
    const out = decideVerdict({
      manifest: manifest({ policy: { minimumScore: 0, requireAllCategories: true, requireBaseline: false } }),
      results,
      regression: emptyRegression,
      readiness: computeReadinessScore(results),
      hasBaseline: true,
    });
    expect(out.verdict).toBe("READY_WITH_WARNINGS");
  });

  it("BLOCKS on a failing regression even when every gate passed", () => {
    const results = clean();
    const regression = compareToBaseline(
      { "suite.tests": 10 },
      {
        runId: "r",
        projectId: "proj",
        recordedAt: "",
        commit: null,
        branch: null,
        score: 100,
        verdict: "READY",
        metrics: { "suite.tests": 22 },
      },
      [{ metric: "suite.tests", direction: "higher-is-better", tolerance: 0, severity: "fail" }],
    );
    const out = decideVerdict({
      manifest: manifest({ policy: { minimumScore: 0, requireAllCategories: true, requireBaseline: false } }),
      results,
      regression,
      readiness: computeReadinessScore(results),
      hasBaseline: true,
    });
    expect(out.verdict).toBe("BLOCKED");
    expect(out.blockReasons.some((r) => r.code === "regression_failure")).toBe(true);
  });

  it("BLOCKS when the score is below the policy minimum", () => {
    const results = clean();
    results[0] = { ...results[0], status: "warn", required: true, reasons: ["slow"] };
    const out = decideVerdict({
      manifest: manifest({ policy: { minimumScore: 100, requireAllCategories: true, requireBaseline: false } }),
      results,
      regression: emptyRegression,
      readiness: computeReadinessScore(results),
      hasBaseline: true,
    });
    expect(out.verdict).toBe("BLOCKED");
    expect(out.blockReasons.some((r) => r.code === "score_below_minimum")).toBe(true);
  });

  it("BLOCKS a manifest that forgot a category, even with a perfect score", () => {
    const incomplete = manifest({ gates: [spec({ id: "b", category: "build" })] });
    const results = [gateResult({ gateId: "b", category: "build" })];
    const out = decideVerdict({
      manifest: incomplete,
      results,
      regression: emptyRegression,
      readiness: computeReadinessScore(results),
      hasBaseline: true,
    });
    expect(out.verdict).toBe("BLOCKED");
    expect(computeReadinessScore(results).score).toBe(100);
    expect(out.blockReasons.some((r) => r.code === "missing_category")).toBe(true);
  });

  it("BLOCKS on a missing baseline only when the policy demands one", () => {
    const results = clean();
    const strict = decideVerdict({
      manifest: manifest({ policy: { minimumScore: 0, requireAllCategories: true, requireBaseline: true } }),
      results,
      regression: emptyRegression,
      readiness: computeReadinessScore(results),
      hasBaseline: false,
    });
    expect(strict.verdict).toBe("BLOCKED");

    const lenient = decideVerdict({
      manifest: manifest({ policy: { minimumScore: 0, requireAllCategories: true, requireBaseline: false } }),
      results,
      regression: emptyRegression,
      readiness: computeReadinessScore(results),
      hasBaseline: false,
    });
    expect(lenient.verdict).toBe("READY_WITH_WARNINGS");
  });
});
