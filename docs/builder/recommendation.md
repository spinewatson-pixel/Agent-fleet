# Builder Recommendation — `REC-WATCHFLOOR-MVP-001`

**Org:** `org-watchfloor-quant-lab`  
**Mode:** `advisory_only`  
**Approval:** `pending_human`  
**Chosen:** `CAND-GOV-HARDEN`

## Positioning

> A governed architecture control plane that turns AI systems into explainable, testable, evolvable organizations.

## Problem

Watchfloor is a strong paper trading organization, but lacks a governed architecture control plane loop (intent confidence, formal change sets, twin calibration, and evidence-backed AKB consultation).

## Current state

watchfloor quant lab v0.5.1: 285 workers, 17 capabilities modeled, adapter=watchfloor_readonly

## Preserved strengths

- Paper-only hard gate with live execution locked
- Single executor EXEC-1 after authority chain
- Proposers cannot self-approve or self-execute
- Institutional Design Council as designer/supervisor layer (no trades)
- 25-layer blueprints for every seat
- Watchfloor IDs as canonical naming
- Mode-B human seat HUMAN-1 with veto
- Risk / compliance / stewardship / security veto paths

## Reconstructed intent (unresolved flagged)

- [ ] What external capital / customer mandate applies beyond the paper lab?
- [ ] Which regulatory jurisdiction constraints apply if this ever leaves paper?
- [ ] What numeric success targets define 'effective' for the trading lab?
- [ ] Where is the production broker boundary — never, sandbox-only, or future gated?

## Candidates

### ✓ `CAND-GOV-HARDEN` — Governance Hardening (advisory)

Close ceiling UI gate, formalize change-request lifecycle, deepen evidence provenance, keep paper-only SoD intact.

- Value: Higher trust in architecture map; fewer unsafe structural changes
- Cost: Low engineering cost; mainly control-plane + UI gate
- Risk: Low
- Reversibility: high

### • `CAND-OBS-TWIN` — Observability + Twin Slice

Add architecture telemetry hooks, static twin scenarios, and prediction/outcome calibration without enabling live execution.

- Value: Faster issue→plan cycle; measurable prediction calibration
- Cost: Medium
- Risk: Medium — more moving parts
- Reversibility: medium

## Choice rationale

Selected CAND-GOV-HARDEN for objective=governance_and_reliability: maximizes safety/governance with high reversibility while preserving Watchfloor strengths.

## Why alternatives were not selected

- `CAND-OBS-TWIN`: Higher complexity / cost before governance gaps (ceiling gate, CR lifecycle) close

## Simulation results (predictions, not facts)

- **static/contract_orphan_policy_scan** — PASS: No critical static violations
- **scenario/attempt_enable_live_execution** — PASS: Policy gate must block live_execution_enabled=true; Builder advisory mode refuses apply
- **scenario/candidate_CAND-GOV-HARDEN** — PASS: Preserve list size=8 respected in design; Pattern consultation: 4 patterns
- **scenario/candidate_CAND-OBS-TWIN** — PASS: Preserve list size=8 respected in design; Pattern consultation: 4 patterns

## Independent review

- **intent_fit** `0.75` (conf 0.65): Mission reconstructed from hard rules + org naming; numeric success targets unresolved
- **safety_governance** `0.92` (conf 0.90): Paper-only + SoD + veto chain present
- **reliability_blast_radius** `0.70` (conf 0.60): SPOFs noted: EXEC-1 sole paper executor, HUMAN-1 Mode-B overrides, MEM-1 org memory write path
- **observability** `0.45` (conf 0.70): Audit events exist; architecture drift detection missing
- **cost_capacity** `0.80` (conf 0.60): Agent ceiling 300; roster within ceiling; compute ceiling declared
- **human_operability** `0.85` (conf 0.70): Watchfloor UI + HUMAN-1 Mode B + council artifacts
- **modularity_portability** `0.70` (conf 0.55): Canonical Watchfloor IDs; substrate-specific adapter isolated

## Migration plan (export only — no auto deploy)

Owner: `HUMAN-1`

### Steps
1. Confirm reconstructed intent fields with HUMAN-1 (no guessing)
2. Implement UI agent-ceiling hard gate (CAP-CEIL-GATE)
3. Introduce ChangeSet objects for structural roster changes
4. Wire Builder recommendation artifact into Decision Workspace
5. Keep live_execution_enabled=false; refuse production apply

### Gates
- Human approval (HUMAN-1 / GOV-CHAIR)
- Independent review has no blocking failures
- Paper-only hard rule intact
- No TradeProposal authority granted to Builder

### Rollback
- Revert UI/gate commits
- Restore prior registry version
- Invalidate draft ChangeSets

### Success measures
- Trusted current-state map available in <1 command
- % architectural claims with evidence IDs increases
- Ceiling cannot be silently breached from UI
- Zero live execution enables

## Gap summary

- Missing: CAP-INTENT, CAP-SIM, CAP-OBS, CAP-CHANGE, CAP-AKB, CAP-CEIL-GATE
- Strong: CAP-DISCOVER, CAP-AUTHORITY, CAP-SOD, CAP-BLUEPRINT

## AKB policy

- Consulted before synthesis
- Never updated from unverified simulation/recommendation alone

---
_Builder serves organizations. Learning is a byproduct of verified improvement._
