# Authority and Approval Map

## Hard rule
**Strategy agents propose. They do not approve, execute, set firm capital limits, or self-certify performance for live authority.**

## Trade lifecycle authorities

| Action | Authorized agents | Notes |
|---|---|---|
| Propose trade | `STRAT-*` | Must cite setup rules fired |
| Validate proposal | `SIG-VAL-001` | Independent; may reject |
| Portfolio approve/reduce/reject | `PORT-ALLOC-001` | Book fit only |
| Risk approve/reduce/reject/pause/close | `RISK-APPR-001` | **Veto** |
| Stewardship approve/reduce/reject/pause | `CAP-STEW-001` | Quality / anti-churn **veto** |
| Execute paper | `EXEC-PAPER-001` | Requires Risk + Steward + Portfolio path |
| Execute live | _(none)_ | `EXEC-LIVE-001` shutdown |
| Emergency halt | `RISK-APPR-001`, `GOV-COMP-001` | Halts bus for new risk-taking |
| Version / deploy approve | `RISK-APPR-001`, `GOV-COMP-001`, `SYS-ORCH-001` | Learning chain |

## Dual-control requirements
- Paper order: Risk decision `APPROVE|REDUCE` **and** Steward `APPROVE` (unless steward waived by policy for micro test — **not enabled**).
- Production rule change: Risk + Governance approvals after full learning stages.
- Live enablement: Human operator + Governance + Risk (future); code flag `LIVE_EXECUTION_ENABLED=False`.

## Code source
`src/agent_fleet/governance/authority.py`
