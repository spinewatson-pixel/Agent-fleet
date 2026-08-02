/**
 * Repeatable smoke journey against a running API (default http://localhost:8787).
 * Usage: pnpm smoke   (API must already be up, or run `pnpm start` / `pnpm dev:api`)
 */
const BASE = process.env.AGENT_FLEET_URL ?? "http://localhost:8787";

async function req<T>(method: string, urlPath: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${urlPath}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) throw new Error(`${method} ${urlPath} → ${res.status}: ${text}`);
  return data as T;
}

async function main() {
  const health = await req<{ ok: boolean; mutationAllowed: boolean }>("GET", "/api/health");
  if (!health.ok || health.mutationAllowed) throw new Error("health check failed");

  const apply = await fetch(`${BASE}/api/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (apply.status !== 405) throw new Error(`expected apply 405, got ${apply.status}`);

  // Demo path must block approve/export when no eligible candidate exists.
  const demo = await req<{
    organizationId: string;
    canonical: { organization: { name: string } };
  }>("POST", "/api/workspaces/import/demo");
  await req("PUT", `/api/workspaces/${demo.organizationId}/intent`, {
    mission: "Reliable claims summarization under human governance",
    successMeasures: ["usable draft rate >= 0.98"],
    constraints: ["human approval before notify"],
    riskTolerance: "low",
    preserveList: ["retrieval read-only authority"],
    confirmed: true,
  });
  const demoAnalyzed = await req<{
    recommendation: {
      chosenCandidateId: string | null;
      selectionStatus: string;
      traceChain: string[];
    };
    gapAnalysis: { findings: unknown[] };
    candidates: { candidates: unknown[] };
    baselineComparison: { proposals: unknown[] };
  }>("POST", `/api/workspaces/${demo.organizationId}/analyze`);
  if (demoAnalyzed.recommendation.selectionStatus !== "BLOCKED_NO_ELIGIBLE_CANDIDATE") {
    throw new Error("demo should be BLOCKED_NO_ELIGIBLE_CANDIDATE");
  }
  if (demoAnalyzed.recommendation.chosenCandidateId !== null) {
    throw new Error("demo must not select an ineligible candidate");
  }
  const blockedApprove = await fetch(
    `${BASE}/api/workspaces/${demo.organizationId}/decision`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: "approved" }),
    },
  );
  if (blockedApprove.status === 200) {
    throw new Error("demo approve/export should fail eligibility gate");
  }

  // Eligible fixture path can approve/export.
  const imported = await req<{
    organizationId: string;
    canonical: { organization: { name: string }; evidence: unknown[] };
  }>("POST", "/api/workspaces/import/fixture/eligible-org.yaml");

  await req("PUT", `/api/workspaces/${imported.organizationId}/intent`, {
    mission: "Reliable claims summarization under human governance",
    successMeasures: ["usable draft rate >= 0.98"],
    constraints: ["human approval before notify"],
    riskTolerance: "low",
    preserveList: ["retrieval read-only authority"],
    confirmed: true,
  });

  const analyzed = await req<{
    gapAnalysis: { findings: unknown[] };
    candidates: { candidates: unknown[] };
    validationResults: unknown[];
    reviewResults: unknown[];
    baselineComparison: { baseline: unknown; proposals: unknown[] };
    recommendation: {
      chosenCandidateId: string | null;
      selectionStatus: string;
      traceChain: string[];
    };
  }>("POST", `/api/workspaces/${imported.organizationId}/analyze`);

  if (analyzed.recommendation.selectionStatus !== "SELECTED") {
    throw new Error("eligible org should SELECT a candidate");
  }
  if (!analyzed.recommendation.chosenCandidateId) {
    throw new Error("expected chosen eligible candidate");
  }
  if (!analyzed.baselineComparison?.proposals?.length) {
    throw new Error("expected baseline/proposal comparison");
  }
  if (!analyzed.recommendation.traceChain.includes("Approval/Outcome")) {
    throw new Error("trace chain incomplete");
  }

  const exported = await req<{
    exports: Array<{ markdown: string; json: unknown }>;
    changeHistory: Array<{ approvalState: string }>;
  }>("POST", `/api/workspaces/${imported.organizationId}/decision`, {
    decision: "approved",
  });

  if (exported.exports.length < 1) throw new Error("expected export artifact");
  if (!exported.exports[0].markdown.includes("advisory-only")) {
    throw new Error("export missing advisory marker");
  }

  console.log("SMOKE_OK");
  console.log(`  demoBlocked: ${demo.canonical.organization.name}`);
  console.log(`  eligibleOrg: ${imported.canonical.organization.name}`);
  console.log(`  chosen: ${analyzed.recommendation.chosenCandidateId}`);
  console.log(`  exportChars: ${exported.exports[0].markdown.length}`);
}

main().catch((err) => {
  console.error("SMOKE_FAIL", err);
  process.exit(1);
});
