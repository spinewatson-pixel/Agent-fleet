# 12 — Implementation Sequence (Phases)

## Phase 0 — Foundation (done in this PR)

- Schemas, authority matrix, event/memory stores, message bus  
- Institutional + strategy contracts  
- Paper broker + operating pipeline  
- Unit/integration/acceptance tests  
- Design council documents  

**Exit criteria:** acceptance tests green; live flags false.

## Phase 1 — Paper organization hardening

- Persist audit log to disk by default  
- Deterministic feature evaluation (parse setup expressions)  
- Daily paper session runner + PnL marks  
- Regime classifier stub → real rules  

**Exit:** multi-day paper session report; no permission escapes.

## Phase 2 — Data & research infrastructure

- Vendor adapters behind MKT-INFO-001  
- Feature store + research notebook/report pipeline  
- Reconciliation agent  
- Cost model  

**Exit:** verified historical replay for ≥1 year liquid US equities.

## Phase 3 — Backtest & validation factory

- Walk-forward harness  
- Stress library  
- Crowding / capacity checks  

**Exit:** each active strategy has OOS package meeting gates.

## Phase 4 — Extended paper with human review UI/API

- Dashboards for proposals, vetoes, incidents  
- Human escalation channel  

**Exit:** 20+ trading days stable paper ops.

## Phase 5 — Limited live (optional, gated)

- Requires answers in `01_missing_information.md`  
- Explicit written authorization (max notional, accounts)  
- Flip live flags only under change-controlled release  
- Start with tiny capital; stewardship + risk veto remain  

**Exit:** limited live with emergency halt proven in drill.

Autonomous live at full capital is **out of scope** until Phase 5+ evidence exists.
