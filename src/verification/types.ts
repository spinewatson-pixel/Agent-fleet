/**
 * Reusable build verification framework — shared vocabulary.
 *
 * The framework exists so that verification is a property of the build rather
 * than something a developer remembers to do. A project declares a manifest;
 * the runner executes every gate, scores the result, compares it against the
 * last successful build, and blocks deployment when a required gate fails.
 *
 * Two invariants are deliberately baked into the types:
 *   1. A gate that errors, times out, or cannot be parsed is `fail` — never
 *      `pass`. Absence of evidence is not evidence of health.
 *   2. Every mandated category must be covered by a manifest. A project that
 *      simply forgets to declare an end-to-end gate is not "passing"; its
 *      manifest is incomplete and the run is blocked.
 */

/** The mandated verification categories. Every manifest must cover the executable ones. */
export const GATE_CATEGORIES = [
  "build",
  "dependencies",
  "e2e",
  "contracts",
  "governance",
  "performance",
] as const;

export type GateCategory = (typeof GATE_CATEGORIES)[number];

/** Categories the framework derives itself rather than executing as commands. */
export const DERIVED_CATEGORIES = ["regression", "readiness"] as const;
export type DerivedCategory = (typeof DERIVED_CATEGORIES)[number];

export type GateStatus = "pass" | "warn" | "fail" | "skip";

export type MetricValue = number | string | boolean;
export type Metrics = Record<string, MetricValue>;

/** How a gate's stdout becomes structured metrics. */
export type ParserSpec =
  | { kind: "exitCode" }
  | { kind: "json" }
  | { kind: "regex"; patterns: Record<string, string> };

export type ThresholdOperator = "gte" | "lte" | "eq" | "neq";

export interface Threshold {
  metric: string;
  operator: ThresholdOperator;
  value: number;
  /** `fail` blocks a required gate; `warn` only costs score. */
  severity: "fail" | "warn";
  description?: string;
}

export interface GateSpec {
  id: string;
  category: GateCategory;
  description: string;
  /** Shell command. Omitted only for gates supplied programmatically in tests. */
  command?: string;
  cwd?: string;
  env?: Record<string, string>;
  timeoutMs?: number;
  /** A required gate that fails blocks deployment outright. */
  required: boolean;
  /** Relative contribution to the readiness score. */
  weight: number;
  parser?: ParserSpec;
  thresholds?: Threshold[];
}

export type RegressionDirection = "higher-is-better" | "lower-is-better";

export interface RegressionRule {
  /** Namespaced metric key: `<gateId>.<metric>`. */
  metric: string;
  direction: RegressionDirection;
  /**
   * Relative slack before a move counts as a regression. `0` means any move in
   * the wrong direction is a regression; `0.25` allows a 25% drift.
   */
  tolerance: number;
  severity: "fail" | "warn";
  description?: string;
}

export interface ReadinessPolicy {
  /** Score below this blocks deployment even when every gate technically passed. */
  minimumScore: number;
  /** Blocks when a required gate is missing a result at all. */
  requireAllCategories: boolean;
  /** Blocks when the baseline is absent (use for release branches). */
  requireBaseline: boolean;
}

export interface ProjectManifest {
  id: string;
  name: string;
  description: string;
  /** Interpreter of relative gate cwd values. */
  rootDir: string;
  gates: GateSpec[];
  regressionRules: RegressionRule[];
  policy: ReadinessPolicy;
}

export interface ThresholdBreach {
  threshold: Threshold;
  actual: MetricValue | undefined;
  reason: string;
}

export interface GateResult {
  gateId: string;
  category: GateCategory;
  description: string;
  required: boolean;
  weight: number;
  status: GateStatus;
  durationMs: number;
  exitCode: number | null;
  /** Human-readable cause when the gate did not pass. */
  reasons: string[];
  metrics: Metrics;
  breaches: ThresholdBreach[];
  /** Trimmed output kept as evidence for the report. */
  evidence: string;
  timedOut: boolean;
}

export interface RegressionFinding {
  rule: RegressionRule;
  baselineValue: number;
  currentValue: number;
  /** Signed relative change, positive meaning the metric grew. */
  changeRatio: number;
  regressed: boolean;
  reason: string;
}

export interface RegressionReport {
  /** Null when no successful baseline exists yet. */
  baselineRunId: string | null;
  baselineCommit: string | null;
  comparedMetrics: number;
  findings: RegressionFinding[];
  failures: RegressionFinding[];
  warnings: RegressionFinding[];
  /** Metrics named by a rule but absent from either side. */
  unmatchedRules: string[];
}

export interface ScoreBreakdownEntry {
  gateId: string;
  category: GateCategory;
  status: GateStatus;
  weight: number;
  /** Score contribution before normalization. */
  earned: number;
  possible: number;
}

export interface ReadinessScore {
  /** 0-100. */
  score: number;
  breakdown: ScoreBreakdownEntry[];
  totalWeight: number;
  earnedWeight: number;
}

export type DeploymentVerdict = "READY" | "READY_WITH_WARNINGS" | "BLOCKED";

export interface BlockReason {
  code:
    | "required_gate_failed"
    | "missing_category"
    | "regression_failure"
    | "score_below_minimum"
    | "baseline_missing"
    | "manifest_invalid";
  detail: string;
}

export interface VerificationRun {
  runId: string;
  projectId: string;
  projectName: string;
  startedAt: string;
  finishedAt: string;
  durationMs: number;
  commit: string | null;
  branch: string | null;
  gateResults: GateResult[];
  regression: RegressionReport;
  readiness: ReadinessScore;
  verdict: DeploymentVerdict;
  blockReasons: BlockReason[];
  warnings: string[];
  /** Flattened `<gateId>.<metric>` map, the unit of regression comparison. */
  metrics: Record<string, number>;
}

/** The subset persisted as the comparison baseline for the next build. */
export interface Baseline {
  runId: string;
  projectId: string;
  recordedAt: string;
  commit: string | null;
  branch: string | null;
  score: number;
  verdict: DeploymentVerdict;
  metrics: Record<string, number>;
}
