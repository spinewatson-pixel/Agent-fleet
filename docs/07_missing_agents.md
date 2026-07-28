# 07 — Missing Agents That Must Be Added

Relative to an institutional paper org, these were **absent** (repo empty) and are now introduced:

## Control plane (required)

| ID | Why required |
|----|--------------|
| ARCH-CHIEF-001 | Conflict resolution + final ApprovalDecision + live lock |
| SYS-INTEL-001 | Lineage, permissions graph, audit |
| MKT-INFO-001 | Verified data ingestion |
| AI-INFRA-001 | Compute/model routing placeholder + health |
| PORT-RISK-001 | Binding portfolio/risk decisions |
| TRADE-OPS-001 | Regime + multi-strategy ops |
| QUANT-RES-001 | Validation standards / features / anti-overfit |
| FUND-RES-001 | Fundamental/event research → signals |
| GOV-OPS-001 | Compliance, shutdown, escalation |
| CAP-STEW-001 | Long-term quality + activity veto |
| VAL-IND-001 | Independent validation (cannot be the proposing strategy) |
| EXEC-OMS-001 | Execution separated from strategy |
| MON-LIVE-001 | Post-entry monitoring |
| ATTR-001 | Independent performance measurement |
| LEARN-001 | Controlled improvement gate |

## Strategy plane (provisional roster)

Eight `STRAT-*` agents (see org map). Replace if you supply prior skeletons.

## Not yet implemented (Phase 2+)

| Future agent | Purpose |
|--------------|---------|
| RECON-001 | Cash/position reconciliation vs broker |
| COMPLIANCE-LIST-001 | Restricted-list enforcement service |
| DATA-QA-001 | Dedicated dual-source macro confirmation |
| COST-MODEL-001 | Transaction cost model distinct from EXEC |
| HUMAN-ESC-001 | Human-in-the-loop escalation inbox adapter |

These are scheduled; paper org can run without them with documented risk.
