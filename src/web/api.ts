export type WorkspaceSnapshot = {
  organizationId: string;
  canonical: {
    organization: {
      id: string;
      name: string;
      mission?: string;
      owners: string[];
      scope?: string;
      criticality?: string;
      environment: string;
      version: string;
    };
    capabilities: Array<Record<string, unknown>>;
    workers: Array<Record<string, unknown>>;
    interfaces: Array<Record<string, unknown>>;
    knowledgeMemories: Array<Record<string, unknown>>;
    governancePolicies: Array<Record<string, unknown>>;
    topologies: Array<{
      id: string;
      name: string;
      nodes: Array<{ id: string; refId: string; kind: string; label: string }>;
      edges: Array<{ id: string; from: string; to: string; kind: string; label?: string }>;
    }>;
    evidence: Array<{
      id: string;
      sourceType: string;
      status: string;
      summary: string;
      collectedAt: string;
      freshness?: string;
      confidence: string;
      lineage: string[];
    }>;
    metrics: Array<Record<string, unknown>>;
    changeSets: Array<Record<string, unknown>>;
    intentProfile?: IntentProfile;
  };
  intent?: IntentProfile;
  importValidation?: {
    ok: boolean;
    gaps: Array<{ path: string; severity: string; message: string }>;
    warnings: string[];
    unsupportedFeatures: string[];
  };
  gapAnalysis?: {
    objective: string;
    findings: Array<{
      id: string;
      category: string;
      severity: string;
      title: string;
      rationale: string;
      evidenceIds: string[];
      knowledgeIds: string[];
      evidenceConfidence: string;
    }>;
    preserveList: string[];
    summary: string;
  };
  candidates?: {
    candidates: Array<{
      id: string;
      name: string;
      template: string;
      summary: string;
      assumptions: string[];
      benefits: string[];
      costs: string[];
      risks: string[];
      reversibility: string;
      doNotUseWhen: string[];
      tradeOffs: Record<string, number>;
    }>;
    notes: string;
  };
  validationResults?: Array<{
    candidateId: string;
    declaredFidelity: string;
    checks: Array<{
      id: string;
      name: string;
      kind: string;
      pass: boolean;
      currentStatePass?: boolean;
      currentStateObservations?: string[];
      observations: string[];
      assumptions: string[];
    }>;
    overallPass: boolean;
    limitations: string[];
    modeled: string[];
    notModeled: string[];
  }>;
  reviewResults?: Array<{
    candidateId: string;
    dimensions: Array<{
      dimension: string;
      score: number;
      notes: string;
      blocker: boolean;
      blockerReason?: string;
    }>;
    averageScore: number;
    weightedScore: number;
    blockers: string[];
    status: "PASS" | "BLOCKED";
    summary: string;
  }>;
  recommendation?: {
    chosenCandidateId: string | null;
    rejectedCandidateIds: string[];
    selectionStatus?: string;
    eligibility?: {
      assessments: Array<{
        candidateId: string;
        eligible: boolean;
        reasons: string[];
      }>;
      blockReasons: string[];
      selectionStatus: string;
    };
    rationale: string;
    uncertainty: string[];
    approvalState: string;
    changeSet: Record<string, unknown>;
    traceChain: string[];
  };
  baselineComparison?: {
    baseline: {
      label: string;
      criticalGapCount: number;
      highGapCount: number;
      missingContracts: number;
      hasApprovalGate: boolean;
      orphanWorkerNodes: number;
      circularDependency: boolean;
      summary: string;
    };
    proposals: Array<{
      candidateId: string;
      name: string;
      remediates: string[];
      residualRisks: string[];
      validationOverallPass: boolean;
      reviewStatus: "PASS" | "BLOCKED";
      weightedScore: number;
      tradeOffs: Record<string, number>;
      vsBaseline: string;
    }>;
    notes: string;
  };
  changeHistory: Array<Record<string, unknown>>;
  exports: Array<{
    id: string;
    changeSetId: string;
    createdAt: string;
    markdown: string;
    json: unknown;
  }>;
  updatedAt: string;
};

export type IntentProfile = {
  id: string;
  mission?: string;
  successMeasures: string[];
  constraints: string[];
  riskTolerance: string;
  preserveList: string[];
  unresolvedQuestions: string[];
  fieldConfidence: Record<string, string>;
  confirmed: boolean;
};

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  list: () => req<{ organizationId: string; name: string; updatedAt: string }[]>("/api/workspaces"),
  importDemo: () => req<WorkspaceSnapshot>("/api/workspaces/import/demo", { method: "POST" }),
  importContent: (content: string, format: "json" | "yaml") =>
    req<WorkspaceSnapshot>("/api/workspaces/import", {
      method: "POST",
      body: JSON.stringify({ content, format, label: "upload" }),
    }),
  get: (id: string) => req<WorkspaceSnapshot>(`/api/workspaces/${id}`),
  updateIntent: (id: string, body: Partial<IntentProfile>) =>
    req<WorkspaceSnapshot>(`/api/workspaces/${id}/intent`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  analyze: (id: string) =>
    req<WorkspaceSnapshot>(`/api/workspaces/${id}/analyze`, { method: "POST" }),
  decide: (id: string, decision: "approved" | "rejected") =>
    req<WorkspaceSnapshot>(`/api/workspaces/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    }),
};
