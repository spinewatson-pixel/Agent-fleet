import fs from "node:fs";
import path from "node:path";
import { defaultAdapter } from "./adapters/readOnlyDiscoveryAdapter.js";
import { evaluateIntentCompleteness } from "./services/intentCompleteness.js";
import {
  JsonFileWorkspaceStore,
  type WorkspaceSnapshot,
  type WorkspaceStore,
  defaultDataDir,
} from "./services/workspaceStore.js";
import { analyzeGaps } from "./engines/gapAnalysis.js";
import { synthesizeCandidates } from "./engines/candidateSynthesis.js";
import { validateAllCandidates } from "./engines/validation.js";
import { reviewAll } from "./engines/review.js";
import {
  buildRecommendation,
  exportRecommendationArtifacts,
  type RecommendationResult,
} from "./engines/recommendAndExport.js";
import {
  compareBaselineToProposals,
  type BaselineProposalComparison,
} from "./engines/baselineComparison.js";
import {
  assertEligibleForApprovalExport,
  runEligibilityGate,
} from "./engines/eligibility.js";
import type { GapAnalysisResult } from "./engines/gapAnalysis.js";
import type { CandidateArchitecture } from "./engines/candidateSynthesis.js";
import type { ValidationResult } from "./engines/validation.js";
import type { ReviewResult } from "./engines/review.js";
import type { IntentProfile } from "./schemas/entities.js";
import { SCHEMA_VERSION } from "./schemas/common.js";
import { newId, nowIso } from "./util/ids.js";

export class BuilderPipeline {
  constructor(
    private readonly store: WorkspaceStore = new JsonFileWorkspaceStore(defaultDataDir()),
    private readonly adapter = defaultAdapter,
  ) {}

  getStore(): WorkspaceStore {
    return this.store;
  }

  async importDemo(): Promise<WorkspaceSnapshot> {
    return this.importFixture("demo-org.yaml");
  }

  async importFixture(fileName: string): Promise<WorkspaceSnapshot> {
    const fixturePath = path.resolve(process.cwd(), "fixtures", fileName);
    const text = fs.readFileSync(fixturePath, "utf8");
    return this.importRaw(text, { label: fileName, format: "yaml" });
  }

  async importRaw(
    input: string | unknown,
    options?: { label?: string; format?: "json" | "yaml" },
  ): Promise<WorkspaceSnapshot> {
    const raw = await this.adapter.discover(input, options);
    const canonical = await this.adapter.normalize(raw);
    const importValidation = await this.adapter.validate(canonical);
    const intentEval = evaluateIntentCompleteness(canonical);

    const snapshot: WorkspaceSnapshot = {
      organizationId: canonical.organization.id,
      canonical: {
        ...canonical,
        intentProfile: intentEval.profile,
      },
      intent: intentEval.profile,
      importValidation,
      changeHistory: [],
      exports: [],
      updatedAt: nowIso(),
    };
    await this.store.save(snapshot);
    return snapshot;
  }

  async updateIntent(
    organizationId: string,
    input: Partial<IntentProfile>,
  ): Promise<WorkspaceSnapshot> {
    const snap = await this.require(organizationId);
    const evalResult = evaluateIntentCompleteness(snap.canonical, {
      ...snap.intent,
      ...input,
    });
    // Record owner statements as evidence
    if (input.mission || input.successMeasures || input.constraints) {
      const ts = nowIso();
      snap.canonical.evidence.push({
        id: newId("ev"),
        schemaVersion: SCHEMA_VERSION,
        createdAt: ts,
        updatedAt: ts,
        ownerIds: snap.canonical.organization.owners,
        evidenceIds: [],
        sourceType: "owner_statement",
        status: "assertion",
        summary: "Owner updated intent/constraints form (assertion; not corroborated observation)",
        collectedAt: ts,
        freshness: "at_statement",
        // Owner assertions are not high-confidence without corroborating observation.
        confidence: "medium",
        lineage: [],
        details: { fields: Object.keys(input) },
      });
    }
    snap.intent = evalResult.profile;
    snap.canonical.intentProfile = evalResult.profile;
    await this.store.save(snap);
    return snap;
  }

  async runAnalysis(organizationId: string): Promise<WorkspaceSnapshot> {
    const snap = await this.require(organizationId);
    const gaps = analyzeGaps(snap.canonical, snap.intent);
    const { candidates, notes } = synthesizeCandidates(
      snap.canonical,
      gaps,
      snap.intent,
    );
    const validationResults = validateAllCandidates(snap.canonical, candidates);
    const reviewResults = reviewAll(
      snap.canonical,
      candidates,
      gaps,
      validationResults,
      snap.intent,
    );
    const recommendation = buildRecommendation(
      snap.canonical,
      candidates,
      validationResults,
      reviewResults,
      gaps,
      snap.intent,
    );
    const baselineComparison = compareBaselineToProposals(
      snap.canonical,
      gaps,
      candidates,
      validationResults,
      reviewResults,
    );

    snap.gapAnalysis = gaps;
    snap.candidates = { candidates, notes };
    snap.validationResults = validationResults;
    snap.reviewResults = reviewResults;
    snap.recommendation = recommendation;
    snap.baselineComparison = baselineComparison;
    snap.eligibility = recommendation.eligibility;
    await this.store.save(snap);
    return snap;
  }

  async approveAndExport(
    organizationId: string,
    decision: "approved" | "rejected",
  ): Promise<WorkspaceSnapshot> {
    const snap = await this.require(organizationId);
    if (!snap.recommendation || !snap.gapAnalysis || !snap.candidates) {
      throw new Error("Run analysis before approve/export");
    }

    const base = snap.recommendation as RecommendationResult;
    const gaps = snap.gapAnalysis as GapAnalysisResult;
    const candidatesBundle = snap.candidates as {
      candidates: CandidateArchitecture[];
      notes: string;
    };
    const validations = snap.validationResults as ValidationResult[];
    const reviews = snap.reviewResults as ReviewResult[];

    // Re-run gate at approval time — never trust a stale chosen id.
    const gate = runEligibilityGate({
      candidates: candidatesBundle.candidates,
      validations,
      reviews,
      gaps,
    });
    const recommendationFresh: RecommendationResult = {
      ...base,
      eligibility: gate,
      selectionStatus: gate.selectionStatus,
      chosenCandidateId: gate.chosenCandidateId,
      rejectedCandidateIds: candidatesBundle.candidates
        .filter((c) => c.id !== gate.chosenCandidateId)
        .map((c) => c.id),
    };

    if (decision === "approved") {
      const gateCheck = assertEligibleForApprovalExport({
        chosenCandidateId: recommendationFresh.chosenCandidateId,
        gate,
      });
      if (!gateCheck.ok) {
        throw new Error(
          `Approval/export blocked by eligibility gate: ${gateCheck.reasons.join("; ")}`,
        );
      }
    }

    if (decision === "rejected") {
      const recommendation: RecommendationResult = {
        ...recommendationFresh,
        approvalState: "rejected",
        changeSet: {
          ...recommendationFresh.changeSet,
          approvalState: "rejected",
          outcome: "Human rejected recommendation. No deployment performed.",
          updatedAt: nowIso(),
          candidateId: recommendationFresh.chosenCandidateId ?? undefined,
        },
      };
      await this.store.appendChange(organizationId, recommendation.changeSet);
      const refreshed = await this.require(organizationId);
      refreshed.recommendation = recommendation;
      refreshed.eligibility = gate;
      await this.store.save(refreshed);
      return refreshed;
    }

    const recommendation: RecommendationResult = {
      ...recommendationFresh,
      approvalState: "exported",
      changeSet: {
        ...recommendationFresh.changeSet,
        approvalState: "exported",
        outcome:
          "Human approved advisory recommendation and exported plan (state=exported). No deployment performed.",
        updatedAt: nowIso(),
        candidateId: recommendationFresh.chosenCandidateId ?? undefined,
      },
    };

    const artifact = exportRecommendationArtifacts({
      org: snap.canonical,
      intent: snap.intent,
      gaps,
      candidates: candidatesBundle.candidates,
      validations,
      reviews,
      recommendation,
      baselineComparison: snap.baselineComparison as
        | BaselineProposalComparison
        | undefined,
    });

    recommendation.changeSet.exportArtifactIds = [artifact.id];

    await this.store.appendChange(organizationId, recommendation.changeSet);
    await this.store.appendExport(organizationId, {
      id: artifact.id,
      changeSetId: recommendation.changeSet.id,
      createdAt: nowIso(),
      markdown: artifact.markdown,
      json: artifact.json,
    });

    const refreshed = await this.require(organizationId);
    refreshed.recommendation = recommendation;
    refreshed.eligibility = gate;
    await this.store.save(refreshed);
    return refreshed;
  }

  private async require(organizationId: string): Promise<WorkspaceSnapshot> {
    const snap = await this.store.get(organizationId);
    if (!snap) throw new Error(`Organization not found: ${organizationId}`);
    return snap;
  }
}
