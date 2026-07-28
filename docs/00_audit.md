# 00 — Audit of Current Agent Setup

**Council date:** 2026-07-28  
**Subject repository:** `spinewatson-pixel/Agent-fleet`  
**Environment under review:** `main` @ initial commit `6fbef43`

## Finding (Chief Architecture)

The repository contains **no executable multi-agent trading system**. The only artifact is:

```
README.md  →  "# Agent-fleet"
```

There are no agent skeletons, strategy modules, message schemas, risk controls, data connectors, tests, or deployment configs in git history.

**Implication:** The Institutional Design Council cannot “preserve existing agent wiring” because none exists in this repository. Useful components to preserve are limited to:

| Component | Status | Council action |
|-----------|--------|----------------|
| Repository name / identity (`Agent-fleet`) | Present | Keep |
| README stub | Present | Replace with institutional operating README |
| Implied intent (multi-agent trading fleet) | Inferred from user brief | Materialize as contracts + paper org |

## Independent institutional audits

### Palantir-inspired Systems Intelligence (`SYS-INTEL-001`)
- **Missing:** decision graph, data lineage, permissions model, audit event store, shared context bus.
- **Weakness:** unnamed agents cannot be mapped into a connected decision system.
- **Recommendation:** adopt `MessageEnvelope` + append-only `EventStore` as the system of record for every handoff.

### Bloomberg-inspired Market Information (`MKT-INFO-001`)
- **Missing:** market feeds, news/filings/earnings/macro calendars, source verification, normalization, tagging, agent-specific delivery.
- **Recommendation:** define `MarketEvent` contract first; wire paper feed; defer vendor APIs behind adapters.

### NVIDIA-inspired AI Infrastructure (`AI-INFRA-001`)
- **Missing:** model routing, compute plan, inference SLOs, embeddings store, local/cloud split, failover.
- **Recommendation:** Phase 0–1 runs deterministic agents locally (no LLM required for paper path). Reserve model-routing interface for Phase 2+.

### BlackRock-inspired Portfolio & Risk (`PORT-RISK-001`)
- **Missing:** capital allocation, exposure/correlation limits, stress tests, drawdown halts, liquidity caps.
- **Unsafe default if built naively:** strategy-local sizing treated as binding capital.
- **Recommendation:** strategies emit *suggested* size only; `PORT-RISK-001` owns binding limits and veto.

### Citadel-inspired Trading Operations (`TRADE-OPS-001`)
- **Missing:** OMS, regime engine, slippage ledger, multi-strategy coordination.
- **Recommendation:** paper OMS (`EXEC-OMS-001`) with hard `live_execution_enabled=false`.

### Renaissance-inspired Quant Research (`QUANT-RES-001`)
- **Missing:** hypothesis registry, feature store, OOS/walk-forward harness, multiple-testing controls.
- **Recommendation:** controlled improvement pipeline; no production self-mutation.

### Goldman-inspired Research & Strategy (`FUND-RES-001`)
- **Missing:** standardized research→signal schema.
- **Recommendation:** `ResearchSignal` as the only research output strategies may consume.

### JPMorgan-inspired Governance (`GOV-OPS-001`)
- **Missing:** approval authority, reconciliation, incident management, escalation, documentation.
- **Recommendation:** governance veto + shutdown switch; mandatory audit on every message.

### Berkshire-inspired Capital Stewardship (`CAP-STEW-001`)
- **Missing:** quality/valuation discipline; activity veto against trading-for-its-own-sake.
- **Recommendation:** edge/cost hurdle + short-horizon low-conviction veto.

## Cross-critique summary

| Team | Critique of others | Resolution by `ARCH-CHIEF-001` |
|------|--------------------|--------------------------------|
| Risk vs Trading Ops | Ops wanted strategy-local kill switches; Risk requires portfolio-level halt primacy | Portfolio halt overrides strategy; Ops may pause sleeves |
| Quant vs Fundamental | Competing signal formats | Single `ResearchSignal` schema; both may publish |
| Stewardship vs Momentum/MR | Stewardship argued short-horizon strategies are harmful | Keep MR/MOM in paper roster with stewardship veto on low edge/conviction |
| Infra vs Info | Infra proposed cloud-first; Info needs offline paper replay | Local-first paper; cloud adapters optional |

**Vetoes exercised:** Risk + Governance veto any design where strategies approve/execute/self-grade. Stewardship vetoes designs that incentivize fill-rate over expected edge.

## Unified design decision

Build a **paper-trading institutional organization** with:

1. Nine departmental supervisors + chief architecture  
2. Eight strategy agents with complete operating contracts  
3. Independent validation → portfolio/risk → stewardship → governance → execution chain  
4. Live execution **disabled** until Phase 5 explicit authorization  

Evidence: empty repo audit; user-mandated operating chain; separation of propose / approve / execute / review roles.
