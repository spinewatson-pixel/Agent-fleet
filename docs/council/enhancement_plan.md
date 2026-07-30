# Institutional Design Council — Enhancement Plan

Generated: `2026-07-30T06:38:01.145480+00:00`
Organization: **watchfloor quant lab** (registry v0.5.0)
Agents: `{'total_agents': 285, 'proposers': 128, 'executors': 1, 'divisions': 12}`

## Reasoning
Council ran independent audits against the Watchfloor registry and paper-org wiring, cross-critiqued trading vs risk vs stewardship tensions, applied standing live-execution vetoes, and ordered implementation by P0→P3.

## Decisions
- **Unified enhance sequence adopted** — P0: separation + ceiling governance + measurable contracts. P1: durable lineage, fixed-dollar sizing, regime gate, ResearchSignal wiring. P2: data adapters, backtest factory, ML compute budget. P3: limited live only with explicit HUMAN-1 authorization.
  - Task: Execute tasks_by_priority in order; do not skip P0.
- **Watchfloor IDs remain canonical; council is designer/supervisor layer** — Institutional teams design and enhance; Watchfloor strategy agents propose; RISK-1/COMP-1/GOV-CHAIR/SEC-HALT/HUMAN-1 decide; EXEC-1 executes paper.
  - Task: Keep IDC-* agents out of TradeProposal emission.
- **Critique resolution: single ResearchSignal schema remains mandatory** — Intel and quant may both publish, but payload must be ResearchSignal.
  - Task: Reject non-ResearchSignal handoffs in message bus permissions.

## Vetoes
- None beyond standing live-execution lock.

## Dissenting views retained
- Dissent: retiring mean-reversion scouts entirely is too aggressive for a lab — Keep SCOUT/MR-style cohorts in paper with stewardship veto and fixed $1–2 sizing; do not delete the experiment.
- Critique: do not confuse lab breadth with production capital allocation — Paper cohorts may be wide; binding capital stays tiny and comparable.

## Implementation tasks by priority
### P0
1. **Unified enhance sequence adopted** (Chief Architecture)
   - Execute tasks_by_priority in order; do not skip P0.
   - Seats: GOV-CHAIR, ARCH-1, HUMAN-1
2. **Watchfloor IDs remain canonical; council is designer/supervisor layer** (Chief Architecture)
   - Keep IDC-* agents out of TradeProposal emission.
   - Seats: EXEC-1, RISK-1, GOV-CHAIR
### P1
1. **Permissions exist in registry flags but are not enforced in the UI** (Systems Intelligence)
   - Gate UI agent creation behind council proposal objects validated against agent_ceiling and COMP-1 mandate checks.
   - Seats: GOV-CHAIR, HUMAN-1, UI-1
2. **Separate local paper inference from optional cloud workloads** (AI Infrastructure)
   - Document and enforce Environment.EXPERIMENTAL for ML self-builds.
   - Seats: ML-ARCH, RT-FORGE-1
3. **ResearchSignal not produced by intel/pred desks in Watchfloor runtime** (Research and Strategy)
   - Route intel/pred outputs through ResearchSignal schema; strategies may only consume ResearchSignal IDs, never raw narrative blobs.
   - Seats: CORP-1, BULL-1, BEAR-1, FORE-1, HEAD-INTEL
4. **Agent ceiling decision in force; enforce in UI create flow** (Governance and Operations)
   - Wire UI agent creation to agent_ceiling + GOV-CHAIR proposal queue.
   - Seats: GOV-CHAIR, HUMAN-1, LIFE-1, UI-1
5. **Activity incentives still favor many small discretionary experiments** (Capital Stewardship)
   - Add activity budget: max new discretionary proposals/day/cohort; BRK-INV reviews duplicates of the same thesis family.
   - Seats: BRK-SAFE, BRK-INV, CAP-1, HEAD-TRADE
6. **Critique resolution: single ResearchSignal schema remains mandatory** (Quantitative Research)
   - Reject non-ResearchSignal handoffs in message bus permissions.
   - Seats: FORE-1, MINE-1, CORP-1
7. **Critique: do not confuse lab breadth with production capital allocation** (Capital Stewardship)
   - Separate paper experiment capital from stewardship sleeve capital in portfolio state.
   - Seats: CAP-1, BRK-SAFE
### P2
1. **Durable EventStore path exists; UI still lacks MEM-1 audit export** (Systems Intelligence)
   - Add MEM-1 audit export endpoint/bridge so the UI can read data/audit/events.jsonl lineage for each proposal_id.
   - Seats: MEM-1, DQ-1, UI-1, TOOL-1
2. **No real market/news/filings adapters behind MKT-1/ALT-1** (Market Information)
   - Implement MarketEvent adapters (bars, calendar, filings, news) with source_verified + tagging, delivering slices to intel/pred consumers.
   - Seats: MKT-1, ALT-1, DQ-1, GEO-1, MACRO-1
3. **Dual-source confirmation for macro prints not encoded** (Market Information)
   - Add dual_source_required flag for macro event types in DQ-1.
   - Seats: MACRO-1, FORE-1, DQ-1
4. **ML-ARCH autonomy budget not instrumented** (AI Infrastructure)
   - Add hard_rules.compute_ceiling and a model-routing health endpoint; ML-ARCH proposals above ceiling require GOV-CHAIR.
   - Seats: ML-ARCH, ML-VIT, ML-SEQ, TOOL-1
5. **Fixed-dollar cohort sizing wired; fund/quant sleeves still %NAV** (Portfolio and Risk)
   - Expose paper_experiment_capital_usd vs stewardship_sleeve_capital_usd in portfolio state exports for BRK-SAFE.
   - Seats: CAP-1, RISK-1, EXEC-1
6. **Same-symbol cluster check exists; full correlation matrix still missing** (Portfolio and Risk)
   - Add rolling cross-name correlation matrix feeding CORR-Q.
   - Seats: RISK-1, CORR-Q, CAP-1
7. **REG-1 regime service admits proposals; richer regime engine still needed** (Trading Operations)
   - Replace static regime labels with tape/vol feature classifier.
   - Seats: HEAD-TRADE, REG-1, EXEC-1
8. **Per-symbol daily order cap live; slippage ledger still thin** (Trading Operations)
   - Persist EXEC-1 slippage scorecards per fill for ATTR-1.
   - Seats: EXEC-1, CAP-1, HEAD-TRADE
9. **EXEC-1 is both quality analyst and sole order placer** (Trading Operations)
   - Clarify EXEC-1 contract: place authorized paper orders; ATTR-1 owns slippage scorecards.
   - Seats: EXEC-1, ATTR-1
10. **Proposer contract stubs complete; promote from stub to validated** (Quantitative Research)
   - Run BACK-1/STAT-1 validation packs per contract; mark contract_completeness=validated_v1 when OOS gates pass.
   - Seats: FIT-1, STAT-1, HYPO-1, BACK-1
11. **No walk-forward / OOS harness wired to HYPO-1 and BACK-1** (Quantitative Research)
   - Build hypothesis registry + point-in-time backtest queue with FIT-1/COST-1 veto.
   - Seats: HYPO-1, BACK-1, STAT-1, FIT-1, COST-1
12. **Quant evidence_package_id gate is live; packages still synthetic in paper** (Quantitative Research)
   - Replace paper stub packages with FIT-1/COST-1 signed evidence objects.
   - Seats: FIT-1, COST-1, ENS-1
13. **Bull/Bear split authors need conflict metadata on case files** (Research and Strategy)
   - Enforce separate author_id on case file versions in org memory.
   - Seats: BULL-1, BEAR-1, MEM-1
14. **RECON-1 seat added; automate book vs broker mismatch halt** (Governance and Operations)
   - Implement RECON-1 daily check; mismatch → COMP-1 halt.
   - Seats: RECON-1, COMP-1, EXEC-1, SEC-LEDGER
15. **Incident runbooks for SEC-HALT drills not versioned in repo** (Governance and Operations)
   - Add docs/runbooks/halt_drill.md and automate SEC-DRILL quarterly checklist.
   - Seats: SEC-HALT, SEC-DRILL, SEC-RESTORE, SEC-LEDGER
16. **Berkshire desk moat/MOS gate is live; scorecards still manual** (Capital Stewardship)
   - Have BRK-MOAT/BRK-SAFE publish signed score objects instead of free-form metadata.
   - Seats: BRK-MOAT, BRK-SAFE, BRK-TRD1, BRK-TRD2
17. **Dissent: retiring mean-reversion scouts entirely is too aggressive for a lab** (Capital Stewardship)
   - Retain MR/scout cohorts; tag as experimental with elevated reject sensitivity.
   - Seats: SCOUT-L2, SCOUT-S2, BRK-SAFE
### P3
- (none)

## Full findings
- `P2` `recommended_improvement` **Systems Intelligence**: Durable EventStore path exists; UI still lacks MEM-1 audit export
  - Paper org now writes lineage to data/audit/events.jsonl by default. Remaining gap: Watchfloor UI does not surface or export that graph.
- `P1` `structural_weakness` **Systems Intelligence**: Permissions exist in registry flags but are not enforced in the UI
  - UI create-agent flow can invent custom agents without going through GOV-CHAIR proposal queue or ceiling checks in code.
- `P2` `missing_capability` **Market Information**: No real market/news/filings adapters behind MKT-1/ALT-1
  - Paper path uses synthetic verified bars. Intel desks (GEO/MACRO/…) have mandates but no normalized MarketEvent feed contract wired in.
- `P2` `recommended_improvement` **Market Information**: Dual-source confirmation for macro prints not encoded
  - MACRO-1 / POLICY-1 should require two-source confirm before FORE-1 publishes high-confidence calls.
- `P2` `missing_capability` **AI Infrastructure**: ML-ARCH autonomy budget not instrumented
  - Pattern Recognition ML claims self-building below compute ceiling, but there is no compute meter, model registry, or failover SLA.
- `P1` `recommended_improvement` **AI Infrastructure**: Separate local paper inference from optional cloud workloads
  - Phase-1 paper org should stay local/deterministic; cloud only for experimental ML cells.
- `P2` `recommended_improvement` **Portfolio and Risk**: Fixed-dollar cohort sizing wired; fund/quant sleeves still %NAV
  - PaperBroker + RISK-1 honor suggested_size_usd for fixed_1_2_usd cohorts. Continue separating paper experiment capital from stewardship sleeve capital.
- `P2` `recommended_improvement` **Portfolio and Risk**: Same-symbol cluster check exists; full correlation matrix still missing
  - RISK-1 rejects when same-symbol cluster exceeds max_correlated_cluster_pct. Cross-name rolling correlation matrix remains a P2 gap.
- `P2` `recommended_improvement` **Trading Operations**: REG-1 regime service admits proposals; richer regime engine still needed
  - RegimeService gates FIT-1 admission against contract valid/invalid regimes. Next: data-driven regime labels owned by HEAD-TRADE / REG-1.
- `P2` `recommended_improvement` **Trading Operations**: Per-symbol daily order cap live; slippage ledger still thin
  - 103 trading-division agents share a per-symbol daily cap of 20.
- `P2` `structural_weakness` **Trading Operations**: EXEC-1 is both quality analyst and sole order placer
  - Watchfloor nick 'Fill Check' mixes measurement with authority. Keep execution authority, but split attribution of fill quality to ATTR-1.
- `P2` `recommended_improvement` **Quantitative Research**: Proposer contract stubs complete; promote from stub to validated
  - All proposers have measurable setup/entry/exit stubs and FIT-1 blocks incomplete contracts. Next: empirically validate expressions.
- `P2` `missing_capability` **Quantitative Research**: No walk-forward / OOS harness wired to HYPO-1 and BACK-1
  - Lab seats exist; controlled improvement sequence is documented but not automated.
- `P2` `recommended_improvement` **Quantitative Research**: Quant evidence_package_id gate is live; packages still synthetic in paper
  - FIT-1 requires evidence_package_id on RT/quant proposals before RISK-1.
- `P1` `missing_capability` **Research and Strategy**: ResearchSignal not produced by intel/pred desks in Watchfloor runtime
  - CORP-1/BULL-1/BEAR-1/FORE-1 exist, but paper path synthesizes a single CORP-1 signal. Standardized research→signal handoff is incomplete.
- `P2` `recommended_improvement` **Research and Strategy**: Bull/Bear split authors need conflict metadata on case files
  - BULL-1 and BEAR-1 must never share authorship on the same case version.
- `P1` `recommended_improvement` **Governance and Operations**: Agent ceiling decision in force; enforce in UI create flow
  - Roster 285 ≤ ceiling 300 (GOV-CEIL-2026-07-28). UI still needs hard gate.
- `P2` `recommended_improvement` **Governance and Operations**: RECON-1 seat added; automate book vs broker mismatch halt
  - Seat exists under COMP-1; runtime recon loop still to implement.
- `P2` `recommended_improvement` **Governance and Operations**: Incident runbooks for SEC-HALT drills not versioned in repo
  - Kill switch exists in code; drill scorecards and restore checklist need artifacts.
- `P1` `structural_weakness` **Capital Stewardship**: Activity incentives still favor many small discretionary experiments
  - 100-trader floor + novel fleet can create trading-for-learning without quality filter. Stewardship veto exists for low edge but not for unnecessary concurrent identical setups.
- `P2` `recommended_improvement` **Capital Stewardship**: Berkshire desk moat/MOS gate is live; scorecards still manual
  - BRK-TRD* proposals require moat_score and margin_of_safety metadata before RISK-1.
- `P2` `dissent` **Capital Stewardship**: Dissent: retiring mean-reversion scouts entirely is too aggressive for a lab
  - Keep SCOUT/MR-style cohorts in paper with stewardship veto and fixed $1–2 sizing; do not delete the experiment.
- `P1` `architecture_decision` **Quantitative Research**: Critique resolution: single ResearchSignal schema remains mandatory
  - Intel and quant may both publish, but payload must be ResearchSignal.
- `P1` `dissent` **Capital Stewardship**: Critique: do not confuse lab breadth with production capital allocation
  - Paper cohorts may be wide; binding capital stays tiny and comparable.
