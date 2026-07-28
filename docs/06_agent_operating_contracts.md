# 06 — Agent Operating Contracts

Machine-readable contracts are the source of truth in code:

- Builders: `src/agent_fleet/agents/strategy/__init__.py`
- Institutional: `src/agent_fleet/agents/institutional.py`
- Schema: `src/agent_fleet/schemas/contracts.py`
- Export: `agent-fleet export-contracts`

Every contract includes the full field set mandated by the council:

agent name/id, department, supervisor, strategy & rationale, assets/markets, holding period & frequency, valid regimes, data inputs & sources, indicators/models, setup-detection rules (measurable expressions), entry/exit/stop/invalidation, position-sizing limits, inbound/outbound agent links, approval requirements, execution permissions, monitoring duties, memory, performance metrics, failure/shutdown behavior, deployment status, strategy version, self-improvement gates.

## Strategy contracts (summary)

| Agent | Setup rule (expression) | Hold | Max suggest %NAV | Supervisor |
|-------|-------------------------|------|------------------|------------|
| STRAT-MOM-001 | `close > sma_50 AND sma_50 > sma_50[20] AND returns_12_1 > 0 AND adv_20d > 5e6` | 5–60d | 3% | TRADE-OPS-001 |
| STRAT-MR-001 | `rsi_14 < 30 AND bollinger_z < -2 AND regime == RANGE_BOUND AND adv_20d > 5e6` | 1–10d | 2% | TRADE-OPS-001 |
| STRAT-EARN-001 | `eps_surprise_pct > 5 AND guidance_delta >= 0 AND adv_20d > 1e7` | 1–30d | 2.5% | FUND-RES-001 |
| STRAT-MACRO-001 | `regime_changed == True AND confirm_count >= 2` | 10–120d | 5% | FUND-RES-001 |
| STRAT-FACTOR-001 | `combined_alpha_v1 in extreme deciles AND adv_20d > 5e6` | 5–40d | 1.5% | QUANT-RES-001 |
| STRAT-VALUE-001 | `moat_score >= 4 AND margin_of_safety >= 0.25 AND roic > cost_of_capital` | 90–1825d | 5% | CAP-STEW-001 |
| STRAT-VOL-001 | `realized_vol_20 > p90 OR corr_average > 0.7` | 1–20d | 4% | TRADE-OPS-001 |
| STRAT-MR note | Invalid in trending / high-vol / risk-off | — | — | — |
| STRAT-SECTOR-001 | `rs_rank_63d >= 0.75 AND cycle_aligned == True` | 10–90d | 4% | FUND-RES-001 |

## Universal strategy permission block

```
can_self_approve: false
can_self_execute: false
can_set_own_capital_limits: false
can_evaluate_own_performance: false
may_place_orders: false
live_enabled: false
self_improvement.may_auto_apply_to_production: false
required_sequence: documented → statistical_test → out_of_sample → paper_trade
                   → risk_review → versioned → approved → gradual_deploy
```

## Institutional control contracts

| ID | Owns stages | Authority |
|----|-------------|-----------|
| MKT-INFO-001 | data_ingestion, information_validation | reject unverified sources |
| FUND-RES-001 | research, signal_generation | publish ResearchSignal |
| QUANT-RES-001 | research, controlled_improvement | reject overfit models |
| VAL-IND-001 | independent_validation | reject |
| PORT-RISK-001 | portfolio_evaluation, risk_approval | approve/reject/reduce/pause/close (veto) |
| CAP-STEW-001 | risk_approval | reject/reduce/pause (veto) |
| GOV-OPS-001 | risk_approval | reject/pause/shutdown (veto) |
| TRADE-OPS-001 | execution, live_monitoring | pause/close |
| EXEC-OMS-001 | execution | authorized paper orders |
| MON-LIVE-001 | live_monitoring | recommend close |
| ATTR-001 | post_trade_attribution | measure |
| LEARN-001 | controlled_improvement | propose only |
| SYS-INTEL-001 | (cross-cutting audit) | lineage |
| AI-INFRA-001 | (infra) | failover |
| ARCH-CHIEF-001 | risk_approval, execution gate | pause/shutdown/final decision |

Per-agent JSON dumps are generated into `docs/agent_contracts/contracts.json` via CLI.
