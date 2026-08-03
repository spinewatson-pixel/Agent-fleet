# Agent Fleet / Watchfloor Quant Lab

Institutional-grade **multi-agent paper-trading organization** built on the Watchfloor agent fleet.

Live brokerage execution is **hard-disabled**.

## Canonical sources

| Artifact | Role |
|----------|------|
| `config/watchfloor_registry.json` | Machine-readable roster (300 agents) |
| `ui/watchfloor.html` | Org UI (loads rebuilt blueprints from `ui/data/`) |
| `ui/builder.html` | Builder Decision Workspace (advisory control plane) |
| `AKB/` | Architecture Knowledge Base (L1 research + L2 assets) |
| `docs/builder/` | Builder product binding + generated recommendations |
| `docs/14_watchfloor_reconciliation.md` | Council mapping onto Watchfloor seats |
| `docs/00_audit.md` … `docs/13_*.md` | Institutional redesign deliverables |

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
agent-fleet registry
agent-fleet authority-map
agent-fleet enhance                 # Design Council → docs/council/enhancement_plan.*
agent-fleet builder run             # Architecture control plane → docs/builder/
agent-fleet export-contracts --watchfloor
agent-fleet paper-run --symbol AAPL --price 190 --agent AAPL-L
```

## Builder — Architecture Control Plane

The **Builder** is a governed architecture control plane for AI organizations (blueprint v1.1). It inventories Watchfloor, reconstructs intent with explicit gaps, consults the AKB, synthesizes ≥2 candidates, runs static/scenario checks, adversarially reviews, and exports a human-approved migration plan.

- **Mode:** advisory only — no trades, no production mutation, no AKB writes from unverified sims
- **First org:** Watchfloor Quant Lab (`watchfloor_readonly` adapter)
- **AKB:** `AKB/` Phases 1–30 scaffolds + seed patterns in `agent_fleet.builder.akb`

```bash
agent-fleet builder decisions
agent-fleet builder run --out-dir docs/builder
# UI: http://127.0.0.1:8765/builder.html
```

See [`docs/builder/00_product_definition.md`](docs/builder/00_product_definition.md) and [`AKB/AKB_Master_Index.md`](AKB/AKB_Master_Index.md).

## Institutional Design Council (enhance fleet)

Nine specialty teams + chief architecture audit Watchfloor and emit a prioritized plan:

| Team | Inspired by | Role |
|------|-------------|------|
| Systems Intelligence | Palantir | lineage, permissions, audit |
| Market Information | Bloomberg | feeds, verification, delivery |
| AI Infrastructure | NVIDIA | model routing, compute |
| Portfolio and Risk | BlackRock | limits, stress (**veto**) |
| Trading Operations | Citadel | OMS, slippage, coordination |
| Quantitative Research | Renaissance | hypotheses, anti-overfit |
| Research and Strategy | Goldman | research → signals |
| Governance and Operations | JPMorgan | controls, escalation (**veto**) |
| Capital Stewardship | Berkshire | quality, activity (**veto**) |

Council agents **design and supervise only** — they do not propose or execute trades. Run `agent-fleet enhance` to refresh `docs/council/enhancement_plan.md`.

## Agent blueprints (25 layers)

Every Watchfloor agent has a complete operating blueprint:

**Structural:** Identity · Goal · Responsibilities · Functions · Tools · Capabilities · Memory · Knowledge Base  

**Operating:** Skills · Workflows · Decision Rules · Communication · Inputs · Outputs · Learning · Evaluation · Permissions  

**Control:** Constraints · Triggers · Scheduling · Logging · Self-Reflection · Escalation · Versioning · Health Monitoring

```bash
./scripts/rebuild_from_watchfloor.sh   # sync UI → registry + contracts + blueprints → ui/data/
agent-fleet blueprints                 # → docs/agent_blueprints/blueprints.json
```

Open any agent in `ui/watchfloor.html` → **BLUEPRINT** tile (prefers rebuilt `ui/data/blueprints.json`).

```bash
cd ui && python3 -m http.server 8765 --bind 127.0.0.1
# http://127.0.0.1:8765/watchfloor.html
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
