# Builder — Product & System Blueprint (repo binding)

Canonical product text: AI Enterprise Architecture Engineer (Builder) **v1.1**.

## What it is

A **governed architecture control plane** for AI organizations. It discovers, models, evaluates, simulates, recommends, and—only after explicit approval—plans migrations. It does **not** silently operate business processes or place trades.

## Watchfloor binding (MVP)

| Decision | Choice |
|----------|--------|
| Primary user | Internal ops / HUMAN-1 + Mission Control |
| First substrate | Custom Python Watchfloor org |
| First adapter | `watchfloor_readonly` |
| Operating mode | `advisory_only` |
| First objective | `governance_and_reliability` |
| Tenancy | Single internal organization |
| Deploy boundary | Export plans only — no production apply |

See `settled_decisions.json` (generated) and `agent_fleet.builder.decisions`.

## Control flow (implemented)

```text
Human Command Layer (cross-cutting)
  → Organization Registry (builder_registry.json view)
  → Discovery (WatchfloorReadOnlyAdapter)
  → Digital twin notes (fidelity declared; static+scenario MVP)
  → Intent reconstruction (unresolved fields explicit)
  → Capability / gap analysis + preserve list
  → AKB consultation (before synthesis)
  → Architecture synthesis (≥2 candidates)
  → Simulation (static + scenarios)
  → Independent adversarial review
  → Implementation plan (export)
  → Human approval required
  → Controlled deployment DEFERRED
  → AKB update only after reviewed outcomes (refused in MVP auto-path)
```

## Commands

```bash
agent-fleet builder decisions
agent-fleet builder discover
agent-fleet builder analyze
agent-fleet builder recommend
agent-fleet builder run --out-dir docs/builder
```

## Relationship to Design Council

| Layer | Role |
|-------|------|
| Institutional Design Council (`enhance`) | Specialty audits → enhancement tasks |
| Builder (`builder run`) | Canonical org model, evidence, gaps, candidates, review, migration plan |
| Watchfloor agents | Carry out paper trading work under SoD |

Builder and Council **design/supervise architecture**. Neither emits `TradeProposal` nor places orders.
