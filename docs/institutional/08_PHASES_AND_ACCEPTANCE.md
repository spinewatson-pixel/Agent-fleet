# Implementation Sequence and Acceptance Tests

## Phase 0 — Bootstrap (current)
**Deliverables:** contracts, bus, authority maps, paper chain, risk engine, learning FSM, docs, tests.  
**Acceptance**
- [ ] All provisional agents have operating contracts exportable to JSON
- [ ] Strategy contracts cannot hold APPROVE or execution permissions
- [ ] Paper proposal chain stages complete in order
- [ ] Risk rejects over-limit proposals
- [ ] Steward rejects empty thesis
- [ ] Live order with `paper=False` raises
- [ ] Learning stages cannot skip
- [ ] `LIVE_EXECUTION_ENABLED is False`

## Phase 1 — Data & research depth
**Deliverables:** real data adapters, validation rules, research note pipeline, persistence of audit log.  
**Acceptance**
- [ ] Validated data required before proposal acceptance
- [ ] Source allowlist enforced
- [ ] Audit log durable across restart

## Phase 2 — Strategy realism
**Deliverables:** replace provisional strategies with operator’s real skeletons; indicator engines; regime classifier.  
**Acceptance**
- [ ] Each strategy: backtest + OOS report stored
- [ ] Regime gate blocks invalid regimes
- [ ] Paper run ≥ N days with stable ops

## Phase 3 — Portfolio stress & monitoring
**Deliverables:** correlation model, stress scenarios, full monitor/close loop.  
**Acceptance**
- [ ] Stress suite pass
- [ ] Emergency halt drill pass
- [ ] Reconciliation report daily

## Phase 4 — Live shadow (no capital)
**Deliverables:** broker read-only + shadow orders.  
**Acceptance**
- [ ] Shadow vs paper attribution within tolerance
- [ ] GOV+RISK written approval artifact

## Phase 5 — Limited live capital (explicit authorization only)
**Deliverables:** enable `EXEC-LIVE-001` with tiny limits.  
**Acceptance**
- [ ] Human authorization recorded
- [ ] Dual control enablement
- [ ] Kill-switch drill within 60s

**Do not advance phases without green acceptance tests.**
