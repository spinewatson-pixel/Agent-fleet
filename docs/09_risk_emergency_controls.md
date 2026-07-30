# 09 — Risk and Emergency-Control Framework

## Hard limits (`config/organization.yaml`)

| Control | Default |
|---------|---------|
| Max gross exposure | 100% NAV |
| Max net exposure | 60% NAV |
| Max single name | 5% NAV |
| Max sector | 25% NAV |
| Max strategy sleeve | 30% NAV |
| Max correlated cluster | 40% NAV |
| Daily loss halt | 2% NAV |
| Drawdown halt | 8% NAV |
| Max orders / day | 50 |
| Max order vs ADV | 2% ADV |

## Kill switches

| Trigger | Action | Authority |
|---------|--------|-----------|
| Daily loss halt | `PORT-RISK-001.halted=true`; reject new proposals | PORT-RISK-001 |
| Drawdown halt | same + escalate GOV | PORT-RISK + GOV |
| Data integrity fail | pause proposals; alert | MKT-INFO + GOV |
| Repeated rejects (≥10/day/strategy) | reduce proposal rate; review | TRADE-OPS + QUANT |
| Governance shutdown | org-wide reject | GOV-OPS-001 |
| Live lock | no live orders | ARCH-CHIEF + package flags |

## Stress / scenario (Phase 1 stub → Phase 3 full)

- Phase 1: simple stress PnL proxy on proposal (`stress_pnl_pct`)  
- Phase 3: historical crash windows, rate shock, liquidity dry-up, correlation→1  

## Emergency close

1. `MON-LIVE-001` raises critical alert with `recommended_action=close`  
2. `TRADE-OPS-001` or `PORT-RISK-001` authorizes close  
3. `EXEC-OMS-001` places paper close (live still locked)  
4. `SYS-INTEL-001` + `GOV-OPS-001` record incident  

## Reconciliation (Phase 2)

`RECON-001` (planned) compares internal positions vs broker paper account each session.
