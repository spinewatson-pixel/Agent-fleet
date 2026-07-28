# Organizational Map

## Principle
Company-inspired council teams designed the system. Runtime agents are **departments/supervisors**, **strategy proposers**, **risk/portfolio deciders**, **execution**, and **review** — not branded roleplay bots.

## Department tree

```
GOV-COMP-001 (Governance)
├── SYS-ORCH-001 (Systems Intelligence / Orchestration)
│   ├── DATA-MKT-001
│   ├── DATA-NEWS-001
│   ├── DATA-VAL-001
│   ├── RSH-FUND-001
│   ├── RSH-QUANT-001
│   ├── AI-INFRA-001
│   ├── SIG-VAL-001
│   ├── EXEC-PAPER-001
│   ├── MON-REGIME-001
│   ├── REV-ATTR-001
│   └── Strategy desk (propose only)
│       ├── STRAT-MOM-001
│       ├── STRAT-MR-001
│       ├── STRAT-EVT-001
│       ├── STRAT-MACRO-001
│       ├── STRAT-QUAL-001
│       ├── STRAT-SECROT-001
│       └── STRAT-PAIRS-001
├── RISK-APPR-001 (Portfolio & Risk)
│   ├── PORT-ALLOC-001
│   └── MON-LIVE-001
├── CAP-STEW-001 (Capital Stewardship)
└── LEARN-CTRL-001 (Controlled Learning)
EXEC-LIVE-001 — SHUTDOWN (no supervisor activation until authorization)
```

## Operating chain ownership

| Stage | Owner agent(s) | May approve/reject? |
|---|---|---|
| Data ingestion | DATA-MKT-001, DATA-NEWS-001 | n/a (emit only) |
| Information validation | DATA-VAL-001 | reject bad data |
| Research | RSH-FUND-001, RSH-QUANT-001 | propose signals/notes |
| Signal generation | Research + Strategy feature use | propose |
| Strategy proposal | STRAT-* | **propose only** |
| Independent validation | SIG-VAL-001 | pass/fail |
| Portfolio evaluation | PORT-ALLOC-001 | approve/reduce/reject |
| Risk approval | RISK-APPR-001 | approve/reduce/reject/pause/close/**halt** |
| Capital stewardship | CAP-STEW-001 | approve/reduce/reject/pause |
| Execution | EXEC-PAPER-001 | execute authorized paper only |
| Live monitoring | MON-LIVE-001, MON-REGIME-001 | pause/close requests |
| Post-trade attribution | REV-ATTR-001 | report only |
| Controlled improvement | LEARN-CTRL-001 | propose/reject changes; not trade |

## Missing agents added (vs empty repo)
All control-plane and provisional strategy agents above.

## Duplicates / combinations
| Candidate overlap | Decision |
|---|---|
| Combined research+strategy megagent | **Split** — research emits signals; strategy proposes trades |
| Combined risk+portfolio | **Split** — portfolio optimizes fit; risk is independent veto |
| Combined paper+live execution | **Split** — live remains shutdown |
| News vs market data | **Split** — different SLAs and verification |
| Attribution inside strategy | **Forbidden** — REV-ATTR-001 is independent |
