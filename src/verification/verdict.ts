import { GATE_CATEGORIES } from "./types.js";
import type {
  BlockReason,
  DeploymentVerdict,
  GateResult,
  ProjectManifest,
  ReadinessScore,
  RegressionReport,
} from "./types.js";

/**
 * Structural checks on the manifest itself.
 *
 * This is the part that stops verification from depending on someone
 * remembering: a project that never declared an end-to-end or governance gate
 * does not quietly score 100, it fails to verify at all.
 */
export function validateManifest(manifest: ProjectManifest): BlockReason[] {
  const problems: BlockReason[] = [];
  const seen = new Set<string>();

  if (manifest.gates.length === 0) {
    problems.push({
      code: "manifest_invalid",
      detail: `project '${manifest.id}' declares no gates`,
    });
  }

  for (const gate of manifest.gates) {
    if (seen.has(gate.id)) {
      problems.push({
        code: "manifest_invalid",
        detail: `duplicate gate id '${gate.id}'`,
      });
    }
    seen.add(gate.id);

    if (!gate.command) {
      problems.push({
        code: "manifest_invalid",
        detail: `gate '${gate.id}' declares no command — it cannot verify anything`,
      });
    }
    if (!(gate.weight > 0)) {
      problems.push({
        code: "manifest_invalid",
        detail: `gate '${gate.id}' has weight ${gate.weight}; weight must be positive`,
      });
    }
  }

  if (manifest.policy.minimumScore < 0 || manifest.policy.minimumScore > 100) {
    problems.push({
      code: "manifest_invalid",
      detail: `minimumScore ${manifest.policy.minimumScore} is outside 0-100`,
    });
  }

  if (manifest.policy.requireAllCategories) {
    for (const category of GATE_CATEGORIES) {
      if (!manifest.gates.some((g) => g.category === category)) {
        problems.push({
          code: "missing_category",
          detail: `no '${category}' gate declared — every build must produce ${category} verification`,
        });
      }
    }
  }

  return problems;
}

export interface VerdictInput {
  manifest: ProjectManifest;
  results: GateResult[];
  regression: RegressionReport;
  readiness: ReadinessScore;
  hasBaseline: boolean;
}

export interface VerdictOutput {
  verdict: DeploymentVerdict;
  blockReasons: BlockReason[];
  warnings: string[];
}

/**
 * The deployment decision. Any single blocking condition stops the build; a
 * high score never buys its way past a failed required gate.
 */
export function decideVerdict(input: VerdictInput): VerdictOutput {
  const blockReasons: BlockReason[] = validateManifest(input.manifest);
  const warnings: string[] = [];

  for (const result of input.results) {
    if (result.status === "fail") {
      const detail = `${result.gateId} (${result.category}) failed: ${
        result.reasons.join("; ") || "no reason reported"
      }`;
      if (result.required) {
        blockReasons.push({ code: "required_gate_failed", detail });
      } else {
        warnings.push(`optional gate ${detail}`);
      }
    } else if (result.status === "warn") {
      warnings.push(
        `${result.gateId} (${result.category}) passed with warnings: ${result.reasons.join("; ")}`,
      );
    } else if (result.status === "skip") {
      warnings.push(`${result.gateId} (${result.category}) was skipped`);
    }
  }

  // A required category whose gates all failed to produce a result at all.
  if (input.manifest.policy.requireAllCategories) {
    for (const category of GATE_CATEGORIES) {
      const declared = input.manifest.gates.some((g) => g.category === category);
      const executed = input.results.some((r) => r.category === category);
      if (declared && !executed) {
        blockReasons.push({
          code: "missing_category",
          detail: `'${category}' gates were declared but produced no result`,
        });
      }
    }
  }

  for (const failure of input.regression.failures) {
    blockReasons.push({ code: "regression_failure", detail: failure.reason });
  }
  for (const warning of input.regression.warnings) {
    warnings.push(`regression: ${warning.reason}`);
  }
  for (const metric of input.regression.unmatchedRules) {
    warnings.push(
      `regression rule for '${metric}' had no baseline value — it will start comparing from this build`,
    );
  }

  if (input.readiness.score < input.manifest.policy.minimumScore) {
    blockReasons.push({
      code: "score_below_minimum",
      detail: `readiness score ${input.readiness.score} is below the required minimum of ${input.manifest.policy.minimumScore}`,
    });
  }

  if (!input.hasBaseline) {
    const detail =
      "no previous successful build to compare against; regression comparison could not run";
    if (input.manifest.policy.requireBaseline) {
      blockReasons.push({ code: "baseline_missing", detail });
    } else {
      warnings.push(detail);
    }
  }

  const verdict: DeploymentVerdict =
    blockReasons.length > 0 ? "BLOCKED" : warnings.length > 0 ? "READY_WITH_WARNINGS" : "READY";

  return { verdict, blockReasons, warnings };
}
