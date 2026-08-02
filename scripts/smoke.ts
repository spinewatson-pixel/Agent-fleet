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

  const imported = await req<{
    organizationId: string;
    canonical: { organization: { name: string }; evidence: unknown[] };
    intent?: { unresolvedQuestions: string[] };
  }>("POST", "/api/workspaces/import/demo");

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
    recommendation: { chosenCandidateId: string | null; traceChain: string[] };
  }>("POST", `/api/workspaces/${imported.organizationId}/analyze`);

  if (analyzed.gapAnalysis.findings.length < 1) throw new Error("expected gaps");
  if (analyzed.candidates.candidates.length < 2) throw new Error("expected >=2 candidates");
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
  console.log(`  org: ${imported.canonical.organization.name}`);
  console.log(`  gaps: ${analyzed.gapAnalysis.findings.length}`);
  console.log(`  candidates: ${analyzed.candidates.candidates.length}`);
  console.log(`  chosen: ${analyzed.recommendation.chosenCandidateId}`);
  console.log(`  exportChars: ${exported.exports[0].markdown.length}`);
}

main().catch((err) => {
  console.error("SMOKE_FAIL", err);
  process.exit(1);
});
