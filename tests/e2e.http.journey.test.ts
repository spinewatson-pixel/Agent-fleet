/**
 * End-to-end HTTP journey against the real Express app (no browser).
 * Covers: import fixture → inspect canonical → intent/evidence → gap →
 * candidates → validation → baseline/proposal compare → review →
 * recommendation → approval/export → mutation rejected.
 */
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createApp } from "../src/api/createApp.js";

describe("HTTP end-to-end advisory journey", () => {
  let dataDir: string;
  let server: http.Server;
  let base: string;

  beforeAll(async () => {
    dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "af-e2e-"));
    const { app } = createApp({ dataDir });
    server = app.listen(0);
    await new Promise<void>((resolve) => server.once("listening", () => resolve()));
    const addr = server.address();
    if (!addr || typeof addr === "string") throw new Error("no listen address");
    base = `http://127.0.0.1:${addr.port}`;
  });

  afterAll(async () => {
    await new Promise<void>((resolve, reject) => {
      server.close((err) => (err ? reject(err) : resolve()));
    });
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  async function api<T>(
    method: string,
    urlPath: string,
    body?: unknown,
  ): Promise<{ status: number; data: T }> {
    const res = await fetch(`${base}${urlPath}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = (await res.json()) as T;
    return { status: res.status, data };
  }

  it("completes the full product journey over HTTP", async () => {
    // 1) Health / security posture
    const health = await api<{
      ok: boolean;
      mutationAllowed: boolean;
      mode: string;
    }>("GET", "/api/health");
    expect(health.status).toBe(200);
    expect(health.data.ok).toBe(true);
    expect(health.data.mutationAllowed).toBe(false);
    expect(health.data.mode).toBe("advisory_export_only");

    // 2) Import fixture → canonical model
    const imported = await api<{
      organizationId: string;
      canonical: {
        organization: { name: string; mission?: string };
        capabilities: unknown[];
        workers: unknown[];
        interfaces: Array<{ contractSchema?: string }>;
        evidence: Array<{ status: string }>;
        topologies: Array<{ nodes: unknown[]; edges: unknown[] }>;
      };
      intent?: { unresolvedQuestions: string[]; mission?: string };
      importValidation?: { gaps: Array<{ path: string }> };
    }>("POST", "/api/workspaces/import/demo");
    expect(imported.status).toBe(201);
    expect(imported.data.canonical.organization.name).toContain("Contoso");
    expect(imported.data.canonical.organization.mission).toBeUndefined();
    expect(imported.data.canonical.evidence.some((e) => e.status === "observation")).toBe(
      true,
    );
    expect(imported.data.canonical.topologies[0].nodes.length).toBeGreaterThan(0);
    expect(
      imported.data.importValidation?.gaps.some((g) => g.path.includes("contractSchema")),
    ).toBe(true);
    expect(imported.data.intent?.unresolvedQuestions.length).toBeGreaterThan(0);

    const id = imported.data.organizationId;

    // 3) Inspect canonical via GET
    const inspected = await api<typeof imported.data>("GET", `/api/workspaces/${id}`);
    expect(inspected.status).toBe(200);
    expect(inspected.data.canonical.workers.length).toBeGreaterThan(0);
    expect(
      inspected.data.canonical.interfaces.some((i) => !i.contractSchema),
    ).toBe(true);

    // 4) Reconstruct intent / evidence (owner statements)
    const intented = await api<{
      intent: {
        mission: string;
        unresolvedQuestions: string[];
        confirmed: boolean;
      };
      canonical: { evidence: Array<{ sourceType: string; status: string }> };
    }>("PUT", `/api/workspaces/${id}/intent`, {
      mission: "Reliable claims summarization under human governance",
      successMeasures: ["usable draft rate >= 0.98", "approval before notify"],
      constraints: ["human approval before notify", "no live mutation"],
      riskTolerance: "low",
      preserveList: ["retrieval read-only authority", "intake API mTLS"],
      confirmed: true,
    });
    expect(intented.status).toBe(200);
    expect(intented.data.intent.mission).toMatch(/Reliable claims/);
    expect(intented.data.intent.unresolvedQuestions).toEqual([]);
    expect(
      intented.data.canonical.evidence.some(
        (e) =>
          e.sourceType === "owner_statement" &&
          e.status === "assertion" &&
          (e as { confidence?: string }).confidence === "medium",
      ),
    ).toBe(true);

    // 5–8) Gap → candidates → validation → baseline/proposal → review → recommendation
    const analyzed = await api<{
      gapAnalysis: {
        findings: Array<{ id: string; severity: string; evidenceIds: string[] }>;
        preserveList: string[];
      };
      candidates: { candidates: Array<{ id: string; name: string }> };
      validationResults: Array<{
        candidateId: string;
        checks: Array<{ id: string; pass: boolean }>;
        limitations: string[];
      }>;
      reviewResults: Array<{
        candidateId: string;
        status: string;
        blockers: string[];
        weightedScore: number;
      }>;
      baselineComparison: {
        baseline: {
          label: string;
          criticalGapCount: number;
          missingContracts: number;
          hasApprovalGate: boolean;
        };
        proposals: Array<{
          candidateId: string;
          remediates: string[];
          reviewStatus: string;
          vsBaseline: string;
        }>;
      };
      recommendation: {
        chosenCandidateId: string | null;
        rejectedCandidateIds: string[];
        selectionStatus: string;
        rationale: string;
        uncertainty: string[];
        traceChain: string[];
      };
    }>("POST", `/api/workspaces/${id}/analyze`);

    expect(analyzed.status).toBe(200);
    expect(
      analyzed.data.gapAnalysis.findings.some((f) => f.id.startsWith("gap_contract_")),
    ).toBe(true);
    expect(
      analyzed.data.gapAnalysis.findings.some((f) => f.id === "gap_approval_gate"),
    ).toBe(true);
    expect(analyzed.data.gapAnalysis.preserveList.length).toBeGreaterThan(0);
    expect(analyzed.data.candidates.candidates.length).toBeGreaterThanOrEqual(2);

    // Deterministic simulation/validation catches seeded cases
    const anyValidation = analyzed.data.validationResults[0];
    expect(anyValidation.checks.some((c) => c.id === "static_missing_contracts")).toBe(
      true,
    );
    expect(
      anyValidation.checks.some((c) => c.id === "scenario_escalation_approval"),
    ).toBe(true);
    expect(anyValidation.limitations.length).toBeGreaterThan(0);

    // Baseline vs proposal comparison
    expect(analyzed.data.baselineComparison.baseline.label).toBe("current_baseline");
    expect(analyzed.data.baselineComparison.baseline.missingContracts).toBeGreaterThan(0);
    expect(analyzed.data.baselineComparison.baseline.hasApprovalGate).toBe(false);
    expect(analyzed.data.baselineComparison.proposals.length).toBeGreaterThanOrEqual(2);
    expect(
      analyzed.data.baselineComparison.proposals.every((p) => p.vsBaseline.length > 0),
    ).toBe(true);

    // Architecture review present; demo must not select ineligible candidates
    expect(analyzed.data.reviewResults.length).toBeGreaterThanOrEqual(2);
    expect(analyzed.data.recommendation.traceChain).toEqual([
      "Mission",
      "Intent",
      "Evidence",
      "Knowledge",
      "Simulation/Validation",
      "Architecture Review",
      "Recommendation",
      "Approval/Outcome",
    ]);
    expect(analyzed.data.recommendation.rationale.length).toBeGreaterThan(0);
    expect(analyzed.data.recommendation.selectionStatus).toBe(
      "BLOCKED_NO_ELIGIBLE_CANDIDATE",
    );
    expect(analyzed.data.recommendation.chosenCandidateId).toBeNull();

    // Demo approve/export blocked by eligibility gate
    const blocked = await api<{ error: string }>("POST", `/api/workspaces/${id}/decision`, {
      decision: "approved",
    });
    expect(blocked.status).toBe(400);
    expect(blocked.data.error).toMatch(/eligibility gate/i);

    // Eligible fixture can approve/export
    const eligible = await api<{ organizationId: string }>(
      "POST",
      "/api/workspaces/import/fixture/eligible-org.yaml",
    );
    expect(eligible.status).toBe(201);
    const eid = eligible.data.organizationId;
    await api("PUT", `/api/workspaces/${eid}/intent`, {
      mission: "Reliable claims summarization under human governance",
      successMeasures: ["usable draft rate >= 0.98"],
      constraints: ["human approval before notify"],
      riskTolerance: "low",
      preserveList: ["retrieval read-only authority"],
      confirmed: true,
    });
    const eligibleAnalyzed = await api<{
      recommendation: {
        chosenCandidateId: string | null;
        selectionStatus: string;
      };
    }>("POST", `/api/workspaces/${eid}/analyze`);
    expect(eligibleAnalyzed.data.recommendation.selectionStatus).toBe("SELECTED");
    expect(eligibleAnalyzed.data.recommendation.chosenCandidateId).toBeTruthy();

    const decided = await api<{
      exports: Array<{ id: string; markdown: string; json: Record<string, unknown> }>;
      changeHistory: Array<{ approvalState: string; outcome?: string }>;
      recommendation: { approvalState: string };
    }>("POST", `/api/workspaces/${eid}/decision`, { decision: "approved" });
    expect(decided.status).toBe(200);
    expect(decided.data.exports.length).toBe(1);
    expect(decided.data.exports[0].markdown).toContain("Trace chain");
    expect(decided.data.exports[0].markdown).toContain("advisory-only");
    expect(decided.data.exports[0].json.securityBoundaries).toMatchObject({
      readOnly: true,
      liveMutationPath: false,
    });
    expect(decided.data.changeHistory[0].approvalState).toBe("exported");
    expect(decided.data.changeHistory[0].outcome).toMatch(/No deployment/);

    const exportId = decided.data.exports[0].id;
    const artifact = await api<{ markdown: string }>(
      "GET",
      `/api/workspaces/${eid}/exports/${exportId}`,
    );
    expect(artifact.status).toBe(200);
    expect(artifact.data.markdown).toContain("Staged migration plan");

    // Mutation path rejected
    const apply = await api<{ code: string }>("POST", "/api/apply", { change: true });
    expect(apply.status).toBe(405);
    expect(apply.data.code).toBe("MUTATION_REJECTED");
  });
});
