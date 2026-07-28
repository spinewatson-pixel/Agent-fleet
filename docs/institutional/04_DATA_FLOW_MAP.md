# Data-Source and Information-Flow Map

## Sources (logical IDs — adapters pluggable)

| source_id | Category | Fields | Consumers | Verification |
|---|---|---|---|---|
| SRC-MKT-OHLCV | market_price | OHLCV, venue, ts | DATA-VAL → strategies/regime | schema, staleness, outlier |
| SRC-MKT-REF | reference | symbol master, corp actions | DATA-VAL, PORT | vendor checksum |
| SRC-NEWS-WIRE | news | headline, body, ts, symbols | DATA-VAL → RSH-FUND, STRAT-EVT | source allowlist |
| SRC-SEC-FILINGS | filings | 10-K/Q, 8-K, sections | RSH-FUND, STRAT-QUAL | EDGAR hash |
| SRC-EARNINGS | earnings | EPS, surprise, guidance | STRAT-EVT | calendar match |
| SRC-MACRO | macro | CPI, NFP, FOMC, yields | STRAT-MACRO, MON-REGIME | release calendar |
| SRC-CALENDAR | calendar | earnings/econ dates | all event strategies | exchange calendar |

## Flow
1. Ingestion agents attach `source_id` + raw URI.  
2. `DATA-VAL-001` scores quality; emits `data_validated` or drops with governance event.  
3. Research agents only read validated data.  
4. Strategy agents only propose using validated inputs + contract indicators.  
5. Every trade proposal stores `supporting_signal_ids` / `supporting_research_ids` for lineage.

## Delivery SLAs (paper targets)
| Path | SLA |
|---|---|
| OHLCV → validated | ≤ 1s local |
| News → validated | ≤ 5s |
| Research note | event-driven |
| Proposal chain end-to-end | ≤ 2s in-process paper |

## Normalization
- Timestamps → UTC  
- Symbols → canonical ticker  
- Currencies → USD for paper book  
- Corporate actions → adjusted series flag required for backtests
