# 04 — Authority and Approval Map

## Principle

> Strategy agents propose trades. They do **not** independently determine capital limits, approve their own trades, execute orders, or evaluate their own performance.

## Binding approval chain

```
STRAT-* proposal
    → VAL-IND-001 (reject malformed / incomplete)
    → PORT-RISK-001 (approve | reduce | reject | pause | close)   [VETO]
    → CAP-STEW-001 (approve | reduce | reject | pause)            [VETO]
    → GOV-OPS-001 (approve | reject | pause | shutdown)           [VETO]
    → ARCH-CHIEF-001 (emits ApprovalDecision; live deploy lock)
    → EXEC-OMS-001 (paper fill iff execution_authorized)
```

## Action privileges

| Agent | approve | reject | reduce | pause | close | shutdown | execute |
|-------|---------|--------|--------|-------|-------|----------|---------|
| STRAT-* | | | | | | | |
| VAL-IND-001 | | ✓ | | | | | |
| PORT-RISK-001 | ✓ | ✓ | ✓ | ✓ | ✓ | | |
| CAP-STEW-001 | | ✓ | ✓ | ✓ | | | |
| GOV-OPS-001 | | ✓ | | ✓ | | ✓ | |
| TRADE-OPS-001 | | | | ✓ | ✓ | | |
| ARCH-CHIEF-001 | final gate | | | ✓ | | ✓ | |
| EXEC-OMS-001 | | | | | | | ✓ authorized only |
| MON-LIVE-001 | recommend close | | | | recommend | | |

## Size authority

- `TradeProposal.suggested_size_pct_nav` = **non-binding suggestion** (≤ 5%).
- Binding size = `min(suggestion, portfolio, risk, stewardship)`.
- Strategy agents have `can_set_own_capital_limits=false`.

## Live execution lock

- Package flag `LIVE_EXECUTION_ENABLED = False`.
- `Organization(live_execution_enabled=True)` raises.
- `PaperBroker(live_execution_enabled=True)` raises.
- Even if toggled later, `AuthorityResolver` pauses until explicit deploy authorization artifact exists (Phase 5).

## Conflict resolution

`ARCH-CHIEF-001` merges stage verdicts. Any veto agent reject/pause wins. Dissenting reasons are retained on `ApprovalDecision.reasons` and in the audit log.
