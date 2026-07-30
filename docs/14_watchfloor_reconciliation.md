# Watchfloor Reconciliation

## Correction to prior audit

Prior audit treated the repo as empty. The user has a complete Watchfloor Quant Lab org UI (agent skeletons across Mission Control, Global Intel, Predictions, Trading Floor, Lab, Quant Research, Fund Floor, Great Minds, Learning Loop, Data Core, Perimeter, Contractors).

## What was preserved

- Full division/department/agent roster → config/watchfloor_registry.json (279 agents)
- Paper sandbox, thesis-before-trade, $1-2 sizing, swing ≤1 week, agent ceiling 150
- Human Mode B veto, RISK-1/COMP-1 halt, SEC-HALT kill switch
- Quant wing thesis-exempt; discretionary thesis-required

## Institutional council mapped onto Watchfloor seats

| Institutional council | Watchfloor seat IDs |
|---|---|
| Palantir Systems Intelligence | MEM-1, DQ-1, UI-1, TOOL-1 |
| Bloomberg Market Information | MKT-1, ALT-1, GEO-1, MACRO-1 |
| NVIDIA AI Infrastructure | ML-ARCH, ML-VIT, ML-SEQ, TOOL-1 |
| BlackRock Portfolio Risk | RISK-1, CAP-1, CORR-Q |
| Citadel Trading Operations | HEAD-TRADE, EXEC-1, CIT-RISK, CIT-ALLOC |
| Renaissance Quantitative Research | MINE-1, ENS-1, FIT-1, COST-1, BACK-1, STAT-1 |
| Goldman Research Strategy | CORP-1, BULL-1, BEAR-1, FORE-1, HEAD-INTEL |
| JPMorgan Governance Operations | GOV-CHAIR, COMP-1, SEC-HALT, SEC-LEDGER, HUMAN-1 |
| Berkshire Capital Stewardship | BRK-MOAT, BRK-SAFE, BRK-MRKT, BRK-INV, BRK-TRD1, BRK-TRD2 |

Source: `config/watchfloor_registry.json` → `institutional_council_map`.

## Operating chain owners in Watchfloor IDs

Data ingestion: MKT-1, ALT-1, DQ-1  
Research: intel + pred agents  
Signal: FORE-1, CHAIN-*, MINE-*, sector desks  
Strategy proposal: trade Group A-G + fund traders + RT-* quant traders  
Independent validation: FIT-1, STAT-1, RED-*  
Portfolio evaluation: RISK-1, CAP-1, CORR-Q  
Risk approval: RISK-1, COMP-1, CIT-RISK, GOV-CHAIR, HUMAN-1  
Execution: EXEC-1 only (paper)  
Monitoring: COMP-1, RISK-1, SEC-*  
Attribution: ATTR-1, CALIB-1  
Controlled improvement: SYNTH-1, ARCH-1, LIFE-1, LEARN gates

## Provisional STRAT-* agents

The earlier provisional STRAT-MOM/MR/... roster is RETIRED as primary. Keep as optional benchmark aliases only if needed for tests; Watchfloor IDs are canonical.

## Non-negotiables retained

Strategies propose only; EXEC-1 executes authorized paper only; live disabled; experimental cannot mutate production.
