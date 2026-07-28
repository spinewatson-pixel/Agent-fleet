# Watchfloor — source of truth

## Preserved agent-skeleton UI

The **Watchfloor Quant Lab HTML** the user provided is the preserved agent-skeleton UI for the org:

- Single-file front-end titled `watchfloor org — quant lab`
- Dark purple theme and division roster from `baseDivisions()`
- Tabs: Overview, Daily Brief, My Desk, Feed
- Agent detail overlay, chat, create agent/dept modals
- Quant + Fund Floor consolidated into the Trading tab
- Client persistence via `window.storage`

Canonical path for that app: **`ui/watchfloor.html`**.

Until the complete HTML is restored into the repo, `ui/watchfloor.html` may be a thin documentation shell. The roster and authority model extracted from that UI remain authoritative in the registry below.

## Machine-readable extract

**`config/watchfloor_registry.json`** is the machine-readable extract of the Watchfloor org used by the paper-trading backend:

| Concern | Location |
|---|---|
| 279 agent skeletons | `agents[]` |
| 12 divisions / 55 departments | `departments[]`, `counts` |
| Paper / thesis / ceiling / sizing rules | `hard_rules` |
| Propose vs execute separation | `proposer_ids`, `executor_ids` (`EXEC-1` only) |
| Approval + veto | `approval_chain`, `veto_agents` |
| Institutional council seat mapping | `institutional_council_map` |

Python loader: `src/agent_fleet/registry/watchfloor.py`.

## Precedence

1. **Watchfloor agent IDs** (from the preserved UI → registry) are canonical for org seats and operating-chain ownership.
2. The registry JSON is what backend paper paths, authority checks, and tests should read.
3. Provisional `STRAT-*` IDs from earlier audits are **not** primary seats; see `docs/14_watchfloor_reconciliation.md`.

## Related

- [`ui/README.md`](../../ui/README.md) — UI ↔ registry field map
- [`docs/14_watchfloor_reconciliation.md`](../14_watchfloor_reconciliation.md) — audit correction + operating chain
