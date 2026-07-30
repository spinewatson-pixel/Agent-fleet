# 11 — Backtesting and Paper-Trading Framework

## Paper trading (Phase 1 — implemented)

- Entry point: `Organization.ingest_market_event` / CLI `agent-fleet paper-run`
- Broker: `PaperBroker` (simulated fills, slippage bps)
- Full chain: data → validate → research → propose → validate → portfolio/risk → stewardship → governance → approval → execute → monitor → attribute → learn
- Capital: configurable NAV (default $1M)
- Live execution: disabled

## Backtesting (Phase 2–3 design)

| Stage | Requirement |
|-------|-------------|
| Hypothesis registry | Linked to `QUANT-RES-001` |
| Feature freeze date | No leakage past decision time |
| In-sample / OOS split | Pre-declared |
| Walk-forward | Rolling windows with embargo |
| Costs | Commission + spread + impact model |
| Multiple testing | Deflated Sharpe / holdout family-wise control |
| Promotion | Must beat hurdle after costs OOS |

## Paper promotion gate before limited live

1. Contract complete and reviewed  
2. OOS stats pass `SelfImprovementGate` thresholds  
3. ≥ `min_paper_days` paper trading  
4. Risk + governance approval recorded  
5. Explicit human deploy authorization with max notional  

## Forbidden

- Training on full sample then “testing” on same sample as proof  
- Strategy self-attribution as sole promotion evidence  
- Hot-swapping production parameters from experimental process memory  
