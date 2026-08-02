import type { CanonicalOrganization, IntentProfile } from "../schemas/entities.js";
import { SCHEMA_VERSION, type Confidence } from "../schemas/common.js";
import { newId, nowIso } from "../util/ids.js";

export interface IntentCompletenessResult {
  profile: IntentProfile;
  unresolvedQuestions: string[];
  isComplete: boolean;
}

/**
 * Emits specific unresolved questions. Never fabricates mission, risk, or success metrics.
 */
export function evaluateIntentCompleteness(
  org: CanonicalOrganization,
  ownerInput?: Partial<IntentProfile>,
): IntentCompletenessResult {
  const ts = nowIso();
  const existing = org.intentProfile;
  const mission = ownerInput?.mission ?? existing?.mission ?? org.organization.mission;
  const successMeasures =
    ownerInput?.successMeasures ?? existing?.successMeasures ?? [];
  const constraints = ownerInput?.constraints ?? existing?.constraints ?? [];
  const riskTolerance =
    ownerInput?.riskTolerance ?? existing?.riskTolerance ?? "unknown";
  const preserveList = ownerInput?.preserveList ?? existing?.preserveList ?? [];
  const confirmed = ownerInput?.confirmed ?? existing?.confirmed ?? false;

  const unresolvedQuestions: string[] = [];
  const fieldConfidence: Record<string, Confidence> = {
    ...(existing?.fieldConfidence ?? {}),
    ...(ownerInput?.fieldConfidence ?? {}),
  };

  // Owner statements are assertions: medium confidence unless corroborated by observation.
  const assertionConfidence: Confidence = "medium";

  if (!mission || mission.trim().length === 0) {
    unresolvedQuestions.push(
      "What is the organization's mission in one sentence? (Do not invent; owner must state it.)",
    );
    fieldConfidence.mission = "unknown";
  } else if (ownerInput?.mission) {
    fieldConfidence.mission = assertionConfidence;
  } else {
    fieldConfidence.mission = fieldConfidence.mission ?? assertionConfidence;
  }

  if (successMeasures.length === 0) {
    unresolvedQuestions.push(
      "Which success measures define good outcomes (e.g., reliability target, capability coverage)?",
    );
    fieldConfidence.successMeasures = "unknown";
  } else if (ownerInput?.successMeasures) {
    fieldConfidence.successMeasures = assertionConfidence;
  } else {
    fieldConfidence.successMeasures = fieldConfidence.successMeasures ?? assertionConfidence;
  }

  if (riskTolerance === "unknown") {
    unresolvedQuestions.push(
      "What is the risk tolerance for autonomous actions (low / medium / high)?",
    );
    fieldConfidence.riskTolerance = "unknown";
  } else if (ownerInput?.riskTolerance) {
    fieldConfidence.riskTolerance = assertionConfidence;
  } else {
    fieldConfidence.riskTolerance = fieldConfidence.riskTolerance ?? assertionConfidence;
  }

  if (constraints.length === 0) {
    unresolvedQuestions.push(
      "What hard constraints must architecture changes respect (data residency, human approval, budget)?",
    );
    fieldConfidence.constraints = "unknown";
  } else if (ownerInput?.constraints) {
    fieldConfidence.constraints = assertionConfidence;
  } else {
    fieldConfidence.constraints = fieldConfidence.constraints ?? assertionConfidence;
  }

  if (preserveList.length === 0) {
    unresolvedQuestions.push(
      "Which current strengths or components must be preserved?",
    );
    fieldConfidence.preserveList = "unknown";
  } else if (ownerInput?.preserveList) {
    fieldConfidence.preserveList = assertionConfidence;
  } else {
    fieldConfidence.preserveList = fieldConfidence.preserveList ?? assertionConfidence;
  }

  if (!org.organization.scope) {
    unresolvedQuestions.push("What is the in-scope boundary for this organization?");
    fieldConfidence.scope = "unknown";
  }

  if (!org.organization.criticality) {
    unresolvedQuestions.push("What is the business criticality (low/medium/high/critical)?");
    fieldConfidence.criticality = "unknown";
  }

  const profile: IntentProfile = {
    id: existing?.id ?? newId("intent"),
    schemaVersion: SCHEMA_VERSION,
    createdAt: existing?.createdAt ?? ts,
    updatedAt: ts,
    ownerIds: org.organization.owners,
    evidenceIds: ownerInput?.evidenceIds ?? existing?.evidenceIds ?? [],
    mission,
    successMeasures,
    constraints,
    riskTolerance,
    preserveList,
    unresolvedQuestions,
    fieldConfidence,
    confirmed: confirmed && unresolvedQuestions.length === 0,
  };

  return {
    profile,
    unresolvedQuestions,
    isComplete: unresolvedQuestions.length === 0 && profile.confirmed,
  };
}
