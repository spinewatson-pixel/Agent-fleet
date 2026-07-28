# Agent Fleet

Institutional-grade **multi-agent paper-trading organization**.

Live brokerage execution is **hard-disabled** until Phase 5+ explicit authorization.

## What this is

Not a pile of generic chatbot agents. This repository implements:

- An Institutional Design Council redesign (9 departmental roles + chief architecture)
- Enforceable **Agent Operating Contracts** for every agent
- A full operating chain:

```
Data ingestion → information validation → research → signal generation
→ strategy proposal → independent validation → portfolio evaluation
→ risk approval → execution → live monitoring → post-trade attribution
→ controlled improvement
```

- Separation of duties: strategies **propose**; risk/portfolio **decide**; execution **places authorized paper orders**; review **measures** and may only **propose** changes

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
agent-fleet paper-run --symbol AAPL --price 190 --strategy STRAT-MOM-001
agent-fleet export-contracts
```

## Documentation (read in order)

1. `docs/00_audit.md` — audit of the prior empty skeleton  
2. `docs/01_missing_information.md` — targeted questions (live-blocking only)  
3. `docs/02_organizational_map.md`  
4. `docs/03_agent_communication_map.md`  
5. `docs/04_authority_approval_map.md`  
6. `docs/05_data_information_flow.md`  
7. `docs/06_agent_operating_contracts.md`  
8. `docs/07_missing_agents.md`  
9. `docs/08_duplicates_consolidation.md`  
10. `docs/09_risk_emergency_controls.md`  
11. `docs/10_memory_learning.md`  
12. `docs/11_backtesting_paper_trading.md`  
13. `docs/12_implementation_phases.md`  
14. `docs/13_acceptance_tests.md`  
15. `docs/council/unified_design.md`

## Layout

```
config/organization.yaml     # limits, departments, strategy roster
src/agent_fleet/
  schemas/                   # messages, contracts, enums
  core/                      # authority, bus, events, memory
  agents/                    # institutional + strategy agents
  paper/                     # paper broker
  workflow/                  # full operating pipeline
docs/                        # council redesign deliverables
tests/                       # unit, integration, acceptance
```

## Non-negotiables

- Strategies cannot self-approve, self-execute, set binding capital, or grade themselves
- Risk, governance, and capital stewardship hold veto power
- Experimental learning never writes production rules
- Paper organization first; autonomous live remains off
