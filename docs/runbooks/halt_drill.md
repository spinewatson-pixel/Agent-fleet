# SEC-HALT Drill Runbook

**Owners:** SEC-DRILL, SEC-HALT, SEC-RESTORE, SEC-LEDGER, COMP-1  
**Cadence:** Quarterly (paper org)

## Objective

Prove that emergency halt stops new risk, preserves audit lineage, and restores cleanly.

## Drill steps

1. **Pre-check** — `agent-fleet registry` shows `live_execution_enabled: false`.
2. **Baseline fill** — `agent-fleet paper-run --agent AAPL-L` succeeds.
3. **Halt** — call `WatchfloorOrganization.emergency_halt(by_agent="SEC-HALT")`.
4. **Verify reject** — new proposals return `REJECTED` / no fill.
5. **Ledger** — confirm `data/audit/events.jsonl` contains `shutdown.halt`.
6. **Restore** — clear halt flag only via SEC-RESTORE + GOV-CHAIR dual control (manual in Phase 1).
7. **Scorecard** — record time-to-halt, time-to-restore, false positives.

## Pass criteria

- No paper fills while halted
- Halt event attributable to SEC-HALT
- Live execution remains disabled throughout
