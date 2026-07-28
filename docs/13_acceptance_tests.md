# 13 — Acceptance Tests Before Advancing Phases

Automated tests live under `tests/acceptance`, `tests/integration`, `tests/unit`.

## Phase 0 → 1

- [x] All required agents present  
- [x] All operating-chain stages owned  
- [x] Veto agents configured; live execution false  
- [x] Strategy contracts forbid self-approve/execute/capital/self-grade  
- [x] Paper chain can produce an authorized fill  
- [x] Stewardship vetoes low-edge proposals  
- [x] Strategies cannot publish approval messages  

## Phase 1 → 2

- [ ] Paper session runner produces daily NAV series  
- [ ] Setup expressions evaluated without `force_setup` escapes in production path  
- [ ] Audit log durable and replayable by `correlation_id`  
- [ ] Regime labels influence proposal admission  

## Phase 2 → 3

- [ ] At least one vendor/paper historical adapter certified  
- [ ] ResearchSignal lineage links to source events  
- [ ] Reconciliation breaks halt new risk  

## Phase 3 → 4

- [ ] Each strategy has OOS package artifact  
- [ ] Overfit gate rejects deliberately overfit toy model  

## Phase 4 → 5

- [ ] Missing information (live) answered  
- [ ] Emergency halt drill signed by GOV + RISK  
- [ ] Explicit deploy authorization document committed or vaulted  
- [ ] Max live notional << paper NAV  

Do not advance phases on narrative confidence. Advance on checked gates only.
