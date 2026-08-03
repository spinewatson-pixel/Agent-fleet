# Watchfloor UI

[`watchfloor.html`](./watchfloor.html) is the **full** Watchfloor Quant Lab single-file app (user-provided source of truth for the org front-end).

Includes:

- Dark purple theme and sticky mobile layout
- `baseDivisions()` roster (Mission Control → Contractors)
- Overview web, Daily Brief, My Desk, Feed
- Division folders, agent cards, detail overlay + chat
- Create / retire agent & department (persists via `window.storage` when available)
- Quant + Fund Floor consolidated into the Trading tab as marked wings
- BLUEPRINT tile loads rebuilt 25-layer blueprints from [`data/blueprints.json`](./data/blueprints.json) when present

Provenance: see [`WATCHFLOOR_SOURCE.txt`](./WATCHFLOOR_SOURCE.txt).

## Serve locally

```bash
cd ui && python3 -m http.server 8765 --bind 127.0.0.1
```

- http://127.0.0.1:8765/index.html
- http://127.0.0.1:8765/watchfloor.html

## Rebuild from this UI

The HTML roster is canonical. Rebuild backend + UI data copies with:

```bash
./scripts/rebuild_from_watchfloor.sh
```

That syncs `config/watchfloor_registry.json`, regenerates contracts/blueprints/council plan, and publishes:

| File | Purpose |
|---|---|
| `ui/data/watchfloor_registry.json` | Registry for the bridge |
| `ui/data/blueprints.json` | 25-layer blueprints per agent |
| `ui/data/watchfloor_contracts.json` | Operating contracts |
| `ui/data/rebuild_meta.json` | Counts + version stamp |

## Backend mapping

| UI concept | Registry (`config/watchfloor_registry.json`) |
|---|---|
| Hard rules | `hard_rules` |
| Departments | `departments[]` / agent `department` |
| Agents | `agents[]` (**285**) |
| Proposers / executor | `proposer_ids` / `executor_ids` (`EXEC-1` only) |
| Approval / veto | `approval_chain`, `veto_agents` |
| Institutional council | `institutional_council_map` |

Paper trading uses Watchfloor IDs via `WatchfloorOrganization` — open this HTML for the org surface; run `agent-fleet paper-run --agent AAPL-L` for the backend chain.

## Bridge

[`watchfloor_bridge.js`](./watchfloor_bridge.js) bootstraps on page load and feeds the BLUEPRINT panel from rebuilt artifacts. The HTML still embeds `baseDivisions()` so the org renders even if `ui/data/` is missing.

## Related docs

- [`docs/watchfloor/00_source_of_truth.md`](../docs/watchfloor/00_source_of_truth.md)
- [`docs/14_watchfloor_reconciliation.md`](../docs/14_watchfloor_reconciliation.md)
