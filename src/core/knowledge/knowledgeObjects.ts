import type { KnowledgeObject } from "../schemas/entities.js";

/** Small cited rule set used by deterministic engines. Not a full research corpus. */
export const KNOWLEDGE_OBJECTS: KnowledgeObject[] = [
  {
    id: "ko_topology_no_universal_best",
    domain: "topology",
    claimOrPattern:
      "Topology selection must match workload coupling and governance constraints; there is no universally best topology.",
    applicability: "Candidate synthesis and architecture review",
    counterexamples: [
      "Homogeneous batch jobs with identical SLOs may converge on one pattern temporarily",
    ],
    confidence: "high",
    sourceReference: "MVP knowledge fixture — topology selection",
    version: "1.0.0",
    status: "reviewed",
    reviewDate: "2026-08-01",
  },
  {
    id: "ko_delegation_contract_integrity",
    domain: "contracts",
    claimOrPattern:
      "Preserve context and contract integrity at delegation boundaries.",
    applicability: "Gap analysis for interfaces and topology edges",
    counterexamples: [],
    confidence: "high",
    sourceReference: "MVP knowledge fixture — delegation boundaries",
    version: "1.0.0",
    status: "reviewed",
    reviewDate: "2026-08-01",
  },
  {
    id: "ko_readonly_before_mutation",
    domain: "governance",
    claimOrPattern:
      "Perform read-only discovery and human review before any mutation path.",
    applicability: "Adapter boundary and recommendation export",
    counterexamples: [],
    confidence: "high",
    sourceReference: "MVP knowledge fixture — read-only first",
    version: "1.0.0",
    status: "reviewed",
    reviewDate: "2026-08-01",
  },
  {
    id: "ko_simulation_bounded",
    domain: "validation",
    claimOrPattern:
      "Simulation and scenario results are bounded predictions under declared fidelity, not proof of production behavior.",
    applicability: "Validation engine output limitations",
    counterexamples: [],
    confidence: "high",
    sourceReference: "MVP knowledge fixture — declared fidelity",
    version: "1.0.0",
    status: "reviewed",
    reviewDate: "2026-08-01",
  },
  {
    id: "ko_critical_governance_blocks",
    domain: "governance",
    claimOrPattern:
      "Critical governance failures block a recommendation and must not be averaged into a pass.",
    applicability: "Independent architecture review",
    counterexamples: [],
    confidence: "high",
    sourceReference: "MVP knowledge fixture — non-averaging blockers",
    version: "1.0.0",
    status: "reviewed",
    reviewDate: "2026-08-01",
  },
  {
    id: "ko_outcomes_promote_knowledge",
    domain: "learning",
    claimOrPattern:
      "Production outcomes and human review are required before promoting patterns into reusable knowledge.",
    applicability: "Change history and knowledge lifecycle",
    counterexamples: [],
    confidence: "medium",
    sourceReference: "MVP knowledge fixture — knowledge promotion",
    version: "1.0.0",
    status: "reviewed",
    reviewDate: "2026-08-01",
  },
];

export function getKnowledgeObject(id: string): KnowledgeObject | undefined {
  return KNOWLEDGE_OBJECTS.find((k) => k.id === id);
}
