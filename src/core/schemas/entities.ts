import { z } from "zod";
import { ConfidenceSchema, EntityMetaSchema, EvidenceStatusSchema } from "./common.js";

export const OrganizationSchema = EntityMetaSchema.extend({
  name: z.string().min(1),
  mission: z.string().optional(),
  owners: z.array(z.string()).default([]),
  scope: z.string().optional(),
  criticality: z.enum(["low", "medium", "high", "critical"]).optional(),
  environment: z.enum(["dev", "staging", "prod", "unknown"]).default("unknown"),
  version: z.string().default("0.0.0"),
});
export type Organization = z.infer<typeof OrganizationSchema>;

export const CapabilitySchema = EntityMetaSchema.extend({
  name: z.string().min(1),
  purpose: z.string().optional(),
  inputs: z.array(z.string()).default([]),
  outputs: z.array(z.string()).default([]),
  dependencies: z.array(z.string()).default([]),
  slos: z.array(z.string()).default([]),
  failureModes: z.array(z.string()).default([]),
  evaluationCriteria: z.array(z.string()).default([]),
});
export type Capability = z.infer<typeof CapabilitySchema>;

export const WorkerKindSchema = z.enum([
  "agent",
  "human",
  "workflow",
  "service",
  "tool",
]);
export type WorkerKind = z.infer<typeof WorkerKindSchema>;

export const WorkerSchema = EntityMetaSchema.extend({
  name: z.string().min(1),
  kind: WorkerKindSchema,
  responsibilities: z.array(z.string()).default([]),
  authority: z.string().optional(),
  runtimeOrModel: z.string().optional(),
  permissions: z.array(z.string()).default([]),
  costProfile: z
    .object({
      unit: z.string().optional(),
      estimate: z.number().optional(),
      notes: z.string().optional(),
    })
    .optional(),
});
export type Worker = z.infer<typeof WorkerSchema>;

export const InterfaceKindSchema = z.enum([
  "api",
  "event",
  "queue",
  "file",
  "ui",
]);
export type InterfaceKind = z.infer<typeof InterfaceKindSchema>;

export const InterfaceSchema = EntityMetaSchema.extend({
  name: z.string().min(1),
  kind: InterfaceKindSchema,
  contractSchema: z.string().optional(),
  rateLimits: z.string().optional(),
  authReference: z.string().optional(),
  producerId: z.string().optional(),
  consumerIds: z.array(z.string()).default([]),
});
export type Interface = z.infer<typeof InterfaceSchema>;

export const KnowledgeMemorySchema = EntityMetaSchema.extend({
  name: z.string().min(1),
  source: z.string().optional(),
  freshness: z.string().optional(),
  retention: z.string().optional(),
  access: z.string().optional(),
  provenance: z.string().optional(),
  retrievalBehavior: z.string().optional(),
});
export type KnowledgeMemory = z.infer<typeof KnowledgeMemorySchema>;

export const GovernancePolicySchema = EntityMetaSchema.extend({
  name: z.string().min(1),
  approvals: z.array(z.string()).default([]),
  riskClass: z.enum(["low", "medium", "high", "critical"]).optional(),
  dataRules: z.array(z.string()).default([]),
  budgets: z.array(z.string()).default([]),
  escalation: z.string().optional(),
  auditRequirements: z.array(z.string()).default([]),
  requiresHumanApprovalGate: z.boolean().default(false),
});
export type GovernancePolicy = z.infer<typeof GovernancePolicySchema>;

export const TopologyNodeSchema = z.object({
  id: z.string(),
  refId: z.string(),
  kind: z.enum(["worker", "capability", "interface", "knowledge", "policy"]),
  label: z.string(),
});
export type TopologyNode = z.infer<typeof TopologyNodeSchema>;

export const TopologyEdgeSchema = z.object({
  id: z.string(),
  from: z.string(),
  to: z.string(),
  kind: z.enum(["communication", "delegation", "dependency", "approval"]),
  label: z.string().optional(),
});
export type TopologyEdge = z.infer<typeof TopologyEdgeSchema>;

export const TopologySchema = EntityMetaSchema.extend({
  name: z.string().min(1),
  nodes: z.array(TopologyNodeSchema).default([]),
  edges: z.array(TopologyEdgeSchema).default([]),
});
export type Topology = z.infer<typeof TopologySchema>;

export const EvidenceSchema = EntityMetaSchema.extend({
  sourceType: z.enum([
    "organization_definition",
    "trace",
    "metric",
    "owner_statement",
    "knowledge_rule",
    "engine_output",
  ]),
  status: EvidenceStatusSchema,
  summary: z.string(),
  collectedAt: z.string().datetime(),
  freshness: z.string().optional(),
  confidence: ConfidenceSchema.default("unknown"),
  lineage: z.array(z.string()).default([]),
  details: z.record(z.unknown()).optional(),
});
export type Evidence = z.infer<typeof EvidenceSchema>;

export const MetricDimensionSchema = z.enum([
  "quality",
  "latency",
  "reliability",
  "safety",
  "cost",
]);
export type MetricDimension = z.infer<typeof MetricDimensionSchema>;

export const MetricSchema = EntityMetaSchema.extend({
  name: z.string().min(1),
  definition: z.string().optional(),
  baseline: z.union([z.number(), z.string()]).optional(),
  target: z.union([z.number(), z.string()]).optional(),
  sampling: z.string().optional(),
  dimension: MetricDimensionSchema,
});
export type Metric = z.infer<typeof MetricSchema>;

export const ApprovalStateSchema = z.enum([
  "draft",
  "pending_review",
  "approved",
  "rejected",
  "exported",
]);
export type ApprovalState = z.infer<typeof ApprovalStateSchema>;

export const ChangeSetSchema = EntityMetaSchema.extend({
  proposal: z.string(),
  affectedEntityIds: z.array(z.string()).default([]),
  predictedImpact: z.string().optional(),
  approvalState: ApprovalStateSchema.default("draft"),
  rollout: z.string().optional(),
  rollback: z.string().optional(),
  outcome: z.string().optional(),
  candidateId: z.string().optional(),
  exportArtifactIds: z.array(z.string()).default([]),
});
export type ChangeSet = z.infer<typeof ChangeSetSchema>;

export const IntentFieldConfidenceSchema = z.record(ConfidenceSchema);

export const IntentProfileSchema = EntityMetaSchema.extend({
  mission: z.string().optional(),
  successMeasures: z.array(z.string()).default([]),
  constraints: z.array(z.string()).default([]),
  riskTolerance: z.enum(["low", "medium", "high", "unknown"]).default("unknown"),
  preserveList: z.array(z.string()).default([]),
  unresolvedQuestions: z.array(z.string()).default([]),
  fieldConfidence: IntentFieldConfidenceSchema.default({}),
  confirmed: z.boolean().default(false),
});
export type IntentProfile = z.infer<typeof IntentProfileSchema>;

export const CanonicalOrganizationSchema = z.object({
  schemaVersion: z.string(),
  organization: OrganizationSchema,
  capabilities: z.array(CapabilitySchema).default([]),
  workers: z.array(WorkerSchema).default([]),
  interfaces: z.array(InterfaceSchema).default([]),
  knowledgeMemories: z.array(KnowledgeMemorySchema).default([]),
  governancePolicies: z.array(GovernancePolicySchema).default([]),
  topologies: z.array(TopologySchema).default([]),
  evidence: z.array(EvidenceSchema).default([]),
  metrics: z.array(MetricSchema).default([]),
  changeSets: z.array(ChangeSetSchema).default([]),
  intentProfile: IntentProfileSchema.optional(),
});
export type CanonicalOrganization = z.infer<typeof CanonicalOrganizationSchema>;

export const KnowledgeObjectSchema = z.object({
  id: z.string(),
  domain: z.string(),
  claimOrPattern: z.string(),
  applicability: z.string(),
  counterexamples: z.array(z.string()).default([]),
  confidence: ConfidenceSchema,
  sourceReference: z.string(),
  version: z.string(),
  status: z.enum(["draft", "reviewed", "deprecated"]),
  reviewDate: z.string(),
});
export type KnowledgeObject = z.infer<typeof KnowledgeObjectSchema>;
