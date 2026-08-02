import path from "node:path";
import type { ProjectManifest } from "../types.js";

const ROOT = path.resolve(process.cwd());

/**
 * The Python agent stack. Every gate is a subcommand of
 * `ecosystem/verify_gates.py` that prints one JSON object, which is the entire
 * contract a non-JavaScript project has to satisfy to join the framework.
 */
export const nursingEcosystemManifest: ProjectManifest = {
  id: "nursing-ecosystem",
  name: "Nursing OS — study and agent stack",
  description:
    "Standard-library Python agent stack. Gates run the real chains against test doubles, so the wiring is verified without the claude CLI or the pre-existing backend.",
  rootDir: ROOT,
  gates: [
    {
      id: "build.compile",
      category: "build",
      description: "Every shipped module byte-compiles",
      command: "python3 ecosystem/verify_gates.py build",
      required: true,
      weight: 3,
      timeoutMs: 120_000,
      parser: { kind: "json" },
      thresholds: [
        { metric: "checks_failed", operator: "eq", value: 0, severity: "fail" },
        { metric: "modules_compiled", operator: "gte", value: 9, severity: "fail" },
      ],
    },
    {
      id: "deps.stdlib",
      category: "dependencies",
      description:
        "Standard library only — no pip installs, and external deps stay declared",
      command: "python3 ecosystem/verify_gates.py dependencies",
      required: true,
      weight: 3,
      timeoutMs: 120_000,
      parser: { kind: "json" },
      thresholds: [
        { metric: "third_party_imports", operator: "eq", value: 0, severity: "fail" },
        { metric: "checks_failed", operator: "eq", value: 0, severity: "fail" },
      ],
    },
    {
      id: "e2e.chains",
      category: "e2e",
      description:
        "Full simulation: foundations, textbook chain, intake, learner, org cycle, world sweep",
      command: "python3 ecosystem/verify_gates.py e2e",
      required: true,
      weight: 5,
      timeoutMs: 600_000,
      parser: { kind: "json" },
      thresholds: [
        { metric: "checks_failed", operator: "eq", value: 0, severity: "fail" },
        { metric: "chapter_words", operator: "gte", value: 900, severity: "fail" },
        { metric: "chapter_items", operator: "gte", value: 1, severity: "fail" },
        { metric: "cards_filed", operator: "gte", value: 1, severity: "fail" },
        { metric: "problems_triaged", operator: "gte", value: 1, severity: "fail" },
      ],
    },
    {
      id: "contracts.agentkit",
      category: "contracts",
      description:
        "The nine-rule agent contract: prompt placement, accumulating carry, no furniture, counted rank, no self-verification, UNCHECKED default",
      command: "python3 ecosystem/verify_gates.py contracts",
      required: true,
      weight: 5,
      timeoutMs: 300_000,
      parser: { kind: "json" },
      thresholds: [
        { metric: "checks_failed", operator: "eq", value: 0, severity: "fail" },
        { metric: "rules_checked", operator: "gte", value: 8, severity: "fail" },
      ],
    },
    {
      id: "governance.posture",
      category: "governance",
      description:
        "Nothing runs unattended, write/execute tools stay disallowed, guards present, capability unlocks are evidence counts",
      command: "python3 ecosystem/verify_gates.py governance",
      required: true,
      weight: 5,
      timeoutMs: 300_000,
      parser: { kind: "json" },
      thresholds: [
        { metric: "checks_failed", operator: "eq", value: 0, severity: "fail" },
        { metric: "unattended_findings", operator: "eq", value: 0, severity: "fail" },
        { metric: "roles_gated", operator: "gte", value: 1, severity: "fail" },
      ],
    },
    {
      id: "perf.chains",
      category: "performance",
      description: "Schema init, chapter chain latency and scoring throughput",
      command: "python3 ecosystem/verify_gates.py performance",
      required: true,
      weight: 2,
      timeoutMs: 300_000,
      parser: { kind: "json" },
      thresholds: [
        { metric: "checks_failed", operator: "eq", value: 0, severity: "fail" },
        { metric: "schema_init_ms", operator: "lte", value: 5_000, severity: "warn" },
        { metric: "score_ops_per_sec", operator: "gte", value: 500, severity: "warn" },
      ],
    },
  ],
  regressionRules: [
    {
      metric: "e2e.chains.checks_run",
      direction: "higher-is-better",
      tolerance: 0,
      severity: "fail",
      description: "the end-to-end simulation must never check less than it used to",
    },
    {
      metric: "contracts.agentkit.checks_run",
      direction: "higher-is-better",
      tolerance: 0,
      severity: "fail",
      description: "contract coverage must never shrink",
    },
    {
      metric: "governance.posture.checks_run",
      direction: "higher-is-better",
      tolerance: 0,
      severity: "fail",
      description: "governance coverage must never shrink",
    },
    {
      metric: "e2e.chains.chapter_score",
      direction: "higher-is-better",
      tolerance: 0.1,
      severity: "warn",
    },
    {
      metric: "perf.chains.score_ops_per_sec",
      direction: "higher-is-better",
      tolerance: 0.5,
      severity: "warn",
    },
    {
      metric: "perf.chains.chapter_chain_ms",
      direction: "lower-is-better",
      tolerance: 1.0,
      severity: "warn",
    },
    {
      metric: "deps.stdlib.third_party_imports",
      direction: "lower-is-better",
      tolerance: 0,
      severity: "fail",
      description: "a new third-party import is a release blocker for this stack",
    },
  ],
  policy: {
    minimumScore: 90,
    requireAllCategories: true,
    requireBaseline: false,
  },
};
