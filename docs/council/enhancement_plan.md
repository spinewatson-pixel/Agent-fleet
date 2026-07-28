# Institutional Design Council — Enhancement Plan

Generated: `2026-07-28T19:53:30.312509+00:00`
Organization: **watchfloor quant lab** (registry v0.2.0)
Agents: `{'total_agents': 279, 'proposers': 128, 'executors': 1, 'divisions': 12}`

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
- Critique: Trading Ops must not unlock live microstructure before correlation controls — Slippage ledgers are fine in paper; live hooks stay gated at Phase 5.
- Critique: do not confuse lab breadth with production capital allocation — Paper cohorts may be wide; binding capital stays tiny and comparable.

## Implementation tasks by priority
### P0
1. **Proposers lack measurable setup-detection rules in registry** (Quantitative Research)
   - Generate AgentOperatingContract stubs for every proposer with setup_detection_rules, entry/exit/stop, and invalidation fields; block paper proposal if contract incomplete.
   - Seats: FIT-1, STAT-1, HYPO-1, BACK-1
2. **Agent ceiling exceeded by roster design** (Governance and Operations)
   - Open GOV-CHAIR proposal: (a) raise ceiling with written rationale, or (b) mark excess cohorts ON-DEMAND/RETIRED until under ceiling.
   - Seats: GOV-CHAIR, HUMAN-1, LIFE-1
3. **Critique: Trading Ops must not unlock live microstructure before correlation controls** (Portfolio and Risk)
   - Keep live_execution_enabled=false until correlation + halt drills pass.
   - Seats: RISK-1, EXEC-1
4. **Unified enhance sequence adopted** (Chief Architecture)
   - Execute tasks_by_priority in order; do not skip P0.
   - Seats: GOV-CHAIR, ARCH-1, HUMAN-1
5. **Watchfloor IDs remain canonical; council is designer/supervisor layer** (Chief Architecture)
   - Keep IDC-* agents out of TradeProposal emission.
   - Seats: EXEC-1, RISK-1, GOV-CHAIR
### P1
1. **No persistent decision graph across Watchfloor runtime** (Systems Intelligence)
   - Add durable EventStore path + Watchfloor message schema bridge so every proposal/approval/fill writes lineage readable by MEM-1.
   - Seats: MEM-1, DQ-1, UI-1, TOOL-1
2. **Permissions exist in registry flags but are not enforced in the UI** (Systems Intelligence)
   - Gate UI agent creation behind council proposal objects validated against agent_ceiling and COMP-1 mandate checks.
   - Seats: GOV-CHAIR, HUMAN-1, UI-1
3. **Separate local paper inference from optional cloud workloads** (AI Infrastructure)
   - Document and enforce Environment.EXPERIMENTAL for ML self-builds.
   - Seats: ML-ARCH, RT-FORGE-1
4. **Comparable $1–2 sizing not applied as binding NAV policy in paper broker** (Portfolio and Risk)
   - Teach PaperBroker + RISK-1 to convert fixed-dollar cohort sizes and keep %NAV only for fund/quant desk sleeves that declare it.
   - Seats: CAP-1, RISK-1, EXEC-1
5. **Correlation cluster limits declared but not computed** (Portfolio and Risk)
   - Add rolling correlation cluster check before RISK-1 approval.
   - Seats: RISK-1, CORR-Q, CAP-1
6. **No regime engine owned by HEAD-TRADE / REG-1 wired into discretionary admission** (Trading Operations)
   - Add regime label service; block invalid-regime discretionary proposals.
   - Seats: HEAD-TRADE, REG-1, EXEC-1
7. **Multi-strategy coordination needs order schedule + slippage ledger** (Trading Operations)
   - Implement per-symbol daily order cap and slippage ledger on EXEC-1.
   - Seats: EXEC-1, CAP-1, HEAD-TRADE
8. **Quant thesis-exempt path must still require OOS evidence package** (Quantitative Research)
   - Require evidence_package_id on RT-* proposals before RISK-1 sees them.
   - Seats: FIT-1, COST-1, ENS-1
9. **ResearchSignal not produced by intel/pred desks in Watchfloor runtime** (Research and Strategy)
   - Route intel/pred outputs through ResearchSignal schema; strategies may only consume ResearchSignal IDs, never raw narrative blobs.
   - Seats: CORP-1, BULL-1, BEAR-1, FORE-1, HEAD-INTEL
10. **No reconciliation agent between internal book and paper broker** (Governance and Operations)
   - Add RECON-1 agent; mismatch → COMP-1 halt on new proposals.
   - Seats: COMP-1, EXEC-1, SEC-LEDGER
11. **Activity incentives still favor many small discretionary experiments** (Capital Stewardship)
   - Add activity budget: max new discretionary proposals/day/cohort; BRK-INV reviews duplicates of the same thesis family.
   - Seats: BRK-SAFE, BRK-INV, CAP-1, HEAD-TRADE
12. **Berkshire desk traders need quality gate before RISK-1** (Capital Stewardship)
   - Require moat_score and margin_of_safety fields on BRK-* TradeProposals.
   - Seats: BRK-MOAT, BRK-SAFE, BRK-TRD1, BRK-TRD2
13. **Critique resolution: single ResearchSignal schema remains mandatory** (Quantitative Research)
   - Reject non-ResearchSignal handoffs in message bus permissions.
   - Seats: FORE-1, MINE-1, CORP-1
14. **Critique: do not confuse lab breadth with production capital allocation** (Capital Stewardship)
   - Separate paper experiment capital from stewardship sleeve capital in portfolio state.
   - Seats: CAP-1, BRK-SAFE
### P2
1. **No real market/news/filings adapters behind MKT-1/ALT-1** (Market Information)
   - Implement MarketEvent adapters (bars, calendar, filings, news) with source_verified + tagging, delivering slices to intel/pred consumers.
   - Seats: MKT-1, ALT-1, DQ-1, GEO-1, MACRO-1
2. **Dual-source confirmation for macro prints not encoded** (Market Information)
   - Add dual_source_required flag for macro event types in DQ-1.
   - Seats: MACRO-1, FORE-1, DQ-1
3. **ML-ARCH autonomy budget not instrumented** (AI Infrastructure)
   - Add hard_rules.compute_ceiling and a model-routing health endpoint; ML-ARCH proposals above ceiling require GOV-CHAIR.
   - Seats: ML-ARCH, ML-VIT, ML-SEQ, TOOL-1
4. **EXEC-1 is both quality analyst and sole order placer** (Trading Operations)
   - Clarify EXEC-1 contract: place authorized paper orders; ATTR-1 owns slippage scorecards.
   - Seats: EXEC-1, ATTR-1
5. **No walk-forward / OOS harness wired to HYPO-1 and BACK-1** (Quantitative Research)
   - Build hypothesis registry + point-in-time backtest queue with FIT-1/COST-1 veto.
   - Seats: HYPO-1, BACK-1, STAT-1, FIT-1, COST-1
6. **Bull/Bear split authors need conflict metadata on case files** (Research and Strategy)
   - Enforce separate author_id on case file versions in org memory.
   - Seats: BULL-1, BEAR-1, MEM-1
7. **Incident runbooks for SEC-HALT drills not versioned in repo** (Governance and Operations)
   - Add docs/runbooks/halt_drill.md and automate SEC-DRILL quarterly checklist.
   - Seats: SEC-HALT, SEC-DRILL, SEC-RESTORE, SEC-LEDGER
8. **Dissent: retiring mean-reversion scouts entirely is too aggressive for a lab** (Capital Stewardship)
   - Retain MR/scout cohorts; tag as experimental with elevated reject sensitivity.
   - Seats: SCOUT-L2, SCOUT-S2, BRK-SAFE
### P3
- (none)

## Full findings
- `P1` `missing_capability` **Systems Intelligence**: No persistent decision graph across Watchfloor runtime
  - MEM-1 / DQ-1 exist as seats, but agent-to-agent lineage is only implemented inside the Python paper org, not as a shared Watchfloor event bus every division writes to.
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
- `P1` `structural_weakness` **Portfolio and Risk**: Comparable $1–2 sizing not applied as binding NAV policy in paper broker
  - Watchfloor mandates fixed $1–2 for cohort comparability, but paper fills currently size by %NAV suggestions.
- `P1` `missing_capability` **Portfolio and Risk**: Correlation cluster limits declared but not computed
  - CORR-Q and RISK-1 lack a live correlation matrix feeding max_correlated_cluster_pct.
- `P1` `missing_capability` **Trading Operations**: No regime engine owned by HEAD-TRADE / REG-1 wired into discretionary admission
  - Proposers accept regimes loosely; WatchfloorOrganization does not consult REG-1.
- `P1` `recommended_improvement` **Trading Operations**: Multi-strategy coordination needs order schedule + slippage ledger
  - 102 trading-division agents can flood the same name without ADV throttling.
- `P2` `structural_weakness` **Trading Operations**: EXEC-1 is both quality analyst and sole order placer
  - Watchfloor nick 'Fill Check' mixes measurement with authority. Keep execution authority, but split attribution of fill quality to ATTR-1.
- `P0` `missing_capability` **Quantitative Research**: Proposers lack measurable setup-detection rules in registry
  - 128 proposers have role text only. Operating contracts require exact setup expressions before promotion beyond design.
- `P2` `missing_capability` **Quantitative Research**: No walk-forward / OOS harness wired to HYPO-1 and BACK-1
  - Lab seats exist; controlled improvement sequence is documented but not automated.
- `P1` `recommended_improvement` **Quantitative Research**: Quant thesis-exempt path must still require OOS evidence package
  - Exemption from narrative thesis is not exemption from validation.
- `P1` `missing_capability` **Research and Strategy**: ResearchSignal not produced by intel/pred desks in Watchfloor runtime
  - CORP-1/BULL-1/BEAR-1/FORE-1 exist, but paper path synthesizes a single CORP-1 signal. Standardized research→signal handoff is incomplete.
- `P2` `recommended_improvement` **Research and Strategy**: Bull/Bear split authors need conflict metadata on case files
  - BULL-1 and BEAR-1 must never share authorship on the same case version.
- `P0` `structural_weakness` **Governance and Operations**: Agent ceiling exceeded by roster design
  - Registry has 279 agents vs ceiling 150. Either raise ceiling via council vote or prune/retire cohorts.
- `P1` `missing_capability` **Governance and Operations**: No reconciliation agent between internal book and paper broker
  - RECON seat planned but absent; breaks cannot halt new risk today.
- `P2` `recommended_improvement` **Governance and Operations**: Incident runbooks for SEC-HALT drills not versioned in repo
  - Kill switch exists in code; drill scorecards and restore checklist need artifacts.
- `P1` `structural_weakness` **Capital Stewardship**: Activity incentives still favor many small discretionary experiments
  - 100-trader floor + novel fleet can create trading-for-learning without quality filter. Stewardship veto exists for low edge but not for unnecessary concurrent identical setups.
- `P1` `recommended_improvement` **Capital Stewardship**: Berkshire desk traders need quality gate before RISK-1
  - BRK-TRD1/2 should require BRK-MOAT + BRK-SAFE scores on the proposal metadata.
- `P2` `dissent` **Capital Stewardship**: Dissent: retiring mean-reversion scouts entirely is too aggressive for a lab
  - Keep SCOUT/MR-style cohorts in paper with stewardship veto and fixed $1–2 sizing; do not delete the experiment.
- `P0` `dissent` **Portfolio and Risk**: Critique: Trading Ops must not unlock live microstructure before correlation controls
  - Slippage ledgers are fine in paper; live hooks stay gated at Phase 5.
- `P1` `architecture_decision` **Quantitative Research**: Critique resolution: single ResearchSignal schema remains mandatory
  - Intel and quant may both publish, but payload must be ResearchSignal.
- `P1` `dissent` **Capital Stewardship**: Critique: do not confuse lab breadth with production capital allocation
  - Paper cohorts may be wide; binding capital stays tiny and comparable.
