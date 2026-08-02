import type { GateStatus, Metrics, MetricValue, ParserSpec } from "./types.js";

export interface RawGateOutput {
  stdout: string;
  stderr: string;
  exitCode: number | null;
  timedOut: boolean;
}

export interface ParsedGateOutput {
  metrics: Metrics;
  /** A parser may assert a status; the runner still applies the exit code rule. */
  statusHint?: GateStatus;
  /** Why parsing failed, when it did. An unparseable gate is never a pass. */
  parseError?: string;
}

/**
 * Turn gate output into metrics.
 *
 * Any language can plug into the framework by printing a JSON object — that is
 * the whole contract for a non-JavaScript project.
 */
export function parseGateOutput(
  spec: ParserSpec | undefined,
  raw: RawGateOutput,
): ParsedGateOutput {
  const parser: ParserSpec = spec ?? { kind: "exitCode" };
  switch (parser.kind) {
    case "exitCode":
      return { metrics: {} };
    case "json":
      return parseJson(raw);
    case "regex":
      return parseRegex(parser.patterns, raw);
    default: {
      // Exhaustiveness: an unknown parser must not silently succeed.
      const never: never = parser;
      return { metrics: {}, parseError: `unknown parser: ${JSON.stringify(never)}` };
    }
  }
}

function parseJson(raw: RawGateOutput): ParsedGateOutput {
  const block = lastJsonObject(raw.stdout);
  if (!block) {
    return { metrics: {}, parseError: "expected a JSON object on stdout, found none" };
  }
  let value: unknown;
  try {
    value = JSON.parse(block);
  } catch (err) {
    return {
      metrics: {},
      parseError: `stdout JSON did not parse: ${(err as Error).message}`,
    };
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return { metrics: {}, parseError: "expected a JSON object, got a non-object" };
  }
  const record = value as Record<string, unknown>;
  const metrics: Metrics = {};
  const rawMetrics = record.metrics;
  if (typeof rawMetrics === "object" && rawMetrics !== null && !Array.isArray(rawMetrics)) {
    for (const [key, val] of Object.entries(rawMetrics as Record<string, unknown>)) {
      if (isMetricValue(val)) metrics[key] = val;
    }
  }
  const statusHint = isGateStatus(record.status) ? record.status : undefined;
  return { metrics, statusHint };
}

function parseRegex(
  patterns: Record<string, string>,
  raw: RawGateOutput,
): ParsedGateOutput {
  const haystack = `${raw.stdout}\n${raw.stderr}`;
  const metrics: Metrics = {};
  const missing: string[] = [];
  for (const [name, source] of Object.entries(patterns)) {
    const match = new RegExp(source, "m").exec(haystack);
    const captured = match?.[1];
    if (captured === undefined) {
      missing.push(name);
      continue;
    }
    const numeric = Number(captured.replace(/,/g, ""));
    metrics[name] = Number.isFinite(numeric) ? numeric : captured;
  }
  return {
    metrics,
    parseError: missing.length
      ? `output did not contain expected values: ${missing.join(", ")}`
      : undefined,
  };
}

/** Scan for the last balanced `{...}` so a command may log freely before its JSON. */
export function lastJsonObject(text: string): string | null {
  let depth = 0;
  let start = -1;
  let last: string | null = null;
  let inString = false;
  let escaped = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') {
      inString = true;
      continue;
    }
    if (ch === "{") {
      if (depth === 0) start = i;
      depth += 1;
    } else if (ch === "}" && depth > 0) {
      depth -= 1;
      if (depth === 0 && start >= 0) last = text.slice(start, i + 1);
    }
  }
  return last;
}

function isMetricValue(value: unknown): value is MetricValue {
  return (
    typeof value === "number" || typeof value === "string" || typeof value === "boolean"
  );
}

function isGateStatus(value: unknown): value is GateStatus {
  return value === "pass" || value === "warn" || value === "fail" || value === "skip";
}
