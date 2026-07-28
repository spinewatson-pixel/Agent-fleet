# Agent Fleet / Watchfloor Quant Lab

Institutional-grade **multi-agent paper-trading organization** built on the Watchfloor agent fleet.

Live brokerage execution is **hard-disabled**.

## Canonical sources

| Artifact | Role |
|----------|------|
| `config/watchfloor_registry.json` | Machine-readable roster (279 agents) |
| `ui/watchfloor.html` | Org UI (registry-backed) |
| `docs/14_watchfloor_reconciliation.md` | Council mapping onto Watchfloor seats |
| `docs/00_audit.md` … `docs/13_*.md` | Institutional redesign deliverables |

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
agent-fleet registry
agent-fleet authority-map
agent-fleet paper-run --symbol AAPL --price 190 --agent AAPL-L
```

Open the org UI:

```bash
open ui/watchfloor.html   # or serve the file in a browser
```

## Operating chain (Watchfloor IDs)

```
MKT-1 / ALT-1 / DQ-1
  → intel + pred research
  → Watchfloor proposer (AAPL-L, SCOUT-*, RT-*, BRK-TRD*, …)
  → FIT-1 validation
  → RISK-1 / CAP-1 portfolio-risk
  → BRK-SAFE stewardship veto
  → COMP-1 / GOV-CHAIR / HUMAN-1 (Mode B)
  → EXEC-1 paper fill
  → COMP-1 monitor · ATTR-1 attribution · SYNTH-1 controlled improvement
```

## Non-negotiables

- Strategies **propose only**
- Only **EXEC-1** places authorized paper orders
- Risk / governance / stewardship / security hold veto / halt power
- Experimental learning never writes production rules
- Autonomous live remains off until Phase 5+ explicit authorization
