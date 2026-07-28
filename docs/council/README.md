# Institutional Design Council

Executable enhance fleet for the Watchfloor Quant Lab.

## How to run

```bash
agent-fleet enhance
# → docs/council/enhancement_plan.json
# → docs/council/enhancement_plan.md
```

## What it does

1. Nine specialty teams independently audit the Watchfloor registry + paper-org wiring.
2. Teams cross-critique (risk vs trading ops, stewardship vs lab breadth, quant signal schema).
3. Risk / governance / stewardship apply standing vetoes (especially live execution).
4. Chief architecture unifies into P0→P3 implementation tasks.

## Role boundary

- **Council (IDC-\*)** — design, audit, enhance
- **Watchfloor proposers** — TradeProposal only
- **RISK-1 / COMP-1 / GOV-CHAIR / SEC-HALT / HUMAN-1 / BRK-SAFE** — decide / veto / halt
- **EXEC-1** — authorized paper orders only
