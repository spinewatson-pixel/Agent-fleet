# Watchfloor UI

[`watchfloor.html`](./watchfloor.html) is the **full** Watchfloor Quant Lab single-file app (user-provided source of truth for the org front-end).

Includes:

- Dark purple theme and sticky mobile layout
- `baseDivisions()` roster (Mission Control → Contractors)
- Overview web, Daily Brief, My Desk, Feed
- Division folders, agent cards, detail overlay + chat
- Create / retire agent & department (persists via `window.storage` when available)
- Quant + Fund Floor consolidated into the Trading tab as marked wings

Provenance: see [`WATCHFLOOR_SOURCE.txt`](./WATCHFLOOR_SOURCE.txt) (sha256 `60b3121e69cb9c8a0067830c6fc5829e44c42f2d5b1f25f86ede0f700c6178ee`, 156224 bytes).

## Backend mapping

Machine-readable extract of the same roster:

| UI concept | Registry (`config/watchfloor_registry.json`) |
|---|---|
| Hard rules | `hard_rules` |
| Departments | `departments[]` |
| Agents | `agents[]` (279) |
| Proposers / executor | `proposer_ids` / `executor_ids` (`EXEC-1` only) |
| Approval / veto | `approval_chain`, `veto_agents` |
| Institutional council | `institutional_council_map` |

Paper trading uses Watchfloor IDs via `WatchfloorOrganization` — open this HTML for the org surface; run `agent-fleet paper-run --agent AAPL-L` for the backend chain.

## Bridge

[`watchfloor_bridge.js`](./watchfloor_bridge.js) can load the JSON registry for future live wiring. The full HTML currently embeds its own `baseDivisions()` data and does not require the bridge to render.

## Related docs

- [`docs/watchfloor/00_source_of_truth.md`](../docs/watchfloor/00_source_of_truth.md)
- [`docs/14_watchfloor_reconciliation.md`](../docs/14_watchfloor_reconciliation.md)
