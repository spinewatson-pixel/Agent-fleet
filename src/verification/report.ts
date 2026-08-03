import { GATE_CATEGORIES } from "./types.js";
import type { GateResult, GateStatus, VerificationRun } from "./types.js";

const MARK: Record<GateStatus, string> = {
  pass: "PASS",
  warn: "WARN",
  fail: "FAIL",
  skip: "SKIP",
};

/**
 * The console report. When a build is blocked this has to answer one question
 * without the reader opening anything else: what failed, and why.
 */
export function renderConsole(run: VerificationRun): string {
  const lines: string[] = [];
  lines.push(`${run.projectName} · verification ${run.runId}`);
  lines.push(
    `commit ${run.commit ?? "unknown"}${run.branch ? ` on ${run.branch}` : ""} · ${
      Math.round(run.durationMs / 100) / 10
    }s`,
  );
  lines.push("");

  for (const category of GATE_CATEGORIES) {
    const results = run.gateResults.filter((r) => r.category === category);
    if (results.length === 0) continue;
    lines.push(`${category.toUpperCase()}`);
    for (const result of results) {
      lines.push(
        `  ${MARK[result.status]}  ${result.gateId}  ${formatDuration(result.durationMs)}` +
          `${result.required ? "" : "  (optional)"}`,
      );
      for (const reason of result.reasons) {
        lines.push(`        ${reason}`);
      }
      const metrics = notableMetrics(result);
      if (metrics) lines.push(`        ${metrics}`);
    }
    lines.push("");
  }

  lines.push("REGRESSION");
  if (!run.regression.baselineRunId) {
    lines.push("  no previous successful build — this run establishes the baseline");
  } else {
    lines.push(
      `  compared ${run.regression.comparedMetrics} metrics against ${run.regression.baselineRunId}` +
        `${run.regression.baselineCommit ? ` (${run.regression.baselineCommit.slice(0, 8)})` : ""}`,
    );
    for (const finding of run.regression.findings) {
      lines.push(`  ${finding.regressed ? "REGRESSED" : "ok       "}  ${finding.reason}`);
    }
  }
  lines.push("");

  lines.push("READINESS");
  lines.push(`  score ${run.readiness.score}/100`);
  lines.push(`  verdict ${run.verdict}`);
  lines.push("");

  if (run.blockReasons.length > 0) {
    lines.push("DEPLOYMENT STOPPED — the following gates must be resolved:");
    for (const reason of run.blockReasons) {
      lines.push(`  [${reason.code}] ${reason.detail}`);
    }
    lines.push("");
    const failed = run.gateResults.filter((r) => r.status === "fail" && r.evidence);
    for (const result of failed) {
      lines.push(`--- evidence · ${result.gateId} ---`);
      lines.push(indent(tail(result.evidence, 24)));
      lines.push("");
    }
  } else if (run.warnings.length > 0) {
    lines.push("WARNINGS (non-blocking):");
    for (const warning of run.warnings) lines.push(`  · ${warning}`);
    lines.push("");
  }

  return lines.join("\n");
}

export function renderMarkdown(run: VerificationRun): string {
  const lines: string[] = [];
  lines.push(`# Verification — ${run.projectName}`);
  lines.push("");
  lines.push(`**Verdict:** \`${run.verdict}\` · **Readiness:** ${run.readiness.score}/100`);
  lines.push("");
  lines.push(`| Field | Value |`);
  lines.push(`| --- | --- |`);
  lines.push(`| Run | \`${run.runId}\` |`);
  lines.push(`| Commit | \`${run.commit ?? "unknown"}\` |`);
  lines.push(`| Branch | \`${run.branch ?? "unknown"}\` |`);
  lines.push(`| Started | ${run.startedAt} |`);
  lines.push(`| Duration | ${Math.round(run.durationMs / 100) / 10}s |`);
  lines.push("");

  lines.push("## Gates");
  lines.push("");
  lines.push("| Gate | Category | Required | Status | Duration | Notes |");
  lines.push("| --- | --- | --- | --- | --- | --- |");
  for (const result of run.gateResults) {
    lines.push(
      `| \`${result.gateId}\` | ${result.category} | ${result.required ? "yes" : "no"} | ` +
        `**${MARK[result.status]}** | ${formatDuration(result.durationMs)} | ${
          result.reasons.join("; ").replace(/\|/g, "\\|") || result.description
        } |`,
    );
  }
  lines.push("");

  lines.push("## Regression vs previous successful build");
  lines.push("");
  if (!run.regression.baselineRunId) {
    lines.push("No baseline yet — this run establishes it.");
  } else {
    lines.push(`Baseline: \`${run.regression.baselineRunId}\``);
    lines.push("");
    lines.push("| Metric | Baseline | Current | Change | Verdict |");
    lines.push("| --- | --- | --- | --- | --- |");
    for (const f of run.regression.findings) {
      lines.push(
        `| \`${f.rule.metric}\` | ${f.baselineValue} | ${
          Number.isNaN(f.currentValue) ? "absent" : f.currentValue
        } | ${formatRatio(f.changeRatio)} | ${f.regressed ? `**REGRESSED** (${f.rule.severity})` : "ok"} |`,
      );
    }
  }
  lines.push("");

  lines.push("## Readiness score");
  lines.push("");
  lines.push("| Gate | Weight | Status | Earned |");
  lines.push("| --- | --- | --- | --- |");
  for (const entry of run.readiness.breakdown) {
    lines.push(
      `| \`${entry.gateId}\` | ${entry.weight} | ${MARK[entry.status]} | ${entry.earned} |`,
    );
  }
  lines.push("");
  lines.push(
    `**Total:** ${run.readiness.earnedWeight} / ${run.readiness.totalWeight} → **${run.readiness.score}/100**`,
  );
  lines.push("");

  if (run.blockReasons.length > 0) {
    lines.push("## Deployment stopped");
    lines.push("");
    for (const reason of run.blockReasons) {
      lines.push(`- \`${reason.code}\` — ${reason.detail}`);
    }
    lines.push("");
  }

  if (run.warnings.length > 0) {
    lines.push("## Warnings");
    lines.push("");
    for (const warning of run.warnings) lines.push(`- ${warning}`);
    lines.push("");
  }

  return lines.join("\n");
}

function notableMetrics(result: GateResult): string {
  const entries = Object.entries(result.metrics).filter(([key]) => key !== "duration_ms");
  if (entries.length === 0) return "";
  return entries.map(([key, value]) => `${key}=${value}`).join("  ");
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatRatio(ratio: number): string {
  if (Number.isNaN(ratio)) return "n/a";
  if (!Number.isFinite(ratio)) return ratio > 0 ? "+∞" : "-∞";
  const pct = ratio * 100;
  return `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

function tail(text: string, maxLines: number): string {
  const lines = text.split("\n");
  return lines.length <= maxLines ? text : lines.slice(lines.length - maxLines).join("\n");
}

function indent(text: string): string {
  return text
    .split("\n")
    .map((line) => `    ${line}`)
    .join("\n");
}
