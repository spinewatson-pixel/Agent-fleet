# Agent-to-Agent Communication Map

## Transport
In-process `MessageBus` with append-only `audit_log`. Every message is an `Envelope`:

```
message_id, correlation_id, causation_id, message_type,
source_agent_id, target_agent_ids[], created_at, schema_version,
environment, payload, audit_tags[]
```

## Primary flows

```
DATA-MKT-001 --market_data--> DATA-VAL-001 --data_validated--> STRAT-*, RSH-*, MON-REGIME-001
DATA-NEWS-001 --news_event--> DATA-VAL-001 --data_validated--> RSH-FUND-001, STRAT-EVT-001, STRAT-MACRO-001

RSH-FUND-001 --research_note/signal--> STRAT-EVT-001, STRAT-QUAL-001, STRAT-MACRO-001, STRAT-SECROT-001
RSH-QUANT-001 --signal--> STRAT-MOM-001, STRAT-MR-001, STRAT-PAIRS-001

STRAT-* --trade_proposal--> SIG-VAL-001 --validation_result--> PORT-ALLOC-001
PORT-ALLOC-001 --portfolio_evaluation--> RISK-APPR-001
RISK-APPR-001 --risk_decision--> CAP-STEW-001, EXEC-PAPER-001
CAP-STEW-001 --capital_steward_decision--> EXEC-PAPER-001

EXEC-PAPER-001 --execution_order/fill_report--> MON-LIVE-001, REV-ATTR-001, PORT-ALLOC-001
REV-ATTR-001 --attribution_report--> LEARN-CTRL-001, GOV-COMP-001
LEARN-CTRL-001 --improvement_proposal--> RISK-APPR-001, GOV-COMP-001

RISK-APPR-001|GOV-COMP-001 --emergency_halt--> *
```

## Required message types by stage
See `src/agent_fleet/messaging/schemas.py` for exact payloads:
`TradeProposalPayload`, `ValidationResultPayload`, `PortfolioEvaluationPayload`,
`RiskDecisionPayload`, `CapitalStewardDecisionPayload`, `ExecutionOrderPayload`,
`FillReportPayload`, `AttributionReportPayload`, `ImprovementProposalPayload`.

## Forbidden channels
- Strategy → Execution (direct)
- Strategy → Broker
- Experimental → Production rule store
- Any agent spoofing `source_agent_id`
