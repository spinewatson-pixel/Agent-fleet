import type { Metrics, Threshold, ThresholdBreach } from "./types.js";

/**
 * Check declared thresholds against collected metrics.
 *
 * A threshold naming a metric the gate never produced is a breach, not a pass.
 * Silently skipping unknown metrics is how a gate quietly stops checking
 * anything at all.
 */
export function evaluateThresholds(
  thresholds: Threshold[] | undefined,
  metrics: Metrics,
): ThresholdBreach[] {
  if (!thresholds?.length) return [];
  const breaches: ThresholdBreach[] = [];

  for (const threshold of thresholds) {
    const actual = metrics[threshold.metric];
    if (actual === undefined) {
      breaches.push({
        threshold,
        actual: undefined,
        reason: `metric '${threshold.metric}' was not produced by this gate`,
      });
      continue;
    }
    if (typeof actual !== "number" || !Number.isFinite(actual)) {
      breaches.push({
        threshold,
        actual,
        reason: `metric '${threshold.metric}' is not numeric (got ${JSON.stringify(actual)})`,
      });
      continue;
    }
    if (!satisfies(actual, threshold)) {
      breaches.push({
        threshold,
        actual,
        reason: `${threshold.metric}=${actual} violates ${threshold.metric} ${symbol(
          threshold,
        )} ${threshold.value}`,
      });
    }
  }

  return breaches;
}

function satisfies(actual: number, threshold: Threshold): boolean {
  switch (threshold.operator) {
    case "gte":
      return actual >= threshold.value;
    case "lte":
      return actual <= threshold.value;
    case "eq":
      return actual === threshold.value;
    case "neq":
      return actual !== threshold.value;
    default: {
      const never: never = threshold.operator;
      throw new Error(`unknown threshold operator: ${String(never)}`);
    }
  }
}

function symbol(threshold: Threshold): string {
  switch (threshold.operator) {
    case "gte":
      return ">=";
    case "lte":
      return "<=";
    case "eq":
      return "==";
    case "neq":
      return "!=";
    default:
      return "?";
  }
}
