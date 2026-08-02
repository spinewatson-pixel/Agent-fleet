import path from "node:path";
import type { ProjectManifest } from "../types.js";

const ROOT = path.resolve(process.cwd());

/**
 * The TypeScript control plane. Gates wrap the commands this project already
 * had — the framework's contribution is that they now run together, produce
 * metrics, and are compared against the last successful build.
 */
export const agentFleetManifest: ProjectManifest = {
  id: "agent-fleet",
  name: "Agent Fleet — advisory architecture control plane",
  description:
    "Read-only advisory MVP. Gates cover build, dependencies, end-to-end journey, contracts, governance posture and performance.",
  rootDir: ROOT,
  gates: [
    {
      id: "build.types",
      category: "build",
      description: "Strict TypeScript compiles for both API and web projects",
      command: "pnpm run typecheck",
      required: true,
      weight: 3,
      timeoutMs: 300_000,
    },
    {
      id: "build.lint",
      category: "build",
      description: "ESLint passes with no explicit any and no unused symbols",
      command: "pnpm run lint",
      required: true,
      weight: 2,
      timeoutMs: 300_000,
    },
    {
      id: "build.bundle",
      category: "build",
      description: "Production build emits the API bundle and the web assets",
      command: "pnpm run build",
      required: true,
      weight: 3,
      timeoutMs: 600_000,
      parser: {
        kind: "regex",
        patterns: {
          bundle_kb: String.raw`assets/index-[\w-]+\.js\s+([\d.]+)\s*kB`,
          gzip_kb: String.raw`assets/index-[\w-]+\.js.*gzip:\s*([\d.]+)\s*kB`,
        },
      },
      thresholds: [
        {
          metric: "bundle_kb",
          operator: "lte",
          value: 400,
          severity: "warn",
          description: "web bundle should stay well under 400 kB uncompressed",
        },
      ],
    },
    {
      id: "deps.lockfile",
      category: "dependencies",
      description: "Lockfile satisfies package.json exactly (frozen install)",
      command: "pnpm install --frozen-lockfile --prefer-offline",
      required: true,
      weight: 2,
      timeoutMs: 600_000,
    },
    {
      id: "deps.declared",
      category: "dependencies",
      description: "Every imported package is declared — no phantom dependencies",
      command: "pnpm exec tsx scripts/depcheck.ts",
      required: true,
      weight: 2,
      timeoutMs: 120_000,
      parser: { kind: "json" },
      thresholds: [
        { metric: "undeclared", operator: "eq", value: 0, severity: "fail" },
      ],
    },
    {
      id: "e2e.journey",
      category: "e2e",
      description: "HTTP journey: import → intent → analyze → eligibility → export",
      command: "pnpm run test:e2e",
      required: true,
      weight: 4,
      timeoutMs: 600_000,
      parser: {
        kind: "regex",
        patterns: { tests_passed: String.raw`Tests\s+(\d+) passed` },
      },
      thresholds: [
        { metric: "tests_passed", operator: "gte", value: 1, severity: "fail" },
      ],
    },
    {
      id: "contracts.schemas",
      category: "contracts",
      description: "Versioned schemas and intent completeness hold their shape",
      command: "pnpm exec vitest run tests/schemas.test.ts tests/intent.test.ts",
      required: true,
      weight: 3,
      timeoutMs: 300_000,
      parser: {
        kind: "regex",
        patterns: { tests_passed: String.raw`Tests\s+(\d+) passed` },
      },
      thresholds: [
        { metric: "tests_passed", operator: "gte", value: 5, severity: "fail" },
      ],
    },
    {
      id: "governance.advisory",
      category: "governance",
      description:
        "Mutation stays rejected and the eligibility gate still blocks invalid approval/export",
      command:
        "pnpm exec vitest run tests/eligibility.regression.test.ts tests/adapter.test.ts",
      required: true,
      weight: 4,
      timeoutMs: 300_000,
      parser: {
        kind: "regex",
        patterns: { tests_passed: String.raw`Tests\s+(\d+) passed` },
      },
      thresholds: [
        { metric: "tests_passed", operator: "gte", value: 8, severity: "fail" },
      ],
    },
    {
      id: "perf.suite",
      category: "performance",
      description: "Full unit + e2e suite runtime and test count",
      command: "pnpm test",
      required: true,
      weight: 2,
      timeoutMs: 900_000,
      parser: {
        kind: "regex",
        patterns: {
          tests_passed: String.raw`Tests\s+(\d+) passed`,
          test_files: String.raw`Test Files\s+(\d+) passed`,
        },
      },
      thresholds: [
        // A hard floor for clones with no baseline; the regression rule below is
        // what actually stops the suite shrinking build over build.
        { metric: "tests_passed", operator: "gte", value: 70, severity: "fail" },
        { metric: "duration_ms", operator: "lte", value: 300_000, severity: "warn" },
      ],
    },
  ],
  regressionRules: [
    {
      metric: "perf.suite.tests_passed",
      direction: "higher-is-better",
      tolerance: 0,
      severity: "fail",
      description: "the suite must never shrink between builds",
    },
    {
      metric: "governance.advisory.tests_passed",
      direction: "higher-is-better",
      tolerance: 0,
      severity: "fail",
      description: "governance coverage must never shrink",
    },
    {
      metric: "e2e.journey.tests_passed",
      direction: "higher-is-better",
      tolerance: 0,
      severity: "fail",
    },
    {
      metric: "build.bundle.bundle_kb",
      direction: "lower-is-better",
      tolerance: 0.15,
      severity: "warn",
      description: "bundle growth over 15% wants an explanation",
    },
    {
      metric: "perf.suite.duration_ms",
      direction: "lower-is-better",
      tolerance: 1.0,
      severity: "warn",
      description: "suite taking more than twice as long is a signal, not a failure",
    },
  ],
  policy: {
    minimumScore: 90,
    requireAllCategories: true,
    requireBaseline: false,
  },
};
