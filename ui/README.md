# Watchfloor UI

The full single-file **Watchfloor Quant Lab** app should live at [`watchfloor.html`](./watchfloor.html).

That app is the org front-end: dark purple theme, `baseDivisions()` roster, Overview / Daily Brief / My Desk / Feed tabs, agent detail overlay + chat, create agent/dept modals, quant+funds consolidated into the Trading tab, and `window.storage` persistence.

The file currently checked in is a **thin shell** that documents this entry point and loads [`watchfloor_bridge.js`](./watchfloor_bridge.js) against the registry. Restore the complete user-provided HTML here when available so fidelity is preserved.

## Registry mapping

Machine-readable extract of the UI roster:

| UI concept | Registry field (`config/watchfloor_registry.json`) |
|---|---|
| Org title / version | `organization`, `version` |
| Source attribution | `source` → `ui/watchfloor.html baseDivisions()` |
| Hard rules (paper, ceiling, thesis, sizing) | `hard_rules` |
| Division / department tree | `departments[]` (`division`, `name`, `institutional_role`) |
| Agent skeletons (id, nick, role, tags, status, kind, authority flags) | `agents[]` |
| Counts | `counts.total_agents` (279), `proposers`, `executors`, `divisions` (12) |
| Who may propose / execute | `proposer_ids`, `executor_ids` (`EXEC-1` only) |
| Approval / veto | `approval_chain`, `veto_agents` |
| Institutional council seats | `institutional_council_map` |

### Divisions (`baseDivisions()` IDs)

| ID | Division | Notes |
|---|---|---|
| `ctrl` | Mission Control | Council seats, risk & limits |
| `intel` | Global Intel | World watch, company / bull-bear / sector desks |
| `pred` | Predictions | Forecast, causal chains, anomalies, micro-signals |
| `trade` | Trading Floor | Groups A–G; UI Trading tab also surfaces quant+funds |
| `lab` | Lab | Idea engine, test bench, red team |
| `quant` | Quant Research | Thesis-exempt wing; consolidated into Trading tab in UI |
| `funds` | Fund Floor | Style desks; consolidated into Trading tab in UI |
| `minds` | Great Minds | Polymath / first-principles benches |
| `learn` | Learning Loop | Scoreboard, lessons, foundry (no prod mutation) |
| `data` | Data Core | Feeds, DQ, memory, toolshop |
| `sec` | Perimeter | Keys, watch, blast radius, kill switch |
| `contr` | Contractors | Marketplace roster |

### Authority flags on each agent

- `may_propose_trades` — strategy / desk may enqueue paper proposals only
- `may_place_orders` — only `EXEC-1`
- `can_self_approve` — always false under hard rules
- `paper_only` — always true; live execution disabled

## Bridge

[`watchfloor_bridge.js`](./watchfloor_bridge.js) fetches `../config/watchfloor_registry.json` and exposes agent counts plus authority helpers for future UI wiring (`WatchfloorBridge` on `window`).

## Related docs

- [`docs/watchfloor/00_source_of_truth.md`](../docs/watchfloor/00_source_of_truth.md)
- [`docs/14_watchfloor_reconciliation.md`](../docs/14_watchfloor_reconciliation.md)
