import { z } from "zod";

export const SCHEMA_VERSION = "1.0.0" as const;

export const EvidenceStatusSchema = z.enum([
  "observation",
  "assertion",
  "inference",
  "simulation",
  "recommendation",
]);
export type EvidenceStatus = z.infer<typeof EvidenceStatusSchema>;

export const ConfidenceSchema = z.enum(["low", "medium", "high", "unknown"]);
export type Confidence = z.infer<typeof ConfidenceSchema>;

export const EntityMetaSchema = z.object({
  id: z.string().min(1),
  schemaVersion: z.string().default(SCHEMA_VERSION),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
  ownerIds: z.array(z.string()).default([]),
  evidenceIds: z.array(z.string()).default([]),
});
export type EntityMeta = z.infer<typeof EntityMetaSchema>;

export const OptimizationObjectiveSchema = z.enum([
  "reliability_capability_coverage",
]);
export type OptimizationObjective = z.infer<typeof OptimizationObjectiveSchema>;

export const OperatingModeSchema = z.enum(["advisory_export_only"]);
export type OperatingMode = z.infer<typeof OperatingModeSchema>;

export const MVP_CONFIG = {
  operatingMode: "advisory_export_only" as const,
  optimizationObjective: "reliability_capability_coverage" as const,
  candidateComparisonWeights: {
    intentFit: 0.25,
    reliability: 0.25,
    governance: 0.2,
    observability: 0.1,
    cost: 0.1,
    maintainability: 0.1,
  },
  llmEnabled: false,
} as const;
