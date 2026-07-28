# 02 — Complete Organizational Map

```
                         ┌─────────────────────────┐
                         │   ARCH-CHIEF-001         │
                         │   Chief Architecture     │
                         │   conflict resolution,   │
                         │   final approval gate,   │
                         │   live-deploy lock       │
                         └────────────┬────────────┘
           ┌──────────────────────────┼──────────────────────────┐
           ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ SYS-INTEL-001    │      │ AI-INFRA-001     │      │ GOV-OPS-001      │
│ Systems Intel    │      │ AI Infrastructure│      │ Governance/Ops   │
│ (Palantir role)  │      │ (NVIDIA role)    │      │ (JPM role)       │
└────────┬─────────┘      └──────────────────┘      └────────┬─────────┘
         │                                                    │
         │ audit/lineage                                      │ veto/shutdown
         ▼                                                    ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ MKT-INFO-001     │─────▶│ FUND-RES-001     │─────▶│ Strategy Agents  │
│ Market Info      │      │ Research/Strat   │      │ STRAT-*          │
│ (Bloomberg role) │      │ (Goldman role)   │      │ propose only     │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │                         │                         │
         │                         ▼                         │
         │                ┌──────────────────┐               │
         └───────────────▶│ QUANT-RES-001    │◀──────────────┘
                          │ Quant Research   │
                          │ (Renaissance)    │
                          └────────┬─────────┘
                                   │ features / validation standards
                                   ▼
                          ┌──────────────────┐
                          │ VAL-IND-001      │  independent validation
                          └────────┬─────────┘
                                   ▼
                          ┌──────────────────┐
                          │ PORT-RISK-001    │  portfolio + risk (BlackRock)
                          │ veto / reduce    │
                          └────────┬─────────┘
                                   ▼
                          ┌──────────────────┐
                          │ CAP-STEW-001     │  capital stewardship (Berkshire)
                          │ activity veto    │
                          └────────┬─────────┘
                                   ▼
                          ┌──────────────────┐
                          │ GOV-OPS-001      │  governance check
                          └────────┬─────────┘
                                   ▼
                          ┌──────────────────┐
                          │ ARCH-CHIEF-001   │  ApprovalDecision
                          └────────┬─────────┘
                                   ▼
                          ┌──────────────────┐
                          │ TRADE-OPS-001    │  ops/regime (Citadel)
                          │ EXEC-OMS-001     │  paper execution only
                          │ MON-LIVE-001     │  monitoring
                          └────────┬─────────┘
                                   ▼
                          ┌──────────────────┐
                          │ ATTR-001         │  attribution
                          │ LEARN-001        │  controlled improvement
                          └──────────────────┘
```

## Role separation (non-negotiable)

| Layer | Agents | May do | Must not do |
|-------|--------|--------|-------------|
| Design / supervise | `*-001` departmental supervisors | standards, vetoes, routing | retail discretionary trading outside mandate |
| Strategy | `STRAT-*` | emit `TradeProposal` | approve, size binding capital, execute, self-grade |
| Risk / portfolio | `PORT-RISK-001`, `CAP-STEW-001` | approve/reject/reduce/pause/close | generate alpha narratives as cover for weak controls |
| Execution | `EXEC-OMS-001` | place **authorized** paper orders | accept unauthorized or strategy-direct orders |
| Review | `ATTR-001`, `LEARN-001`, `QUANT-RES-001` | measure & propose changes | auto-mutate production rules |

## Strategy roster (provisional — replace if you supply prior skeletons)

| ID | Name | Supervisor |
|----|------|------------|
| STRAT-MOM-001 | Momentum Trend | TRADE-OPS-001 |
| STRAT-MR-001 | Mean Reversion | TRADE-OPS-001 |
| STRAT-EARN-001 | Earnings Event | FUND-RES-001 |
| STRAT-MACRO-001 | Macro Regime | FUND-RES-001 |
| STRAT-FACTOR-001 | Quant Factor | QUANT-RES-001 |
| STRAT-VALUE-001 | Quality Value Steward | CAP-STEW-001 |
| STRAT-VOL-001 | Volatility Awareness | TRADE-OPS-001 |
| STRAT-SECTOR-001 | Sector Rotation | FUND-RES-001 |
