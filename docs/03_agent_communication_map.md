# 03 — Agent-to-Agent Communication Map

All messages use `MessageEnvelope` (`src/agent_fleet/schemas/messages.py`).

## Operating-chain handoffs

| Stage | From | To | MessageType | Payload |
|-------|------|----|-------------|---------|
| Data ingestion | external/paper feed | MKT-INFO-001 | `market_event` | `MarketEvent` |
| Information validation | MKT-INFO-001 | FUND-RES-001, QUANT-RES-001, SYS-INTEL-001 | `market_event` | verified `MarketEvent` |
| Research / signals | FUND-RES-001 / QUANT-RES-001 | STRAT-* | `research_signal` | `ResearchSignal` |
| Strategy proposal | STRAT-* | VAL-IND-001, SYS-INTEL-001 | `trade_proposal` | `TradeProposal` |
| Independent validation | VAL-IND-001 | PORT-RISK-001, SYS-INTEL-001 | `validation_result` | validation + proposal |
| Portfolio / risk | PORT-RISK-001 | CAP-STEW-001, GOV-OPS-001 | `risk_verdict` | portfolio + risk + proposal |
| Stewardship | CAP-STEW-001 | GOV-OPS-001 | `risk_verdict` | + capital_stewardship |
| Governance | GOV-OPS-001 | ARCH-CHIEF-001 | `risk_verdict` | + governance |
| Final approval | ARCH-CHIEF-001 | EXEC-OMS-001, STRAT-*, SYS-INTEL-001 | `approval_decision` | `ApprovalDecision` |
| Execution | EXEC-OMS-001 | MON-LIVE-001, ATTR-001, PORT-RISK-001 | `execution_report` | `ExecutionReport` |
| Monitoring | MON-LIVE-001 | TRADE-OPS-001, PORT-RISK-001 | `monitoring_alert` | `MonitoringAlert` |
| Attribution | ATTR-001 | LEARN-001 | `attribution_report` | `AttributionReport` |
| Controlled improvement | LEARN-001 | QUANT-RES-001, PORT-RISK-001, GOV-OPS-001 | `improvement_proposal` | `ImprovementProposal` |

## Permission highlights

- `STRAT-*` send permission: **`trade_proposal` only** (enforced on `MessageBus`).
- `EXEC-OMS-001` executes only if `ApprovalDecision.execution_authorized == true`.
- Experimental agents may not publish `production_rule` memory writes.
- `SYS-INTEL-001` observes all stages for lineage (does not approve trades).

## Correlation & lineage

- `correlation_id` ties one economic decision from market event → attribution.
- `lineage` lists ancestor `message_id`s.
- `EventStore` append-only audit mirrors every publish.
