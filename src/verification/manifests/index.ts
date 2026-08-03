import { agentFleetManifest } from "./agentFleet.js";
import { nursingEcosystemManifest } from "./nursingEcosystem.js";
import type { ProjectManifest } from "../types.js";

/**
 * Every ecosystem the framework verifies.
 *
 * Adding a project is one entry here plus a manifest file. Nothing else in the
 * framework knows what language a project is written in — a gate is a command
 * that prints JSON.
 */
export const MANIFESTS: ProjectManifest[] = [
  agentFleetManifest,
  nursingEcosystemManifest,
];

export function getManifest(projectId: string): ProjectManifest | undefined {
  return MANIFESTS.find((m) => m.id === projectId);
}

export { agentFleetManifest, nursingEcosystemManifest };
