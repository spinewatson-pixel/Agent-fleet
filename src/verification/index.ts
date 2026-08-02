import { execFileSync } from "node:child_process";
import { compareToBaseline } from "./regression.js";
import { computeReadinessScore, flattenMetrics } from "./scoring.js";
import { runGates, type RunGateOptions } from "./runner.js";
import { decideVerdict } from "./verdict.js";
import type { BaselineStore } from "./baseline.js";
import type { GateResult, ProjectManifest, VerificationRun } from "./types.js";

export * from "./types.js";
export { parseGateOutput, lastJsonObject } from "./parsers.js";
export { evaluateThresholds } from "./thresholds.js";
export { runGate, runGates } from "./runner.js";
export { computeReadinessScore, flattenMetrics } from "./scoring.js";
export { compareToBaseline } from "./regression.js";
export { decideVerdict, validateManifest } from "./verdict.js";
export {
  JsonBaselineStore,
  baselineFromRun,
  defaultBaselineDir,
  defaultHistoryDir,
  writeRunHistory,
  type BaselineStore,
} from "./baseline.js";
export { renderConsole, renderMarkdown } from "./report.js";

export interface RunVerificationOptions {
  manifest: ProjectManifest;
  baselineStore: BaselineStore;
  execute?: RunGateOptions["execute"];
  onGateStart?: RunGateOptions["onGateStart"];
  onGateFinish?: RunGateOptions["onGateFinish"];
  /** Restrict the run to specific gate ids; the manifest check still applies. */
  only?: string[];
  now?: () => Date;
}

/**
 * One full verification pass: run every gate, score it, compare it to the last
 * successful build, and decide whether deployment may proceed.
 *
 * The function never throws for a failing build — a blocked build is a normal
 * outcome that must be reported, not an exception that loses the report.
 */
export async function runVerification(
  options: RunVerificationOptions,
): Promise<VerificationRun> {
  const { manifest } = options;
  const now = options.now ?? (() => new Date());
  const startedAt = now();
  const runId = makeRunId(startedAt);

  const selected = options.only?.length
    ? manifest.gates.filter((g) => options.only?.includes(g.id))
    : manifest.gates;

  // A manifest that cannot be trusted still runs its gates, so the report shows
  // both the structural problem and whatever evidence does exist. decideVerdict
  // re-checks the manifest and turns any problem into a block reason.
  const gateResults: GateResult[] = await runGates(selected, {
    rootDir: manifest.rootDir,
    execute: options.execute,
    onGateStart: options.onGateStart,
    onGateFinish: options.onGateFinish,
  });

  const metrics = flattenMetrics(gateResults);
  const baseline = options.baselineStore.read(manifest.id);
  const regression = compareToBaseline(metrics, baseline, manifest.regressionRules);
  const readiness = computeReadinessScore(gateResults);

  const { verdict, blockReasons, warnings } = decideVerdict({
    manifest,
    results: gateResults,
    regression,
    readiness,
    hasBaseline: baseline !== null,
  });

  const finishedAt = now();
  const git = readGitContext(manifest.rootDir);

  return {
    runId,
    projectId: manifest.id,
    projectName: manifest.name,
    startedAt: startedAt.toISOString(),
    finishedAt: finishedAt.toISOString(),
    durationMs: finishedAt.getTime() - startedAt.getTime(),
    commit: git.commit,
    branch: git.branch,
    gateResults,
    regression,
    readiness,
    verdict,
    blockReasons,
    warnings: [
      ...warnings,
      ...(options.only?.length
        ? [
            `partial run: only ${options.only.join(", ")} executed — not a deployment-grade verification`,
          ]
        : []),
    ],
    metrics,
  };
}

function makeRunId(at: Date): string {
  const stamp = at.toISOString().replace(/[:.]/g, "-");
  const suffix = Math.random().toString(36).slice(2, 6);
  return `${stamp}-${suffix}`;
}

function readGitContext(cwd: string): { commit: string | null; branch: string | null } {
  return {
    commit: gitCommand(cwd, ["rev-parse", "HEAD"]),
    branch: gitCommand(cwd, ["rev-parse", "--abbrev-ref", "HEAD"]),
  };
}

function gitCommand(cwd: string, args: string[]): string | null {
  try {
    return execFileSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] })
      .trim();
  } catch {
    return null;
  }
}
