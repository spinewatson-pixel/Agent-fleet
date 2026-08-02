import fs from "node:fs";
import path from "node:path";
import type { Baseline, VerificationRun } from "./types.js";

/**
 * Where the comparison baseline lives.
 *
 * Baselines are committed (`verification/baselines/<project>.json`) so that a
 * fresh clone and CI compare against the same previous successful build a
 * developer does. Run history is local noise and stays out of the repository.
 */
export function defaultBaselineDir(rootDir: string): string {
  return path.resolve(rootDir, "verification", "baselines");
}

export function defaultHistoryDir(rootDir: string): string {
  return path.resolve(rootDir, ".verification", "runs");
}

export interface BaselineStore {
  read(projectId: string): Baseline | null;
  write(baseline: Baseline): void;
}

export class JsonBaselineStore implements BaselineStore {
  constructor(private readonly dir: string) {}

  read(projectId: string): Baseline | null {
    const file = this.file(projectId);
    if (!fs.existsSync(file)) return null;
    try {
      const parsed: unknown = JSON.parse(fs.readFileSync(file, "utf8"));
      return isBaseline(parsed) ? parsed : null;
    } catch {
      // A corrupt baseline must not be silently treated as "no regression".
      // Returning null surfaces it as a missing baseline instead.
      return null;
    }
  }

  write(baseline: Baseline): void {
    fs.mkdirSync(this.dir, { recursive: true });
    fs.writeFileSync(
      this.file(baseline.projectId),
      `${JSON.stringify(baseline, null, 2)}\n`,
      "utf8",
    );
  }

  private file(projectId: string): string {
    return path.join(this.dir, `${projectId}.json`);
  }
}

/** Only a build that is actually deployable may become the next baseline. */
export function baselineFromRun(run: VerificationRun): Baseline | null {
  if (run.verdict === "BLOCKED") return null;
  return {
    runId: run.runId,
    projectId: run.projectId,
    recordedAt: run.finishedAt,
    commit: run.commit,
    branch: run.branch,
    score: run.readiness.score,
    verdict: run.verdict,
    metrics: run.metrics,
  };
}

export function writeRunHistory(dir: string, run: VerificationRun): string {
  const target = path.join(dir, run.projectId);
  fs.mkdirSync(target, { recursive: true });
  const file = path.join(target, `${run.runId}.json`);
  fs.writeFileSync(file, `${JSON.stringify(run, null, 2)}\n`, "utf8");
  return file;
}

function isBaseline(value: unknown): value is Baseline {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<Baseline>;
  return (
    typeof candidate.runId === "string" &&
    typeof candidate.projectId === "string" &&
    typeof candidate.metrics === "object" &&
    candidate.metrics !== null
  );
}
