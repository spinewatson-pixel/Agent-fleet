# Agent Fleet

Institutional-grade multi-agent **paper trading** organization.

Live execution is **disabled** until data reliability, tested strategies, portfolio controls, independent risk approval, emergency shutdown, and explicit authorization are in place.

## Quick start

```bash
pip install -e ".[dev]"
agent-fleet org-map
agent-fleet export-contracts --out config/contracts
agent-fleet demo-paper
pytest -q
```

## Documentation (Institutional Design Council)

| Doc | Contents |
|---|---|
| [00_AUDIT_AND_COUNCIL.md](docs/institutional/00_AUDIT_AND_COUNCIL.md) | Audit, missing info, team audits, critiques, resolution, vetoes |
| [01_ORGANIZATIONAL_MAP.md](docs/institutional/01_ORGANIZATIONAL_MAP.md) | Org tree, chain owners, missing/duplicate agents |
| [02_COMMUNICATION_MAP.md](docs/institutional/02_COMMUNICATION_MAP.md) | Agent message flows |
| [03_AUTHORITY_MAP.md](docs/institutional/03_AUTHORITY_MAP.md) | Approve/reject/reduce/pause/close/halt |
| [04_DATA_FLOW_MAP.md](docs/institutional/04_DATA_FLOW_MAP.md) | Sources and lineage |
| [05_RISK_AND_EMERGENCY.md](docs/institutional/05_RISK_AND_EMERGENCY.md) | Limits and halt |
| [06_MEMORY_AND_LEARNING.md](docs/institutional/06_MEMORY_AND_LEARNING.md) | Controlled learning FSM |
| [07_BACKTEST_AND_PAPER.md](docs/institutional/07_BACKTEST_AND_PAPER.md) | Research & paper framework |
| [08_PHASES_AND_ACCEPTANCE.md](docs/institutional/08_PHASES_AND_ACCEPTANCE.md) | Phased rollout gates |
| [09_OPERATING_CONTRACTS.md](docs/institutional/09_OPERATING_CONTRACTS.md) | Contract summary |

## Operating chain

Data ingestion → validation → research → signal → strategy proposal → independent validation → portfolio evaluation → risk approval → capital stewardship → paper execution → monitoring → attribution → controlled improvement

**Strategy agents propose only.** Risk and stewardship hold veto. Execution is paper-only.
