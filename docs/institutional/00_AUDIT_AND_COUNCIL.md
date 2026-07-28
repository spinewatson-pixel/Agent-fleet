# Institutional Design Council — Audit & Unified Resolution

**Organization:** Agent Fleet  
**Environment objective:** Fully functional **paper trading** first. Live execution **disabled**.  
**Date:** 2026-07-28  
**Status:** Bootstrap redesign — no prior executable skeleton found in repository

---

## 1. Audit of Current Agent Setup

### What exists in the repository
| Artifact | Status |
|---|---|
| `README.md` (`# Agent-fleet`) | Present |
| Agent source code | **Missing** |
| Strategy skeletons / configs | **Missing** |
| Operating contracts | **Missing** |
| Message schemas / bus | **Missing** |
| Risk / portfolio / execution layers | **Missing** |
| Tests | **Missing** |

### Preservable components
- Repository name and intent: **Agent-fleet** (multi-agent trading organization).
- No executable logic to preserve; redesign is a **greenfield institutional bootstrap**, not a rip-and-replace of working agents.

### Structural implication
The council cannot “refactor existing agents.” It must **define** the organization, then implement a paper-trading operating chain with provisional strategy agents until the operator confirms real strategy skeletons.

---

## 2. Missing Information Required From Operator

Answer only what you know; defaults below apply until then.

1. **Strategy inventory:** Do you have named strategies outside this repo? List each name, edge hypothesis, asset class, and holding period.
2. **Paper NAV:** Starting paper capital? *(Default: `$100,000`)*
3. **Universe:** US equities only, ETFs, futures, crypto, options? *(Default: liquid US equities + index/sector ETFs)*
4. **Data providers:** What market/news/filings APIs are available? *(Default: pluggable adapters; paper uses injected prices)*
5. **Broker for future live:** Which broker API when authorized? *(Default: none; live gateway shut down)*
6. **Jurisdiction / compliance:** Any restricted symbols, PDT, or disclosure rules? *(Default: paper governance stubs)*
7. **Tech constraints:** Must use a specific stack (Python/TS, local-only)? *(Default: Python 3.11+, local paper runtime)*
8. **Human approval:** Who is the final human authority to enable limited live capital? *(Default: explicit config flag + GOV+RISK dual control; currently impossible)*

---

## 3. Independent Team Audits

### 3.1 Palantir-inspired Systems Intelligence
**Findings**
- No org graph, data lineage, shared context store, or audit trail.
- No agent relationship map or permission model.
- Decision path from raw data → trade is undefined.

**Recommendations**
- Introduce typed `Envelope` messages with `correlation_id` lineage.
- Require every agent to load an `AgentOperatingContract`.
- SYS-ORCH-001 owns routing and conflict resolution; append-only audit log on the bus.

**Evidence:** Empty repo; institutional systems fail without lineage.  
**Priority:** P0

### 3.2 Bloomberg-inspired Market Information
**Findings**
- No market feed, news, filings, earnings calendar, macro, alerts, or normalization.

**Recommendations**
- Split `DATA-MKT-001` (prices/calendars) and `DATA-NEWS-001` (news/filings/macro).
- `DATA-VAL-001` enforces schema, staleness, outlier, and source-trust checks before fan-out.
- Tag every item with `source_id`, symbols, categories; reject unverified critical events.

**Evidence:** Strategies without validated inputs produce unsafe proposals.  
**Priority:** P0

### 3.3 NVIDIA-inspired AI Infrastructure
**Findings**
- No model routing, compute budget, embedding/memory store, latency SLOs, or failover.

**Recommendations**
- `AI-INFRA-001` routes research/LLM jobs; separate local inference vs cloud.
- Hard caps on experimental compute; production inference read-only to experimental weights.
- Monitor p95 latency; failover to degraded rules-only mode.

**Evidence:** Unbounded model calls create cost/latency and silent drift.  
**Priority:** P1

### 3.4 BlackRock-inspired Portfolio and Risk
**Findings**
- No portfolio construction, exposure/correlation caps, stress, drawdown, or liquidity controls.
- If strategies self-size, firm risk is unmanageable.

**Recommendations**
- `PORT-ALLOC-001` sizes to book; `RISK-APPR-001` has veto + emergency halt.
- Firm limits: position, sector, strategy, gross/net, daily loss, drawdown, min cash.
- Scenario/stress hooks before live; paper enforces hard numeric limits now.

**Evidence:** Multi-strategy without book-level risk is a known blow-up pattern.  
**Priority:** P0

### 3.5 Citadel-inspired Trading Operations
**Findings**
- No OMS, regime gate, slippage model, multi-strategy coordination, or position monitor.

**Recommendations**
- Paper OMS via `EXEC-PAPER-001`; `EXEC-LIVE-001` shutdown until gates pass.
- `MON-REGIME-001` gates strategy validity; `MON-LIVE-001` watches stops/invalidations.
- Slippage/fee model on every paper fill.

**Evidence:** Execution quality and regime mismatch dominate live underperformance.  
**Priority:** P0

### 3.6 Renaissance-inspired Quantitative Research
**Findings**
- No hypothesis registry, feature store, OOS/walk-forward, or multiple-testing control.

**Recommendations**
- `RSH-QUANT-001` publishes signals only; never trades.
- `LEARN-CTRL-001` enforces sequential testing gates; deflate significance for multiple tests.
- Separate backtest vs paper vs production artifacts.

**Evidence:** Overfitting is the default failure mode of agent “self-improvement.”  
**Priority:** P0

### 3.7 Goldman-inspired Research and Strategy
**Findings**
- No standardized research → signal contract for fundamental/event/macro/thematic work.

**Recommendations**
- `RSH-FUND-001` emits `research_note` + `signal` with conviction, catalysts, risks.
- Event/quality/macro/sector strategies consume standardized fields only.

**Evidence:** Free-text research cannot be validated or attributed.  
**Priority:** P1

### 3.8 JPMorgan-inspired Governance and Operations
**Findings**
- No approval authority matrix, reconciliation, incident process, or escalation.

**Recommendations**
- `GOV-COMP-001` owns permissions, incidents, deployment approval, dual-control for live.
- Separation of duties: strategy cannot approve/execute/self-score for live authority.
- Mandatory incident report for halt recovery.

**Evidence:** Without governance, “autonomous” systems accumulate silent control failures.  
**Priority:** P0

### 3.9 Berkshire-inspired Capital Stewardship
**Findings**
- No check against activity-for-activity’s-sake or low-quality risk seeking.

**Recommendations**
- `CAP-STEW-001` may veto/reduce; requires economic thesis quality.
- `STRAT-QUAL-001` long-horizon book with low turnover.
- Prefer inaction when edge is unclear.

**Evidence:** Turnover without edge destroys capital after costs.  
**Priority:** P0 for veto path; P1 for full quality scoring models

---

## 4. Cross-Team Critique

| Critic | Target | Critique |
|---|---|---|
| Risk | Citadel Ops | Rejects any design where execution can fire without risk approval. |
| Governance | Quant Research | Rejects auto-promotion of models to production from backtest alone. |
| Stewardship | Momentum/MR strategies | Warns against high turnover; demands regime gates and cost-aware acceptance tests. |
| Systems | AI Infra | Requires all model I/O on audited bus — no side-channel LLM trades. |
| Market Info | All strategies | Blocks proposals if `DATA-VAL-001` has not validated prices. |
| Quant | Fundamental Research | Demands numeric signal fields, not narrative-only outputs. |
| Portfolio | Individual strategies | Vetoes strategy-local capital limits as authority; sizing is book-level. |
| Citadel Ops | Stewardship | Accepts veto but requires deterministic SLA so ops is not blocked indefinitely — paper uses sync decision. |
| Governance | Live Execution | Absolute veto on enabling `EXEC-LIVE-001` until acceptance phases complete. |

---

## 5. Chief Architecture Resolution (Unified Design)

**Decision A — Operating chain (binding)**  
`Data ingestion → validation → research → signal → strategy proposal → independent validation → portfolio evaluation → risk approval → capital stewardship → paper execution → monitoring → attribution → controlled improvement`

**Decision B — Separation of duties (binding)**  
Strategy agents may **only** `PROPOSE`. They shall not set firm capital limits, approve their own trades, execute orders, or evaluate their own performance for live decision authority.

**Decision C — Dual veto (binding)**  
`RISK-APPR-001` and `GOV-COMP-001` hold emergency halt. `CAP-STEW-001` may veto on quality/activity grounds. Risk may veto unsafe portfolio recommendations.

**Decision D — Environments (binding)**  
`backtest` / `experimental` / `paper` / `production`. Experimental agents cannot mutate production rules or access unrestricted capital.

**Decision E — Learning (binding)**  
Changes: document → statistical test → OOS → paper → risk review → version → approve → gradual deploy.

**Decision F — Bootstrap fleet (provisional)**  
Seven strategy agents + full control-plane agents (see registry). Replace/extend when operator provides real skeletons.

**Dissenting views recorded**
- Stewardship preferred fewer than seven strategies initially; Architecture kept seven as **paper scaffolds** with low size caps — accepted with Risk concurrence.
- AI Infra wanted GPU cluster specs now; deferred to Phase 2 (P1) — paper runs rules/signals without heavy inference.

**Implementation priority:** P0 chain + contracts + paper OMS + tests → P1 data adapters + research depth → P2 live shadow.

---

## 6. Veto Log

| ID | Vetoing team | Unsafe recommendation vetoed | Alternative accepted |
|---|---|---|---|
| V-1 | Risk | “Strategies self-size and self-approve for speed” | Portfolio sizes; Risk approves |
| V-2 | Governance | “Enable live micro-orders early for learning” | Paper only until phase gates |
| V-3 | Risk | “Experimental agent hot-patches production rules” | Learning state machine + dual approval |
| V-4 | Stewardship | “Maximize number of daily trades” | Thesis quality gate; prefer inaction |
| V-5 | Governance | “Single agent owns research+risk+execution” | Split roles per authority map |

---

## 7. Bootstrap Agent Inventory

### Control plane
| ID | Role |
|---|---|
| SYS-ORCH-001 | Orchestration / architecture |
| DATA-MKT-001 | Market data ingestion |
| DATA-NEWS-001 | News/filings/macro ingestion |
| DATA-VAL-001 | Information validation |
| RSH-FUND-001 | Fundamental/event research |
| RSH-QUANT-001 | Quant research |
| SIG-VAL-001 | Independent validation |
| PORT-ALLOC-001 | Portfolio construction |
| RISK-APPR-001 | Risk approval + halt |
| CAP-STEW-001 | Capital stewardship |
| EXEC-PAPER-001 | Paper execution |
| EXEC-LIVE-001 | Live execution (**SHUTDOWN**) |
| MON-LIVE-001 | Position monitoring |
| MON-REGIME-001 | Regime classification |
| REV-ATTR-001 | Attribution |
| LEARN-CTRL-001 | Controlled learning |
| GOV-COMP-001 | Governance |
| AI-INFRA-001 | AI infrastructure |

### Strategy fleet (provisional)
| ID | Strategy |
|---|---|
| STRAT-MOM-001 | Trend momentum |
| STRAT-MR-001 | Mean reversion |
| STRAT-EVT-001 | Event/earnings |
| STRAT-MACRO-001 | Macro regime |
| STRAT-QUAL-001 | Quality value long-term |
| STRAT-SECROT-001 | Sector rotation |
| STRAT-PAIRS-001 | Statistical pairs |

---

## Concrete tasks spawned by this resolution
1. Encode contracts in code + export JSON.  
2. Implement message bus + paper operating chain.  
3. Enforce risk engine numeric limits.  
4. Encode learning state machine.  
5. Write acceptance tests as phase gates.  
6. Publish org/communication/authority/data maps.  
7. Keep live execution flag `False`.
