# Watchfloor — Source of Truth

## Front-end org UI

`ui/watchfloor.html` is the **complete user-provided Watchfloor Quant Lab app** (not a stub).

- Overview, Daily Brief, My Desk, Feed
- Full division tree via `baseDivisions()`
- Agent detail panels, chat, create/retire flows
- Quant + Funds folded into Trading as labeled wings

Checksum: see `ui/WATCHFLOOR_SOURCE.txt`.

## Backend roster

`config/watchfloor_registry.json` is the machine extract used by the paper-trading organization (`WatchfloorOrganization`).

- **300** agents, 128 proposers, executor `EXEC-1` only
- Agent ceiling 300; live execution disabled
- Institutional Design Council seats mapped onto Watchfloor IDs
- Rebuild with `./scripts/rebuild_from_watchfloor.sh` (publishes `ui/data/` for the bridge)

## Rule

Do not invent a parallel agent naming scheme. Watchfloor IDs are canonical. Legacy `STRAT-*` / `PORT-RISK-*` IDs are compatibility-only.
