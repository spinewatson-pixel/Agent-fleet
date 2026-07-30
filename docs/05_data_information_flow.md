# 05 — Data-Source and Information-Flow Map

## Logical sources (adapters behind MKT-INFO-001)

| Domain | Examples | Normalization | Consumers |
|--------|----------|---------------|-----------|
| Market bars / quotes | OHLCV, NBBO proxy | `MarketEvent.event_type=bar\|quote` | QUANT, STRAT-MOM/MR/FACTOR/VOL |
| Reference | symbol master, industry map | `reference` tags | FACTOR, PORT-RISK |
| Liquidity | ADV 20d | `liquidity` | all strategies, risk |
| News | wires, filtered web | sentiment tags + source_verified | EARN, SECTOR, VALUE |
| Filings | 10-K/Q, 8-K, ownership | `filings` | VALUE, EARN, FUND-RES |
| Earnings | calendar, EPS surprise | `earnings` | EARN |
| Macro | CPI, NFP, FOMC probs, curve | `macro` | MACRO, SECTOR, VOL |
| Calendars | earnings + macro + dividends | `calendar` | all event strategies |
| Options summary | implied move (optional) | `options_summary` | EARN, VOL |
| Borrow / locate | short availability | via TRADE-OPS | FACTOR shorts |

## Verification rules (Bloomberg-inspired)

1. Reject events with `source_verified=false`.
2. Require `symbol`, `timestamp`, `source`, `event_type`.
3. Tag with instrument, event class, urgency.
4. Prefer dual-source confirm for macro prints before MACRO proposals.
5. Deliver **relevant** slices only (strategies list `required_data_inputs` in contracts).

## Flow

```
Vendor/Paper Feed
   → MKT-INFO-001 (verify, normalize, tag)
   → Feature/Research services (QUANT-RES-001, FUND-RES-001)
   → ResearchSignal
   → STRAT-* (setup detection)
   → TradeProposal
   → control chain
   → paper execution
   → attribution memory (paper | experimental | production buckets)
```

## Phase-1 paper reality

Phase 1 uses a **synthetic verified paper feed** (`source=paper_feed`) sufficient to exercise the chain. Vendor adapters are Phase 2.
