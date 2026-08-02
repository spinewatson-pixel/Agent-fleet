import type { CanonicalOrganization } from "../schemas/entities.js";

export interface RawInventory {
  sourceFormat: "json" | "yaml";
  sourceLabel: string;
  raw: unknown;
}

export interface MappingGap {
  path: string;
  severity: "info" | "warning" | "error";
  message: string;
  unsupported?: boolean;
}

export interface ValidateResult {
  ok: boolean;
  gaps: MappingGap[];
  warnings: string[];
  unsupportedFeatures: string[];
}

/**
 * Adapter boundary. MVP implements read-only discovery only.
 * `apply` is defined for future substrates but must reject mutation.
 */
export interface DiscoveryAdapter {
  discover(input: unknown, options?: { label?: string; format?: "json" | "yaml" }): Promise<RawInventory>;
  normalize(raw: RawInventory): Promise<CanonicalOrganization>;
  validate(normalized: CanonicalOrganization): Promise<ValidateResult>;
  apply?(changeSet: unknown): Promise<never>;
}
