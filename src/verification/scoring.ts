import type {
  GateResult,
  GateStatus,
  ReadinessScore,
  ScoreBreakdownEntry,
} from "./types.js";

/**
 * What each outcome is worth. A warning is deliberately expensive: a build that
 * is warning everywhere should not score like a clean one.
 */
const STATUS_CREDIT: Record<GateStatus, number | null> = {
  pass: 1,
  warn: 0.6,
  fail: 0,
  // Skipped gates leave the denominator rather than counting as free credit.
  skip: null,
};

export function computeReadinessScore(results: GateResult[]): ReadinessScore {
  const breakdown: ScoreBreakdownEntry[] = [];
  let totalWeight = 0;
  let earnedWeight = 0;

  for (const result of results) {
    const credit = STATUS_CREDIT[result.status];
    const possible = credit === null ? 0 : result.weight;
    const earned = credit === null ? 0 : result.weight * credit;
    totalWeight += possible;
    earnedWeight += earned;
    breakdown.push({
      gateId: result.gateId,
      category: result.category,
      status: result.status,
      weight: result.weight,
      earned,
      possible,
    });
  }

  // No weighable gate ran at all. That is a zero, not a perfect score — the
  // absence of evidence must never round up.
  const score = totalWeight === 0 ? 0 : (earnedWeight / totalWeight) * 100;

  return {
    score: Math.round(score * 10) / 10,
    breakdown,
    totalWeight,
    earnedWeight: Math.round(earnedWeight * 1000) / 1000,
  };
}

/** Flatten gate metrics into the `<gateId>.<metric>` space used for regression. */
export function flattenMetrics(results: GateResult[]): Record<string, number> {
  const flat: Record<string, number> = {};
  for (const result of results) {
    for (const [key, value] of Object.entries(result.metrics)) {
      if (typeof value === "number" && Number.isFinite(value)) {
        flat[`${result.gateId}.${key}`] = value;
      }
    }
  }
  return flat;
}
