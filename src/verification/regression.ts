import type {
  Baseline,
  RegressionFinding,
  RegressionReport,
  RegressionRule,
} from "./types.js";

/**
 * Compare this build's metrics against the last successful build.
 *
 * Three cases are treated differently on purpose:
 *   - metric present on both sides   → compared against the rule's tolerance
 *   - metric missing from the CURRENT run but present in the baseline → a
 *     regression in its own right, because a gate silently stopped reporting
 *   - metric missing from the BASELINE → nothing to compare; recorded, not held
 *     against the build, since new metrics must be able to appear
 */
export function compareToBaseline(
  current: Record<string, number>,
  baseline: Baseline | null,
  rules: RegressionRule[],
): RegressionReport {
  if (!baseline) {
    return {
      baselineRunId: null,
      baselineCommit: null,
      comparedMetrics: 0,
      findings: [],
      failures: [],
      warnings: [],
      unmatchedRules: rules.map((r) => r.metric),
    };
  }

  const findings: RegressionFinding[] = [];
  const unmatchedRules: string[] = [];

  for (const rule of rules) {
    const before = baseline.metrics[rule.metric];
    const after = current[rule.metric];

    if (before === undefined) {
      unmatchedRules.push(rule.metric);
      continue;
    }
    if (after === undefined) {
      findings.push({
        rule,
        baselineValue: before,
        currentValue: Number.NaN,
        changeRatio: Number.NaN,
        regressed: true,
        reason: `${rule.metric} was reported by the previous successful build but is absent now — the gate producing it stopped reporting`,
      });
      continue;
    }

    const changeRatio = relativeChange(before, after);
    const regressed = isRegression(rule, before, after, changeRatio);
    findings.push({
      rule,
      baselineValue: before,
      currentValue: after,
      changeRatio,
      regressed,
      reason: regressed
        ? `${rule.metric} moved ${describe(rule.direction)} from ${before} to ${after}` +
          ` (${formatPercent(changeRatio)}, tolerance ${formatPercent(rule.tolerance)})`
        : `${rule.metric} ${before} → ${after} within tolerance`,
    });
  }

  const regressions = findings.filter((f) => f.regressed);
  return {
    baselineRunId: baseline.runId,
    baselineCommit: baseline.commit,
    comparedMetrics: findings.length,
    findings,
    failures: regressions.filter((f) => f.rule.severity === "fail"),
    warnings: regressions.filter((f) => f.rule.severity === "warn"),
    unmatchedRules,
  };
}

function relativeChange(before: number, after: number): number {
  if (before === after) return 0;
  if (before === 0) return after > 0 ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY;
  return (after - before) / Math.abs(before);
}

function isRegression(
  rule: RegressionRule,
  before: number,
  after: number,
  changeRatio: number,
): boolean {
  const tolerance = Math.max(0, rule.tolerance);
  if (rule.direction === "higher-is-better") {
    if (after >= before) return false;
    return -changeRatio > tolerance;
  }
  if (after <= before) return false;
  return changeRatio > tolerance;
}

function describe(direction: RegressionRule["direction"]): string {
  return direction === "higher-is-better" ? "down" : "up";
}

function formatPercent(ratio: number): string {
  if (!Number.isFinite(ratio)) return ratio > 0 ? "+∞" : "-∞";
  const pct = ratio * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}
