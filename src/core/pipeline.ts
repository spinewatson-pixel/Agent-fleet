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
    const demoPath = path.resolve(process.cwd(), "fixtures", "demo-org.yaml");
    const text = fs.readFileSync(demoPath, "utf8");
    return this.importRaw(text, { label: "demo-org.yaml", format: "yaml" });
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
        summary: "Owner updated intent/constraints form",
        collectedAt: ts,
        freshness: "at_statement",
        confidence: "high",
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
      reviewResults,
      snap.intent,
    );

    snap.gapAnalysis = gaps;
    snap.candidates = { candidates, notes };
    snap.validationResults = validationResults;
    snap.reviewResults = reviewResults;
    snap.recommendation = recommendation;
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

    const approvalState =
      decision === "approved" ? ("exported" as const) : ("rejected" as const);

    const recommendation: RecommendationResult = {
      ...base,
      approvalState,
      changeSet: {
        ...base.changeSet,
        approvalState,
        outcome:
          decision === "approved"
            ? "Human approved advisory export. No deployment performed."
            : "Human rejected recommendation. No deployment performed.",
        updatedAt: nowIso(),
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
    await this.store.save(refreshed);
    return refreshed;
  }

  private async require(organizationId: string): Promise<WorkspaceSnapshot> {
    const snap = await this.store.get(organizationId);
    if (!snap) throw new Error(`Organization not found: ${organizationId}`);
    return snap;
  }
}
