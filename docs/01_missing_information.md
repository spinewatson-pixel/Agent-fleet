# 01 — Missing Information Required From You

The council proceeded with **documented defaults** so paper trading can function. Answer these only where you want to override defaults — they block *live* readiness, not Phase-1 paper.

## Blocking for live capital (not for paper)

1. **Brokerage / custody**: which paper and live brokers, account IDs, and who holds deploy keys?
2. **Capital mandate**: starting NAV, max drawdown before human halt, legal entity / strategy mandate?
3. **Asset universe**: exact ticker lists or index membership rules per strategy (defaults use liquidity tags)?
4. **Data vendors**: market data, fundamentals, news, filings, options — contracts and redistribution rights?
5. **Compliance constraints**: restricted lists, shorting allowed?, PDT/pattern rules, jurisdiction?
6. **Explicit live-enable authorization**: written approval that Phase-5 limited live may turn on (must name max notional).

## Important for strategy fidelity (paper can use defaults)

7. Did you already have named strategy agents elsewhere (other repo/docs)? If yes, provide IDs and rules so we replace the provisional eight.
8. Preferred holding-period mix (e.g., more value, less mean-reversion)?
9. Sector/geography exclusions (e.g., no biotech, no China ADRs)?
10. Benchmark for attribution (SPY, custom)?
11. Correlation clustering method preference (historical 60d equity, factor model, both)?
12. Who is the human escalation owner for `GOV-OPS-001` incidents (name/email)?

## Defaults assumed until you override

| Item | Default |
|------|---------|
| Environment | Paper only, `$1,000,000` NAV |
| Live execution | Hard-disabled |
| Universe | US liquid equities / sector & index ETFs as tagged in contracts |
| Slippage model | Flat 5 bps paper |
| Risk limits | See `config/organization.yaml` |
| Strategy roster | MOM, MR, EARN, MACRO, FACTOR, VALUE, VOL, SECTOR |
| Improvement | Propose-only; no auto production mutation |

No further questions are required to continue Phase-1 paper organization work.
