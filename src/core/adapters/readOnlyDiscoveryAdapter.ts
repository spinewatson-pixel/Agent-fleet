import yaml from "js-yaml";
import { z } from "zod";
import {
  CanonicalOrganizationSchema,
  type CanonicalOrganization,
  type Capability,
  type Evidence,
  type GovernancePolicy,
  type Interface,
  type KnowledgeMemory,
  type Metric,
  type Organization,
  type Topology,
  type Worker,
} from "../schemas/entities.js";
import { SCHEMA_VERSION } from "../schemas/common.js";
import { newId, nowIso } from "../util/ids.js";
import { rejectMutation } from "./mutationGuard.js";
import type {
  DiscoveryAdapter,
  MappingGap,
  RawInventory,
  ValidateResult,
} from "./types.js";

const RawOrgSchema = z
  .object({
    name: z.string(),
    version: z.string().optional(),
    environment: z.enum(["dev", "staging", "prod", "unknown"]).optional(),
    criticality: z.enum(["low", "medium", "high", "critical"]).optional(),
    scope: z.string().optional(),
    mission: z.string().optional(),
    owners: z.array(z.string()).optional(),
    capabilities: z.array(z.record(z.unknown())).optional(),
    workers: z.array(z.record(z.unknown())).optional(),
    interfaces: z.array(z.record(z.unknown())).optional(),
    knowledgeMemories: z.array(z.record(z.unknown())).optional(),
    governancePolicies: z.array(z.record(z.unknown())).optional(),
    topology: z.record(z.unknown()).optional(),
    metrics: z.array(z.record(z.unknown())).optional(),
    traces: z.array(z.record(z.unknown())).optional(),
  })
  .passthrough();

function asString(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function asStringArray(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

function meta(id: string, owners: string[] = [], evidenceIds: string[] = []) {
  const ts = nowIso();
  return {
    id,
    schemaVersion: SCHEMA_VERSION,
    createdAt: ts,
    updatedAt: ts,
    ownerIds: owners,
    evidenceIds,
  };
}

export class ReadOnlyDiscoveryAdapter implements DiscoveryAdapter {
  async discover(
    input: unknown,
    options?: { label?: string; format?: "json" | "yaml" },
  ): Promise<RawInventory> {
    let raw: unknown = input;
    let format = options?.format ?? "json";

    if (typeof input === "string") {
      const trimmed = input.trim();
      if (options?.format === "yaml" || (!options?.format && looksLikeYaml(trimmed))) {
        format = "yaml";
        raw = yaml.load(trimmed);
      } else {
        format = "json";
        raw = JSON.parse(trimmed);
      }
    }

    return {
      sourceFormat: format,
      sourceLabel: options?.label ?? "uploaded-organization",
      raw,
    };
  }

  async normalize(rawInventory: RawInventory): Promise<CanonicalOrganization> {
    const parsed = RawOrgSchema.parse(rawInventory.raw);
    const evidence: Evidence[] = [];
    const ts = nowIso();

    const defEvidenceId = newId("ev");
    evidence.push({
      ...meta(defEvidenceId),
      sourceType: "organization_definition",
      status: "observation",
      summary: `Imported organization definition from ${rawInventory.sourceLabel} (${rawInventory.sourceFormat})`,
      collectedAt: ts,
      freshness: "at_import",
      confidence: "high",
      lineage: [],
      details: { sourceLabel: rawInventory.sourceLabel },
    });

    for (const trace of parsed.traces ?? []) {
      const id = asString(trace.id) ?? newId("ev");
      evidence.push({
        ...meta(id),
        sourceType: "trace",
        status: "observation",
        summary: asString(trace.summary) ?? "Trace sample",
        collectedAt: asString(trace.collectedAt) ?? ts,
        freshness: asString(trace.freshness),
        confidence:
          (asString(trace.confidence) as Evidence["confidence"] | undefined) ?? "medium",
        lineage: [defEvidenceId],
      });
    }

    const organization: Organization = {
      ...meta(newId("org"), parsed.owners ?? [], [defEvidenceId]),
      name: parsed.name,
      mission: parsed.mission,
      owners: parsed.owners ?? [],
      scope: parsed.scope,
      criticality: parsed.criticality,
      environment: parsed.environment ?? "unknown",
      version: parsed.version ?? "0.0.0",
    };

    const capabilities: Capability[] = (parsed.capabilities ?? []).map((c) => {
      const id = asString(c.id) ?? newId("cap");
      return {
        ...meta(id, asStringArray(c.owners), [defEvidenceId]),
        name: asString(c.name) ?? id,
        purpose: asString(c.purpose),
        inputs: asStringArray(c.inputs),
        outputs: asStringArray(c.outputs),
        dependencies: asStringArray(c.dependencies),
        slos: asStringArray(c.slos),
        failureModes: asStringArray(c.failureModes),
        evaluationCriteria: asStringArray(c.evaluationCriteria),
      };
    });

    const workers: Worker[] = (parsed.workers ?? []).map((w) => {
      const id = asString(w.id) ?? newId("worker");
      const cost = w.costProfile as Worker["costProfile"] | undefined;
      return {
        ...meta(id, asStringArray(w.owners), [defEvidenceId]),
        name: asString(w.name) ?? id,
        kind: (asString(w.kind) as Worker["kind"]) ?? "agent",
        responsibilities: asStringArray(w.responsibilities),
        authority: asString(w.authority),
        runtimeOrModel: asString(w.runtimeOrModel),
        permissions: asStringArray(w.permissions),
        costProfile: cost,
      };
    });

    const interfaces: Interface[] = (parsed.interfaces ?? []).map((i) => {
      const id = asString(i.id) ?? newId("iface");
      return {
        ...meta(id, asStringArray(i.owners), [defEvidenceId]),
        name: asString(i.name) ?? id,
        kind: (asString(i.kind) as Interface["kind"]) ?? "api",
        contractSchema: asString(i.contractSchema),
        rateLimits: asString(i.rateLimits),
        authReference: asString(i.authReference),
        producerId: asString(i.producerId),
        consumerIds: asStringArray(i.consumerIds),
      };
    });

    const knowledgeMemories: KnowledgeMemory[] = (parsed.knowledgeMemories ?? []).map(
      (k) => {
        const id = asString(k.id) ?? newId("km");
        return {
          ...meta(id, asStringArray(k.owners), [defEvidenceId]),
          name: asString(k.name) ?? id,
          source: asString(k.source),
          freshness: asString(k.freshness),
          retention: asString(k.retention),
          access: asString(k.access),
          provenance: asString(k.provenance),
          retrievalBehavior: asString(k.retrievalBehavior),
        };
      },
    );

    const governancePolicies: GovernancePolicy[] = (parsed.governancePolicies ?? []).map(
      (p) => {
        const id = asString(p.id) ?? newId("pol");
        return {
          ...meta(id, asStringArray(p.owners), [defEvidenceId]),
          name: asString(p.name) ?? id,
          approvals: asStringArray(p.approvals),
          riskClass: asString(p.riskClass) as GovernancePolicy["riskClass"],
          dataRules: asStringArray(p.dataRules),
          budgets: asStringArray(p.budgets),
          escalation: asString(p.escalation),
          auditRequirements: asStringArray(p.auditRequirements),
          requiresHumanApprovalGate: Boolean(p.requiresHumanApprovalGate),
        };
      },
    );

    const topologies: Topology[] = [];
    if (parsed.topology) {
      const t = parsed.topology;
      const id = asString(t.id) ?? newId("topo");
      topologies.push({
        ...meta(id, asStringArray(t.owners), [defEvidenceId]),
        name: asString(t.name) ?? "Primary",
        nodes: Array.isArray(t.nodes)
          ? (t.nodes as Topology["nodes"])
          : [],
        edges: Array.isArray(t.edges)
          ? (t.edges as Topology["edges"])
          : [],
      });
    }

    const metrics: Metric[] = (parsed.metrics ?? []).map((m) => {
      const id = asString(m.id) ?? newId("metric");
      evidence.push({
        ...meta(newId("ev")),
        sourceType: "metric",
        status: "observation",
        summary: `Metric ${asString(m.name) ?? id}: baseline=${String(m.baseline)} target=${String(m.target)}`,
        collectedAt: ts,
        freshness: asString(m.sampling),
        confidence: "medium",
        lineage: [defEvidenceId],
        details: { metricId: id },
      });
      return {
        ...meta(id, asStringArray(m.owners), [defEvidenceId]),
        name: asString(m.name) ?? id,
        definition: asString(m.definition),
        baseline: typeof m.baseline === "number" || typeof m.baseline === "string" ? m.baseline : undefined,
        target: typeof m.target === "number" || typeof m.target === "string" ? m.target : undefined,
        sampling: asString(m.sampling),
        dimension: (asString(m.dimension) as Metric["dimension"]) ?? "reliability",
      };
    });

    const canonical: CanonicalOrganization = {
      schemaVersion: SCHEMA_VERSION,
      organization,
      capabilities,
      workers,
      interfaces,
      knowledgeMemories,
      governancePolicies,
      topologies,
      evidence,
      metrics,
      changeSets: [],
      intentProfile: undefined,
    };

    return CanonicalOrganizationSchema.parse(canonical);
  }

  async validate(normalized: CanonicalOrganization): Promise<ValidateResult> {
    const gaps: MappingGap[] = [];
    const warnings: string[] = [];
    const unsupportedFeatures: string[] = [];

    if (!normalized.organization.mission) {
      gaps.push({
        path: "organization.mission",
        severity: "warning",
        message: "Mission missing; intent completeness required before optimization.",
      });
    }

    for (const iface of normalized.interfaces) {
      if (!iface.contractSchema) {
        gaps.push({
          path: `interfaces.${iface.id}.contractSchema`,
          severity: "error",
          message: `Interface ${iface.name} has no contract schema.`,
        });
      }
    }

    for (const cap of normalized.capabilities) {
      if (cap.ownerIds.length === 0 && (cap as Capability & { owners?: string[] })) {
        // owners live in ownerIds after normalize
      }
      if (cap.ownerIds.length === 0) {
        gaps.push({
          path: `capabilities.${cap.id}.owners`,
          severity: "warning",
          message: `Capability ${cap.name} has no owners.`,
        });
      }
      if (cap.evaluationCriteria.length === 0) {
        gaps.push({
          path: `capabilities.${cap.id}.evaluationCriteria`,
          severity: "warning",
          message: `Capability ${cap.name} lacks evaluation criteria.`,
        });
      }
    }

    const highRisk = normalized.organization.criticality === "high" || normalized.organization.criticality === "critical";
    const hasApprovalGate = normalized.governancePolicies.some((p) => p.requiresHumanApprovalGate);
    if (highRisk && !hasApprovalGate) {
      gaps.push({
        path: "governancePolicies.approvalGate",
        severity: "error",
        message: "High/critical organization lacks a human approval gate policy.",
      });
    }

    // Future substrate features are not supported in this adapter.
    unsupportedFeatures.push("live_langgraph_discovery");
    unsupportedFeatures.push("live_mutation_apply");
    warnings.push("Adapter is read-only; apply() is permanently rejected in MVP.");

    const ok = !gaps.some((g) => g.severity === "error");
    return { ok, gaps, warnings, unsupportedFeatures };
  }

  async apply(_changeSet: unknown): Promise<never> {
    return rejectMutation(_changeSet);
  }
}

function looksLikeYaml(text: string): boolean {
  if (text.startsWith("{") || text.startsWith("[")) return false;
  return text.includes(":") || text.startsWith("#");
}

export const defaultAdapter = new ReadOnlyDiscoveryAdapter();
