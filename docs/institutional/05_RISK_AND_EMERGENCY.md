# Risk and Emergency-Control Framework

## Firm limits (paper defaults)
| Limit | Default |
|---|---|
| Max position | 5% NAV |
| Max risk / trade | 0.5% NAV |
| Max gross exposure | 100% NAV |
| Max net exposure | 60% NAV |
| Max sector | 25% NAV |
| Max strategy book | 30% NAV |
| Max correlated group | 35% NAV |
| Max daily loss | 2% NAV |
| Max drawdown | 10% NAV |
| Min cash | 5% NAV |

Configured in `RiskLimits` (`src/agent_fleet/risk/engine.py`) and per-strategy caps in contracts (never self-approved).

## Controls by layer
1. **Contract:** strategy universe, regime, setup rules.  
2. **SIG-VAL-001:** structural + data readiness rejects.  
3. **PORT-ALLOC-001:** concentration / budget.  
4. **RISK-APPR-001:** firm limits + veto + halt.  
5. **CAP-STEW-001:** thesis quality / anti-churn veto.  
6. **MON-LIVE-001:** stop/invalidation monitoring.  
7. **GOV-COMP-001:** permission & incident escalation.

## Emergency halt
- Triggers: drawdown breach, repeated permission violations, data integrity failure, human/governance command.
- Effect: `MessageBus.emergency_halt()`; `PortfolioState.halted=True`; no new risk-taking orders.
- Recovery: incident report + RISK + GOV approvals + contract version bump.

## Scenario / stress (Phase 1+)
Paper phase records hooks for: rate shock, gap -5%, liquidity dry-up, correlation → 1. Enforcement numeric stress gates required before live shadow.
