import { spawn } from "node:child_process";
import path from "node:path";
import { parseGateOutput, type RawGateOutput } from "./parsers.js";
import { evaluateThresholds } from "./thresholds.js";
import type { GateResult, GateSpec, GateStatus, Metrics } from "./types.js";

const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const EVIDENCE_CHARS = 4000;

export interface RunGateOptions {
  rootDir: string;
  /** Injected in tests so gate execution can be exercised without spawning. */
  execute?: (spec: GateSpec, cwd: string) => Promise<RawGateOutput>;
  onGateStart?: (spec: GateSpec) => void;
  onGateFinish?: (result: GateResult) => void;
}

/**
 * Execute one gate and classify it.
 *
 * The classification order matters: an infrastructure problem (timeout,
 * non-zero exit, unparseable output) outranks anything the gate claims about
 * itself, so a broken gate can never report success.
 */
export async function runGate(
  spec: GateSpec,
  options: RunGateOptions,
): Promise<GateResult> {
  const cwd = path.resolve(options.rootDir, spec.cwd ?? ".");
  const started = Date.now();
  options.onGateStart?.(spec);

  const exec = options.execute ?? executeCommand;
  let raw: RawGateOutput;
  try {
    raw = await exec(spec, cwd);
  } catch (err) {
    raw = {
      stdout: "",
      stderr: `gate could not be executed: ${(err as Error).message}`,
      exitCode: null,
      timedOut: false,
    };
  }
  const durationMs = Date.now() - started;

  const parsed = parseGateOutput(spec.parser, raw);
  const metrics: Metrics = { ...parsed.metrics, duration_ms: durationMs };
  const breaches = evaluateThresholds(spec.thresholds, metrics);

  const reasons: string[] = [];
  let status: GateStatus = "pass";

  if (raw.timedOut) {
    status = "fail";
    reasons.push(`timed out after ${spec.timeoutMs ?? DEFAULT_TIMEOUT_MS}ms`);
  } else if (raw.exitCode !== 0) {
    status = "fail";
    reasons.push(
      raw.exitCode === null
        ? "command did not run to completion"
        : `exited with code ${raw.exitCode}`,
    );
  }

  if (parsed.parseError) {
    status = "fail";
    reasons.push(parsed.parseError);
  }

  for (const breach of breaches) {
    if (breach.threshold.severity === "fail") {
      status = "fail";
      reasons.push(breach.reason);
    } else if (status === "pass") {
      status = "warn";
      reasons.push(`(warning) ${breach.reason}`);
    } else {
      reasons.push(`(warning) ${breach.reason}`);
    }
  }

  // A gate may downgrade itself, never upgrade itself.
  if (status === "pass" && parsed.statusHint && parsed.statusHint !== "pass") {
    status = parsed.statusHint;
    reasons.push(`gate reported status '${parsed.statusHint}'`);
  }

  // A required gate that opts out is not satisfied.
  if (status === "skip" && spec.required) {
    status = "fail";
    reasons.push("required gate reported 'skip' — a required gate must actually run");
  }

  const result: GateResult = {
    gateId: spec.id,
    category: spec.category,
    description: spec.description,
    required: spec.required,
    weight: spec.weight,
    status,
    durationMs,
    exitCode: raw.exitCode,
    reasons,
    metrics,
    breaches,
    evidence: buildEvidence(raw),
    timedOut: raw.timedOut,
  };
  options.onGateFinish?.(result);
  return result;
}

export async function runGates(
  gates: GateSpec[],
  options: RunGateOptions,
): Promise<GateResult[]> {
  const results: GateResult[] = [];
  // Sequential on purpose: gates share ports, databases and build output, and a
  // parallel run would make timing metrics meaningless.
  for (const spec of gates) {
    results.push(await runGate(spec, options));
  }
  return results;
}

function executeCommand(spec: GateSpec, cwd: string): Promise<RawGateOutput> {
  if (!spec.command) {
    return Promise.resolve({
      stdout: "",
      stderr: `gate '${spec.id}' declares no command`,
      exitCode: null,
      timedOut: false,
    });
  }
  const timeoutMs = spec.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  return new Promise<RawGateOutput>((resolve) => {
    const child = spawn(spec.command as string, {
      cwd,
      shell: true,
      env: { ...process.env, ...spec.env, CI: process.env.CI ?? "1" },
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let settled = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    const settle = (exitCode: number | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ stdout, stderr, exitCode: timedOut ? null : exitCode, timedOut });
    };

    child.on("error", (err) => {
      stderr += `\n${err.message}`;
      settle(null);
    });
    child.on("close", (code) => settle(code));
  });
}

function buildEvidence(raw: RawGateOutput): string {
  const combined = [raw.stdout.trim(), raw.stderr.trim()].filter(Boolean).join("\n");
  if (combined.length <= EVIDENCE_CHARS) return combined;
  // Keep the tail: failures print their cause last.
  return `…(truncated)…\n${combined.slice(combined.length - EVIDENCE_CHARS)}`;
}
