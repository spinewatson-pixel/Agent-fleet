# Agent Operating Contracts

Complete machine-readable contracts live in:
- Code registry: `src/agent_fleet/contracts/registry.py`
- Exported JSON: `config/contracts/*.json` (via `agent-fleet export-contracts`)

## Contract schema (enforced fields)
Every agent includes: name/id, department, supervisory agent, strategy/rationale, assets/markets, holding period, frequency, valid regimes, data inputs/sources, indicators/models, setup rules, entry/exit/stop/invalidation, position sizing caps, inputs from other agents, outputs to other agents, approval requirements, execution permissions, authorities, post-entry monitoring, memory, performance metrics, failure/shutdown, deployment status, version, self-improvement gates.

## Strategy agents — measurable highlights

### STRAT-MOM-001
- Setup: SMA50/SMA200 cross + volume > 1.2× volSMA20  
- Entry: close confirms + Donchian break  
- Stop: 2.5 ATR  
- Invalidation: high_vol/mean_reverting 3 sessions  
- Caps: 4% position, 0.4% risk/trade  

### STRAT-MR-001
- Setup: RSI14<30, z<-2, close>SMA200  
- Entry: reclaim lower Bollinger  
- Exit: SMA20 or RSI>55  
- Stop: 1.5 ATR beyond setup low  
- Invalidation: trending_down for longs  

### STRAT-EVT-001
- Setup: |surprise|≥5% and research conviction≥0.6  
- Entry: gap direction holds first 30m  
- Exit: 5 sessions or 2R  
- Stop: 1R  

### STRAT-MACRO-001
- Setup: regime change confirmed by ≥2 series  
- Stop: macro book DD≥4%  
- Invalidation: macro staleness>7d  

### STRAT-QUAL-001
- Setup: ROE≥15%, ND/EBITDA≤2, OE yield≥5%  
- Entry: research conviction≥0.7  
- Soft review -25%; thesis-break exit  
- Steward requires quality/moat language in thesis  

### STRAT-SECROT-001
- Setup: RS top quartile + breadth  
- Weekly rebalance proposals  
- Sector book stop 3%  

### STRAT-PAIRS-001
- Setup: ADF p<0.05, half-life 2–20, |z|≥2  
- Exit |z|≤0.5; stop |z|≥4 or coint break  
- Net exposure cap 5%  

## Control-plane contracts
See exported JSON for DATA-*, RSH-*, SIG-VAL, PORT, RISK, CAP-STEW, EXEC-*, MON-*, REV-ATTR, LEARN-CTRL, GOV-COMP, SYS-ORCH, AI-INFRA.

## Status
All contracts start at `design` / `paper` environment. `EXEC-LIVE-001` is `shutdown` with empty execution permissions.
