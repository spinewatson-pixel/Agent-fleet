# 00 — Audit of Current Agent Setup

**Council date:** 2026-07-28 (amended after Watchfloor UI delivery)  
**Subject repository:** `spinewatson-pixel/Agent-fleet`

## Finding (amended)

### Initial git audit
At first commit the git tree contained only `README.md` → `# Agent-fleet`. No Python agents were in the repository.

### Correction — Watchfloor skeleton is the real org
The user subsequently provided the **Watchfloor Quant Lab** single-file org UI: the complete agent-skeleton fleet across Mission Control, Global Intel, Predictions, Trading Floor, The Lab, Quant Research, Fund Floor, Great Minds, Learning Loop, Data Core, Perimeter, and Contractors.

**Canonical machine extract:** `config/watchfloor_registry.json` (**285 agents**, 128 proposers, executor `EXEC-1` only).  
**Human/org UI:** `ui/watchfloor.html` (registry-backed; preserves Watchfloor design language).  
**Reconciliation:** `docs/14_watchfloor_reconciliation.md`.

## What was preserved

| Component | Status | Council action |
|-----------|--------|----------------|
| Watchfloor division/department/agent roster | Provided by user | Extracted to registry; UI restored |
| Paper sandbox / thesis-before-trade / $1–2 sizing | Present in skeleton rules | Encoded in `hard_rules` |
| Human Mode B, RISK/COMP halt, SEC-HALT | Present | Wired into approval + kill switch |
| Quant thesis-exempt wing | Present | Honored in validation |
| Provisional STRAT-* roster from Phase 0 | Temporary | Demoted to legacy compatibility only |

## Institutional council mapped onto Watchfloor seats

See `docs/14_watchfloor_reconciliation.md` and `institutional_council_map` in the registry.

## Unified design decision

Operate a **paper-trading Watchfloor organization** where:

1. Watchfloor agent IDs are canonical  
2. Proposers never approve/execute/self-grade  
3. `EXEC-1` alone places authorized paper orders  
4. Live execution remains hard-disabled  
5. Controlled learning cannot mutate production rules  

Evidence: user-provided Watchfloor skeleton; separation-of-duties mandate; Phase-1 paper objective.
