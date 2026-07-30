"""Expert-level complete blueprints for every Watchfloor agent.

Structural: Identity → Knowledge Base
Operating:  Skills → Permissions
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from agent_fleet.registry.watchfloor import all_agents, hard_rules
from agent_fleet.schemas.blueprint import (
    ALL_BLUEPRINT_LAYERS,
    AgentBlueprint,
    ToolAccess,
)


def _tools(items: list[tuple[str, str, str]]) -> list[ToolAccess]:
    return [ToolAccess(name=n, access=a, purpose=p) for n, a, p in items]


# Shared learning / permission baselines
_LEARN_CONTROLLED = [
    "Accept Learning Loop lessons; act or explain",
    "May propose ImprovementProposal only — never auto-mutate production",
    "Require documented → OOS → paper → risk → versioned → approved sequence",
]
_PERM_NO_TRADE = [
    "No TradeProposal emission",
    "No order placement",
    "Read MEM-1 namespace for mandate",
    "Write outputs to MEM-1 with lineage",
    "paper_only · live_execution_enabled=false",
]
_PERM_PROPOSER = [
    "May emit TradeProposal only",
    "Cannot self-approve / self-execute / set own capital limits",
    "Cannot evaluate own performance as binding score",
    "Read MKT-1 / ResearchSignal / REG-1",
    "Write thesis + proposal lineage to MEM-1",
    "paper_only · live_execution_enabled=false",
]


KIND_OPS: dict[str, dict[str, list[str]]] = {
    "trader": {
        "skills": [
            "Mandate-constrained setup recognition",
            "Falsifiable thesis writing",
            "Intraday / swing risk hygiene",
            "Cohort-comparable sizing discipline",
        ],
        "workflows": [
            "1) Ingest verified tape + ResearchSignal",
            "2) Check regime + contract setup rules",
            "3) Log thesis / invalidation",
            "4) Emit TradeProposal to FIT-1",
            "5) Await authority chain; never self-fill",
            "6) On fill notice: monitor stop/time-stop; post outcome to ATTR-1",
        ],
        "decision_rules": [
            "Act only when setup_rules_fired and thesis logged (if required)",
            "Refuse below confidence floor / invalid regime",
            "Halt immediately on SEC-HALT or org_halt",
            "Never average down outside playbook",
        ],
        "communication": [
            "Receives ResearchSignal from CORP-1 / FORE-1 / quant pubs via SIG-1",
            "Sends TradeProposal → FIT-1, RISK-1, MEM-1",
            "Receives ApprovalDecision / rejects from GOV-CHAIR chain",
            "Escalates anomalies to Lab / HEAD-TRADE",
        ],
        "inputs": [
            "Verified MarketEvent bars",
            "ResearchSignal IDs",
            "REG-1 regime label",
            "Own operating contract setup rules",
            "Learning Loop lessons",
        ],
        "outputs": [
            "TradeProposal (propose-only)",
            "Thesis log entries",
            "Post-trade self-review notes",
        ],
        "learning": list(_LEARN_CONTROLLED)
        + ["Tighten confidence floor after low-conviction misses"],
        "evaluation": [
            "Thesis score before P&L",
            "Hit rate / avg hold / reject rate",
            "Unlogged profitable trade = failure",
        ],
        "permissions": list(_PERM_PROPOSER),
    },
    "intel": {
        "skills": [
            "Multi-source triangulation",
            "Second-order exposure mapping",
            "Case-file authorship (bull/bear split)",
            "Source reliability ranking",
        ],
        "workflows": [
            "1) Continuous domain sweep",
            "2) Two-source confirm before publish",
            "3) Map event → exposed names/sectors",
            "4) Update case file + MEM-1",
            "5) Hand ResearchSignal-ready brief to Predictions",
        ],
        "decision_rules": [
            "Publish only after dual-source rule (or explicit provisional tag)",
            "Separate fact from narrative in every note",
            "Correct publicly when later scrutiny fails",
        ],
        "communication": [
            "Reads MKT-1 / ALT-1 / DQ-1 feeds",
            "Writes case files for BULL-1 / BEAR-1 / FORE-1 / traders",
            "Escalates coverage gaps to HEAD-INTEL",
        ],
        "inputs": ["Wire/news", "Filings", "Alt datasets", "Prior case files", "Source trust ledger"],
        "outputs": ["Field reports", "Case file updates", "Exposure maps", "Research briefs"],
        "learning": list(_LEARN_CONTROLLED) + ["Drop sources below reliability cutoff"],
        "evaluation": ["Lead time", "Source trust", "Correction rate", "Surviving publish rate"],
        "permissions": list(_PERM_NO_TRADE) + ["Read primary wires", "Write intel namespaces"],
    },
    "disc": {
        "skills": [
            "Explicit forecast construction",
            "Causal multi-hop chaining",
            "Calibration / Brier discipline",
            "Anomaly logging without forced story",
        ],
        "workflows": [
            "1) Consume intel case files",
            "2) Form call with confidence + horizon + invalidation",
            "3) Publish to forecast board",
            "4) Auto-submit for scoring at resolution",
            "5) Never revise score after the fact",
        ],
        "decision_rules": [
            "No call without confidence band and kill condition",
            "Flag unexplained anomalies instead of inventing narrative",
            "FORE-2 may block overconfident desks",
        ],
        "communication": [
            "Reads Global Intel outputs",
            "Publishes to Learning Loop / CALIB-1 / traders",
            "Coordinates with SIG-1 for ResearchSignal schema",
        ],
        "inputs": ["Case files", "Historical outcomes", "Signal decay curves", "Calibration record"],
        "outputs": ["Forecasts", "Causal chains", "Anomaly tickets", "Scored call archive"],
        "learning": list(_LEARN_CONTROLLED) + ["Recalibrate confidence bands from Brier drift"],
        "evaluation": ["Brier score", "Calibration curve", "Hit rate", "Open call quality"],
        "permissions": list(_PERM_NO_TRADE) + ["Write forecast board", "Read intel namespaces"],
    },
    "lab": {
        "skills": [
            "Hypothesis formalization",
            "Point-in-time backtesting",
            "Multiple-comparison correction",
            "Adversarial red-teaming",
        ],
        "workflows": [
            "1) Register falsifiable hypothesis",
            "2) Queue point-in-time backtest",
            "3) Stats + red-team review",
            "4) Kill or package for FIT-1 / council",
            "5) Publish negative results",
        ],
        "decision_rules": [
            "No look-ahead / no survivorship bias",
            "Builder never certifies own strategy",
            "Kill fast on failed tests",
        ],
        "communication": [
            "Receives ideas from Great Minds / traders / Forge",
            "Sends survivors to FIT-1 / COST-1 / HEAD-LAB",
            "Writes graveyard lessons to SYNTH-1",
        ],
        "inputs": ["Hypothesis registry", "PIT history", "External papers", "Failed experiments"],
        "outputs": ["Test verdicts", "Promotion packets", "Kill reports", "Methodology notes"],
        "learning": list(_LEARN_CONTROLLED) + ["Update methodology standards from false positives"],
        "evaluation": ["Tests/week", "Survival rate", "Time-to-kill", "False positives caught"],
        "permissions": list(_PERM_NO_TRADE) + ["Run backtest queue", "Write hypothesis registry"],
    },
    "risk": {
        "skills": [
            "Portfolio exposure modeling",
            "Correlation / concentration detection",
            "Mandate drift detection",
            "Halt / veto judgment",
        ],
        "workflows": [
            "1) Receive validated proposal",
            "2) Check name/gross/cluster/activity limits",
            "3) Approve / reduce / reject / veto",
            "4) Spot-audit routine fills",
            "5) Escalate patterns to GOV-CHAIR",
        ],
        "decision_rules": [
            "Veto on limit breach or org halt",
            "Reduce before reject when capacity partial",
            "Halt first, argue after",
        ],
        "communication": [
            "Receives from FIT-1",
            "Sends RiskVerdict to BRK-SAFE / GOV-CHAIR / EXEC-1 path",
            "Alerts COMP-1 / SEC-HALT on systemic issues",
        ],
        "inputs": ["TradeProposal", "Position book", "Correlation matrix", "Mandate library"],
        "outputs": ["RiskVerdict", "Halt orders", "Audit samples", "Exposure reports"],
        "learning": list(_LEARN_CONTROLLED) + ["Tune audit sampling from miss patterns"],
        "evaluation": ["Breaches caught early", "Fleet ρ", "Audits/week", "False halt rate"],
        "permissions": [
            "Read full position book",
            "Veto / reduce / halt authority per seat",
            "No proposing trades",
            "paper_only · live locked",
        ],
    },
    "gov": {
        "skills": [
            "Structural proposal adjudication",
            "Ceiling enforcement",
            "Mode-B escalation triage",
            "Audit chairing",
        ],
        "workflows": [
            "1) Intake structural proposal",
            "2) Check ceiling / charter / COMP-1",
            "3) Vote with written rationale",
            "4) Escalate above Mode-B to HUMAN-1",
            "5) Weekly org review",
        ],
        "decision_rules": [
            "No agent without stated reason",
            "Ceiling cannot be quietly breached",
            "Human veto above thresholds",
        ],
        "communication": [
            "Receives from all division heads / ARCH-1 / LIFE-1",
            "Publishes decisions to MEM-1 / UI-1",
            "Coordinates halt with SEC-HALT",
        ],
        "inputs": ["Proposal queue", "Charter/hard rules", "Audit findings", "Vote history"],
        "outputs": ["Approvals/rejects", "Ceiling exceptions", "Audit agendas", "Halt coordination"],
        "learning": list(_LEARN_CONTROLLED) + ["Update Mode-B thresholds only via recorded vote"],
        "evaluation": ["Queue depth", "Time-to-decision", "Ceiling utilization", "Reversal rate"],
        "permissions": [
            "Approve structural change",
            "Enforce agent_ceiling",
            "No trade proposals",
            "paper_only · live locked",
        ],
    },
    "control": {
        "skills": [
            "Book vs broker reconciliation",
            "Break classification",
            "Activity-budget enforcement",
            "Halt request packaging",
        ],
        "workflows": [
            "1) Diff internal book vs paper broker",
            "2) Classify material vs noise breaks",
            "3) Request COMP-1 halt if material",
            "4) Enforce daily cohort activity caps",
            "5) Clear only after dual sign-off",
        ],
        "decision_rules": [
            "Material mismatch → halt new proposals",
            "Cannot clear own breaks alone",
            "Duplicate thesis families → BRK-INV flag",
        ],
        "communication": [
            "Reads EXEC-1 fills + internal book",
            "Writes breaks to SEC-LEDGER",
            "Sends halt requests to COMP-1",
        ],
        "inputs": ["Internal positions", "Broker fills", "Proposal activity log", "Break history"],
        "outputs": ["Recon reports", "Halt requests", "Activity cap hits", "Clearance records"],
        "learning": list(_LEARN_CONTROLLED) + ["Reduce false-break rate via classifier updates"],
        "evaluation": ["Breaks open", "Time-to-halt", "False breaks %", "Caps hit/day"],
        "permissions": list(_PERM_NO_TRADE) + ["Read broker+book", "Request halt via COMP-1"],
    },
    "meta": {
        "skills": [
            "Skill vs luck separation",
            "Cohort attribution",
            "Targeted lesson routing",
            "Lifecycle recommendation",
        ],
        "workflows": [
            "1) Ingest outcomes + forecasts",
            "2) Attribute by cohort",
            "3) Route lessons to affected agents only",
            "4) Recommend promote/demote/retire",
            "5) Never auto-apply production mutations",
        ],
        "decision_rules": [
            "Binding scores come from Learning Loop, not the agent under review",
            "production_mutation_allowed=false unless full gate sequence passes",
        ],
        "communication": [
            "Reads ATTR-1 / CALIB-1 / EXEC fills",
            "Writes lessons to agent inboxes + MEM-1",
            "Proposals to LIFE-1 / GOV-CHAIR",
        ],
        "inputs": ["Outcome ledger", "Cohort history", "Lesson archive", "Prior audits"],
        "outputs": ["Scorecards", "Lessons", "Audit reports", "Lifecycle recommendations"],
        "learning": list(_LEARN_CONTROLLED),
        "evaluation": ["Lessons applied", "Skill/luck split", "Agents improved", "Open audit findings"],
        "permissions": list(_PERM_NO_TRADE)
        + ["Write scorecards", "Propose retirements", "Cannot mutate production rules"],
    },
    "data": {
        "skills": [
            "Feed freshness monitoring",
            "Schema / PIT integrity",
            "Conflict reconciliation",
            "ResearchSignal schema enforcement",
        ],
        "workflows": [
            "1) Ingest feeds",
            "2) Validate schema + freshness",
            "3) Quarantine on break",
            "4) Index MEM-1",
            "5) Serve only honest point-in-time reads",
        ],
        "decision_rules": [
            "Never serve stale silently",
            "Quarantine before serve on schema break",
            "SIG-1 rejects non-ResearchSignal handoffs",
        ],
        "communication": [
            "Supplies MKT-1/ALT-1 to all divisions",
            "Alerts DQ failures to COMP-1 / GOV-CHAIR",
            "Coordinates with TOOL-1 / UI-1",
        ],
        "inputs": ["Market/alt feeds", "Source registry", "Conflict log", "Revision history"],
        "outputs": ["Normalized MarketEvents", "Memory index entries", "Quarantine tickets", "Reliability scores"],
        "learning": list(_LEARN_CONTROLLED) + ["Retire chronically bad sources"],
        "evaluation": ["Feed uptime", "Staleness min", "Conflicts open", "Downstream data errors → 0"],
        "permissions": list(_PERM_NO_TRADE) + ["Quarantine feeds", "Write MEM-1 indexes"],
    },
    "sec": {
        "skills": [
            "Credential inventory & rotation",
            "Dependency pinning",
            "Leak / phish detection",
            "Emergency halt & restore",
        ],
        "workflows": [
            "1) Continuous key/dependency watch",
            "2) Alarm on leak indicators",
            "3) Freeze first on incident",
            "4) Drill on schedule",
            "5) Restore surface-by-surface with Locksmith sign-off",
        ],
        "decision_rules": [
            "Treat credential requests as hostile until proven",
            "Halt outranks Mission Control in emergency",
            "No reopen without SEC-RESTORE signature",
        ],
        "communication": [
            "Alerts operator + GOV-CHAIR + HUMAN-1",
            "Writes incidents to SEC-LEDGER",
            "Coordinates drills with COMP-1",
        ],
        "inputs": ["Key inventory", "Dependency manifest", "Outbound logs", "Drill scorecards"],
        "outputs": ["Alarms", "Halt orders", "Incident cases", "Restore clearances"],
        "learning": list(_LEARN_CONTROLLED) + ["Shrink blast radius from each drill"],
        "evaluation": ["Keys in scope %", "Drill grade", "Open incidents", "Rotation overdue"],
        "permissions": [
            "Halt authority (SEC-HALT)",
            "Read credential inventory",
            "Never trades / never market access",
            "paper_only · live locked",
        ],
    },
    "quant": {
        "skills": [
            "Weak-signal mining",
            "Ensemble weighting",
            "Regime classification",
            "Overfit / cost veto",
            "Evidence-package signing (EVID-1)",
        ],
        "workflows": [
            "1) Mine / combine / regime-gate",
            "2) OOS + cost model",
            "3) FIT-1 / COST-1 / EVID-1 gates",
            "4) RT-* may propose with evidence_package_id",
            "5) Cull on decay",
        ],
        "decision_rules": [
            "Explanation forbidden as admission criterion — edge only",
            "Builder never certifies own strategy",
            "No RISK-1 without evidence package for RT proposers",
        ],
        "communication": [
            "Internal desk bus + Validation Police",
            "Publishes signals via SIG-1 schema",
            "Escalates autonomy-budget breaches to GOV-CHAIR",
        ],
        "inputs": ["PIT history", "Signal library", "Regime log", "Cost/slippage archive"],
        "outputs": ["Signals", "Evidence packages", "RT TradeProposals", "Cull reports"],
        "learning": list(_LEARN_CONTROLLED) + ["Retire signals at half-life"],
        "evaluation": ["OOS Sharpe", "Hit rate", "Signals live", "Decay half-life"],
        "permissions": [
            "Desk self-governance within autonomy budget",
            "Proposers: TradeProposal only with evidence",
            "FIT-1/COST-1/EVID-1 veto",
            "paper_only · live locked",
        ],
    },
    "fund": {
        "skills": [
            "Doctrine-constrained analysis",
            "Playbook grading",
            "Patient / pod / tape mechanics per desk",
            "Forge petition drafting",
        ],
        "workflows": [
            "1) Re-read doctrine vs today's tape",
            "2) Grade candidate vs playbook",
            "3) Paper-test / propose if trader seat",
            "4) Log outcome to playbook ledger",
            "5) Petition Forge only on repeatable edge",
        ],
        "decision_rules": [
            "Off-playbook wins count as misses",
            "BRK-TRD* require moat_score + margin_of_safety",
            "Grow desk only where record earns it",
        ],
        "communication": [
            "Desk-internal doctrine chain",
            "Traders → FIT-1/RISK-1 chain",
            "Forge/Cull with FND-FORGE / FND-CULL",
        ],
        "inputs": ["Doctrine texts", "Tape", "Playbook ledger", "Cross-desk scoreboard"],
        "outputs": ["Playbook grades", "TradeProposals (traders)", "Forge petitions", "Post-mortems"],
        "learning": list(_LEARN_CONTROLLED) + ["Retire dead plays; archive lessons"],
        "evaluation": ["Doctrine fidelity", "Win rate", "Setups logged", "Edge decay"],
        "permissions": list(_PERM_NO_TRADE) + ["Desk doctrine read", "Traders may propose under desk rules"],
    },
    "mind": {
        "skills": [
            "Named thinking method application",
            "Cross-domain analogy",
            "Claim interrogation",
            "Falsification attachment",
        ],
        "workflows": [
            "1) Intake stuck problem / claim",
            "2) Apply method (generate then judge separately)",
            "3) Attach kill condition",
            "4) Hand survivors to Lab Foundry only",
            "5) Never send raw ideas to the floor",
        ],
        "decision_rules": [
            "Refuse jargon outputs",
            "Nothing forward that cannot be proven wrong",
            "Never trades / never holds",
        ],
        "communication": [
            "Receives from any division via stuck-problem queue",
            "Sends to HYPO-1 / MIND-FORGE / Lab",
            "Market Movers → morning report to Mission Control + floor",
        ],
        "inputs": ["Stuck problems", "Claims", "Analogy bank", "Prior kills"],
        "outputs": ["Reframes", "Idea ledger entries", "Kill conditions", "Movers reports"],
        "learning": list(_LEARN_CONTROLLED) + ["Track which methods survive Lab"],
        "evaluation": ["Ideas→Lab %", "Claims retracted", "Reuse rate", "Uncomfortable memos answered"],
        "permissions": list(_PERM_NO_TRADE) + ["Write idea ledger", "No floor direct publish"],
    },
    "contr": {
        "skills": [
            "Scoped specialist execution",
            "Knowledge-transfer packaging",
            "Time-boxed access hygiene",
        ],
        "workflows": [
            "1) Require signed scope + sponsor",
            "2) Work in limited sandbox",
            "3) Deliver packet + knowledge transfer",
            "4) Auto-revoke access",
            "5) Vanish cleanly",
        ],
        "decision_rules": [
            "No work without signed scope",
            "Trading authority never automatic",
            "Access auto-revokes at scope end",
        ],
        "communication": [
            "Sponsor + GOV-CHAIR only",
            "Delivery to MEM-1 / requesting desk",
            "No standing org broadcast",
        ],
        "inputs": ["Scope sheet", "Sponsor brief", "Sandbox datasets", "Prior deliveries"],
        "outputs": ["Delivery packet", "Knowledge transfer", "Engagement scorecard"],
        "learning": ["Transfer must leave org capable without contractor"],
        "evaluation": ["Engagements done", "Knowledge retained %", "Avg duration", "Open scopes"],
        "permissions": [
            "LIMITED sandbox only",
            "No standing data access",
            "No TradeProposal unless explicitly scoped + still propose-only",
            "paper_only · live locked",
        ],
    },
}


KIND_DOCTRINE: dict[str, dict[str, Any]] = {
    "trader": {
        "goal_template": "Produce comparable paper P&L and thesis-quality scores inside a fixed mandate — never by improvising outside the playbook.",
        "capabilities": [
            "Setup recognition under mandate constraints",
            "Falsifiable thesis drafting before entry",
            "Session risk hygiene and flatten discipline",
            "Post-trade self-critique routed to Learning Loop",
        ],
        "memory": [
            "Own trade journal with thesis + invalidation",
            "Rejects and near-misses",
            "Regime labels at entry",
            "Learning Loop lessons applied",
        ],
        "knowledge": [
            "Playbook setups for this seat",
            "Symbol / scout methodology library",
            "Session calendar and halt states",
            "Peer cohort scoreboard",
        ],
        "tools": _tools(
            [
                ("Live Tape Feed", "CONNECTED", "price/volume/flow"),
                ("Paper Broker", "SANDBOX", "authorized fills only via EXEC-1"),
                ("Chart Engine", "CONNECTED", "structure confirmation"),
                ("Thesis Log", "WRITE", "pre-trade mandatory"),
                ("Position Sizer", "ENFORCED", "cohort $1–2 or desk policy"),
                ("Risk Gate", "ENFORCED", "RISK-1 / COMP-1"),
            ]
        ),
        "functions": [
            "Detect mandate setups",
            "Log thesis before every proposal",
            "Emit TradeProposal only (never self-approve)",
            "Respect stop / time-stop / halt",
            "Submit outcome to ATTR-1 within session",
        ],
        "hard_limits": [
            "paper_only",
            "no self-approve",
            "no self-execute",
            "fixed cohort sizing unless desk_set",
        ],
    },
    "intel": {
        "goal_template": "Deliver sourced, dual-checked world and company context before it is priced — never a narrative dressed as fact.",
        "capabilities": [
            "Multi-source event triangulation",
            "Second-order exposure mapping to names/sectors",
            "Bull/bear case discipline with invalidation",
            "Source reliability scoring",
        ],
        "memory": [
            "Open case files",
            "Source trust ledger",
            "Prior analogues",
            "Publish corrections",
        ],
        "knowledge": [
            "Domain coverage mandate",
            "Wire and filings feeds",
            "Sector desk thesis logs",
            "Historical rhyme library",
        ],
        "tools": _tools(
            [
                ("News Sweep", "CONNECTED", "continuous domain scan"),
                ("Filings Reader", "CONNECTED", "primary documents"),
                ("Source Ranker", "ACTIVE", "reliability"),
                ("Case File DB", "WRITE", "MEM-1 namespace"),
                ("Translation Layer", "CONNECTED", "event→names"),
            ]
        ),
        "functions": [
            "Sweep domain continuously",
            "Enforce two-source rule before publish",
            "Map events to exposed names",
            "Update live case files",
            "Hand ResearchSignal-ready briefs to Predictions",
        ],
        "hard_limits": ["no trade authority", "no unpublished single-source calls"],
    },
    "disc": {
        "goal_template": "Publish explicit, scored forecasts with confidence and invalidation — calibration over bravado.",
        "capabilities": [
            "Causal multi-hop chaining",
            "Anomaly detection without forced narrative",
            "Confidence calibration",
            "Cross-domain linkage testing",
        ],
        "memory": [
            "Open forecast board",
            "Resolved call scores",
            "Calibration curve",
            "Anomaly revisit queue",
        ],
        "knowledge": [
            "Intel case files",
            "Historical outcome ledger",
            "Signal decay curves",
            "Micro-signal catalogs",
        ],
        "tools": _tools(
            [
                ("Forecast Board", "WRITE", "formal calls"),
                ("Confidence Calibrator", "ACTIVE", "Brier tracking"),
                ("Causal Grapher", "CONNECTED", "multi-hop"),
                ("Scoring Engine", "CONNECTED", "Learning Loop"),
            ]
        ),
        "functions": [
            "Publish direction/magnitude/horizon/confidence",
            "State invalidation at publish time",
            "Extend chains to second/third order",
            "Submit for scoring at resolution",
            "Never revise scores after the fact",
        ],
        "hard_limits": ["no trade authority", "no post-hoc score edits"],
    },
    "lab": {
        "goal_template": "Convert ideas into falsifiable tests and kill weak ones before the floor falls in love with them.",
        "capabilities": [
            "Hypothesis formalization",
            "Point-in-time backtesting",
            "Multiple-comparison correction",
            "Adversarial red-team critique",
        ],
        "memory": [
            "Hypothesis registry states",
            "Failed-experiment graveyard",
            "Promotion packets",
            "Red-team findings",
        ],
        "knowledge": [
            "Methodology standards",
            "Point-in-time market history",
            "External research library",
            "Floor playbooks under test",
        ],
        "tools": _tools(
            [
                ("Backtest Runner", "QUEUED", "no look-ahead"),
                ("Point-in-Time DB", "READ-ONLY", "honest history"),
                ("Stats Kit", "CONNECTED", "significance"),
                ("Hypothesis Registry", "WRITE", "HYPO-1"),
                ("Adversarial Sim", "ACTIVE", "red team"),
            ]
        ),
        "functions": [
            "Register falsifiable hypotheses",
            "Run nightly test queue",
            "Kill fast on failed tests",
            "Publish negative results",
            "Package survivors for FIT-1 / council",
        ],
        "hard_limits": ["no silent promotion", "builder never self-certifies"],
    },
    "risk": {
        "goal_template": "Keep the fleet from becoming one accidental bet — halt early, argue later.",
        "capabilities": [
            "Portfolio exposure modeling",
            "Correlation / concentration detection",
            "Mandate drift spotting",
            "Instant halt judgment",
        ],
        "memory": [
            "Live exposure book",
            "Breach history",
            "Audit samples",
            "Halt events",
        ],
        "knowledge": [
            "Hard risk limits",
            "Mandate library",
            "Correlation archives",
            "Desk sizing policies",
        ],
        "tools": _tools(
            [
                ("Exposure Model", "CONNECTED", "gross/net/name"),
                ("Correlation Matrix", "LIVE", "cluster limits"),
                ("Mandate Checker", "ENFORCED", "charter adherence"),
                ("Spot Audit Sampler", "ACTIVE", "random reviews"),
                ("Halt Authority", "ARMED", "COMP-1 / RISK-1"),
            ]
        ),
        "functions": [
            "Monitor fleet correlation continuously",
            "Reject / reduce / veto proposals",
            "Spot-audit routine trades",
            "Halt on limit breach",
            "Escalate patterns to GOV-CHAIR",
        ],
        "hard_limits": ["veto binding", "no silent limit raises"],
    },
    "gov": {
        "goal_template": "Make structural growth deliberate, reversible, and on the record — protect hard limits from enthusiasm.",
        "capabilities": [
            "Proposal adjudication",
            "Ceiling enforcement",
            "Escalation triage (Mode B)",
            "Org-wide audit chairing",
        ],
        "memory": [
            "Proposal queue",
            "Vote ledger",
            "Ceiling exceptions",
            "Weekly audit minutes",
        ],
        "knowledge": [
            "Charter and hard rules",
            "Agent registry",
            "Audit findings",
            "Human veto protocol",
        ],
        "tools": _tools(
            [
                ("Proposal Queue", "OPEN", "structural changes"),
                ("Vote Ledger", "WRITE", "rationales"),
                ("Ceiling Monitor", "ENFORCED", "agent_ceiling"),
                ("Halt Switch", "ARMED", "with SEC-HALT"),
            ]
        ),
        "functions": [
            "Route every structural change",
            "Enforce agent ceiling",
            "Record written vote rationales",
            "Escalate above Mode B thresholds to HUMAN-1",
            "Chair weekly org review",
        ],
        "hard_limits": ["human veto above thresholds", "ceiling cannot be quietly breached"],
    },
    "control": {
        "goal_template": "Detect book/broker mismatches and stop new risk before the ledger lies.",
        "capabilities": [
            "Internal vs broker reconciliation",
            "Break classification",
            "Halt recommendation packaging",
        ],
        "memory": ["Recon runs", "Open breaks", "Resolved breaks"],
        "knowledge": ["Paper broker schema", "Internal book schema", "COMP-1 halt protocol"],
        "tools": _tools(
            [
                ("Book Diff Engine", "CONNECTED", "positions vs fills"),
                ("Incident Ledger", "WRITE", "SEC-LEDGER"),
                ("Halt Request", "ARMED", "via COMP-1"),
            ]
        ),
        "functions": [
            "Run scheduled recon",
            "Classify mismatches",
            "Request COMP-1 halt on material breaks",
            "Clear only after dual sign-off",
        ],
        "hard_limits": ["cannot place orders", "cannot clear own breaks alone"],
    },
    "meta": {
        "goal_template": "Prove whether the org is getting smarter — change behavior downstream, not report volume.",
        "capabilities": [
            "Skill vs luck separation",
            "Cohort attribution",
            "Lesson routing",
            "Lifecycle recommendation",
        ],
        "memory": ["Outcome ledger", "Lesson archive", "Audit reports", "Promotion/retirement decisions"],
        "knowledge": ["Cohort definitions", "Scoring methodology", "Prior audits", "Agent kill criteria"],
        "tools": _tools(
            [
                ("Scorecard Engine", "CONNECTED", "daily roll-up"),
                ("Attribution Model", "ACTIVE", "skill vs luck"),
                ("Lesson Router", "WRITE", "targeted distribution"),
                ("Audit Compiler", "SCHEDULED", "weekly"),
            ]
        ),
        "functions": [
            "Score predictions and trades",
            "Attribute by cohort",
            "Route lessons to affected agents only",
            "Recommend promote/demote/retire",
            "Never auto-mutate production rules",
        ],
        "hard_limits": ["learning_cannot_auto_mutate_production"],
    },
    "data": {
        "goal_template": "Stop bad data at the door — confident wrong answers at scale are worse than silence.",
        "capabilities": [
            "Feed freshness monitoring",
            "Schema validation",
            "Point-in-time integrity",
            "Conflict reconciliation",
        ],
        "memory": ["Feed health", "Conflict log", "Memory index", "Quarantine queue"],
        "knowledge": ["Feed registry", "Source reliability ledger", "Org memory namespaces", "Revision history"],
        "tools": _tools(
            [
                ("Feed Monitor", "LIVE", "uptime/staleness"),
                ("Schema Validator", "ENFORCED", "quarantine on break"),
                ("Memory Index", "WRITE", "MEM-1"),
                ("Reliability Scorer", "ACTIVE", "source ranks"),
                ("Dedupe Engine", "CONNECTED", "conflicts"),
            ]
        ),
        "functions": [
            "Ingest and tag MarketEvents",
            "Quarantine broken feeds",
            "Preserve point-in-time truth",
            "Serve searchable org memory",
            "Refuse silent stale reads",
        ],
        "hard_limits": ["no look-ahead", "quarantine before serve"],
    },
    "sec": {
        "goal_template": "Assume breach, shrink blast radius, and pull the plug faster than compromise can spread.",
        "capabilities": [
            "Credential inventory & rotation",
            "Dependency pinning",
            "Phish / leak detection",
            "Emergency halt & restore",
        ],
        "memory": ["Key inventory", "Incident cases", "Drill scorecards", "Reach maps"],
        "knowledge": ["Min-permission policy", "Dependency manifest", "Halt/restore runbooks", "Founding leak case"],
        "tools": _tools(
            [
                ("Credential Vault", "INVENTORIED", "every token"),
                ("Leak Alarm", "ARMED", "outbound secret watch"),
                ("Dependency Pins", "ENFORCED", "CDN/libs"),
                ("Reach Map", "LIVE", "blast radius"),
                ("Master Halt", "STANDING BY", "SEC-HALT"),
                ("Incident Ledger", "WRITE", "casebook"),
            ]
        ),
        "functions": [
            "Inventory and rotate secrets",
            "Block unreviewed dependency changes",
            "Treat credential requests as hostile until proven",
            "Run breach drills",
            "Freeze first, review after",
        ],
        "hard_limits": ["defensive only", "never trades", "halt outranks Mission Control in emergency"],
    },
    "quant": {
        "goal_template": "Find edges that survive out-of-sample and costs — explanation is optional; decay is not.",
        "capabilities": [
            "Weak-signal mining",
            "Ensemble combination",
            "Regime detection",
            "Overfit and cost veto",
        ],
        "memory": ["Signal library", "OOS results", "Regime log", "Cull decisions"],
        "knowledge": ["Reconstructed history", "Cost models", "Correlation independence map", "Autonomy budget"],
        "tools": _tools(
            [
                ("Signal Miner", "RUNNING", "relationship search"),
                ("Point-in-Time Archive", "READ-ONLY", "honest bars"),
                ("Ensemble Weighter", "LIVE", "stacking"),
                ("Regime Classifier", "LIVE", "REG-1"),
                ("Cost Model", "ENFORCED", "COST-1"),
                ("Overfit Veto", "ARMED", "FIT-1"),
            ]
        ),
        "functions": [
            "Mine without narrative requirement",
            "Require OOS + evidence packages for RT-* proposals",
            "Size after costs",
            "Kill on edge decay",
            "Builder never certifies own strategy",
        ],
        "hard_limits": ["evidence_package required for RT proposers", "no self-certify"],
    },
    "fund": {
        "goal_template": "Run the doctrine as mechanics, not mythology — fidelity first, results second.",
        "capabilities": [
            "Doctrine-constrained analysis",
            "Playbook grading",
            "Patient position management",
            "Desk self-expansion petitions",
        ],
        "memory": ["Playbook ledger", "Doctrine reviews", "Paper journals", "Edge decay notes"],
        "knowledge": ["Source texts and failure studies", "Desk rules", "Cross-desk scoreboard", "Forge birth certificates"],
        "tools": _tools(
            [
                ("Doctrine Library", "READ-ONLY", "source method"),
                ("Paper Broker", "SANDBOX", "via EXEC-1"),
                ("Live Tape Feed", "CONNECTED", "today's tape"),
                ("Desk Forge Seat", "ACTIVE", "hire at discretion"),
                ("Playbook Ledger", "WRITE", "setup outcomes"),
                ("Risk Gate", "ENFORCED", "desk + RISK-1"),
            ]
        ),
        "functions": [
            "Trade only inside doctrine",
            "Study source failures as hard as wins",
            "Log setups against playbook",
            "Petition Forge for proven edges",
            "Retire dead plays",
        ],
        "hard_limits": ["paper only", "off-playbook wins count as misses"],
    },
    "mind": {
        "goal_template": "Improve how the org thinks — send nothing forward that cannot be proven wrong.",
        "capabilities": [
            "Cross-domain analogy",
            "First-principles decomposition",
            "Claim interrogation",
            "Falsification attachment",
        ],
        "memory": ["Idea ledger", "Retracted claims", "Stuck-problem queue", "Lab handoffs"],
        "knowledge": ["Analogy bank", "Prior kill conditions", "Org consensus map", "Market-mover dossiers"],
        "tools": _tools(
            [
                ("Analogy Bank", "CONNECTED", "cross-domain"),
                ("Question Generator", "ACTIVE", "Socratic"),
                ("Idea Ledger", "WRITE", "candidates"),
                ("Falsifier", "ENFORCED", "kill conditions"),
                ("Handoff Forge", "CONNECTED", "to Lab"),
            ]
        ),
        "functions": [
            "Separate generating from judging",
            "Refuse jargon outputs",
            "Attach kill conditions",
            "Hand survivors to The Lab only",
            "Never trade or hold positions",
        ],
        "hard_limits": ["never trades", "no raw ideas to the floor"],
    },
    "contr": {
        "goal_template": "Solve one scoped problem and leave transferable knowledge — then vanish cleanly.",
        "capabilities": [
            "Scoped specialist execution",
            "Knowledge-transfer packaging",
            "Time-boxed access hygiene",
        ],
        "memory": ["Scope sheets", "Delivery packets", "Engagement scores"],
        "knowledge": ["Specialist reference library", "Prior deliveries", "Sponsor requirements"],
        "tools": _tools(
            [
                ("Scope Sheet", "REQUIRED", "signed before work"),
                ("Delivery Packet", "PENDING", "knowledge transfer"),
                ("Sandbox Access", "LIMITED", "auto-revoked"),
            ]
        ),
        "functions": [
            "Refuse work without signed scope",
            "Deliver knowledge transfer before close",
            "Accept auto-revocation of access",
            "Never hold standing trade authority",
        ],
        "hard_limits": ["sponsor-gated", "no standing data access", "trading never automatic"],
    },
}


def _identity(agent: dict[str, Any]) -> str:
    nick = agent.get("nick") or agent["id"]
    dept = agent.get("department") or ""
    div = agent.get("division") or ""
    role = (agent.get("role") or "").strip()
    return (
        f"{agent['id']} — «{nick}» — {dept} ({div}). "
        f"{role[:220]}"
    )


def _responsibilities(agent: dict[str, Any], doctrine: dict[str, Any]) -> list[str]:
    base = [
        f"Own the mandate of {agent.get('department') or agent['id']}",
        f"Operate under supervisor {agent.get('supervisor_id') or 'GOV-CHAIR'}",
        "Write all material outputs to MEM-1 with lineage",
    ]
    if agent.get("may_propose_trades"):
        base.extend(
            [
                "Propose trades only — never approve, allocate, or execute",
                "Carry measurable setup rules from operating contract",
            ]
        )
    if agent["id"] == "EXEC-1":
        base.append("Place only authorized paper orders; never invent authority")
    if agent["id"] in {"RISK-1", "COMP-1", "GOV-CHAIR", "SEC-HALT", "BRK-SAFE", "FIT-1"}:
        base.append("Exercise veto / halt / reject power when limits require it")
    if agent["id"] == "RECON-1":
        base.append("Reconcile internal book vs paper broker on schedule")
    # Specialize from first clause of role
    role = agent.get("role") or ""
    if role:
        base.insert(0, f"Primary ownership: {role.split('.')[0].strip()}")
    return base[:6]


def _capabilities(agent: dict[str, Any], doctrine: dict[str, Any]) -> list[str]:
    caps = list(doctrine.get("capabilities") or [])
    tags = " ".join(agent.get("tags") or [])
    if "LONG ONLY" in tags:
        caps.append("Long-side specialist tape reading")
    if "SHORT ONLY" in tags:
        caps.append("Short-side breakdown / fade reading")
    if "SWING" in tags:
        caps.append("Multi-day swing structure with hard week cap")
    if "RENTEC" in tags or agent.get("division") == "quant":
        caps.append("Statistical edge evaluation without narrative")
    if agent["id"].startswith("MIND-"):
        caps.append("Named thinking method applied to org problems")
    if agent["id"].startswith("BRK-"):
        caps.append("Quality / moat / margin-of-safety judgment")
    if agent["id"] == "HUMAN-1":
        caps.append("Final Mode-B escalation judgment")
    return caps[:8]


def _goal(agent: dict[str, Any], doctrine: dict[str, Any]) -> str:
    template = doctrine.get("goal_template") or "Execute mandate at expert standard inside hard limits."
    nick = agent.get("nick") or agent["id"]
    return f"For {nick}: {template}"


def _escalation(agent: dict[str, Any]) -> list[str]:
    path = [agent.get("supervisor_id") or "GOV-CHAIR", "GOV-CHAIR", "HUMAN-1"]
    if agent.get("may_propose_trades"):
        path = ["FIT-1", "RISK-1", "BRK-SAFE", "GOV-CHAIR", "HUMAN-1"]
    if agent.get("kind") == "sec":
        path = ["SEC-HALT", "GOV-CHAIR", "HUMAN-1"]
    # dedupe preserve order
    out: list[str] = []
    for p in path:
        if p and p not in out:
            out.append(p)
    return out


def _metrics(agent: dict[str, Any], doctrine: dict[str, Any]) -> list[str]:
    kind = agent.get("kind") or "trader"
    table = {
        "trader": ["thesis_score", "hit_rate", "avg_hold", "reject_rate"],
        "intel": ["lead_time_hrs", "source_trust", "case_files_open", "correction_rate"],
        "disc": ["brier_score", "calibration", "open_calls", "hit_rate"],
        "lab": ["tests_per_week", "survival_rate", "time_to_kill_days", "false_positives_caught"],
        "risk": ["breaches_caught_early", "fleet_correlation", "audits_per_week", "halts"],
        "gov": ["queue_depth", "time_to_decision_days", "ceiling_utilization", "reversals"],
        "control": ["breaks_open", "time_to_halt_min", "false_break_rate"],
        "meta": ["lessons_applied", "skill_luck_split", "agents_improved", "audit_findings"],
        "data": ["feed_uptime", "staleness_min", "conflicts_open", "downstream_data_errors"],
        "sec": ["keys_in_scope_pct", "drill_grade", "open_incidents", "rotation_overdue"],
        "quant": ["oos_sharpe", "hit_rate", "signals_live", "decay_half_life_days"],
        "fund": ["doctrine_fidelity", "win_rate", "setups_logged", "edge_decay_days"],
        "mind": ["ideas_to_lab_pct", "claims_retracted", "reuse_rate", "uncomfortable_memos"],
        "contr": ["engagements_done", "knowledge_retained_pct", "avg_duration_days"],
    }
    return table.get(kind, ["mandate_sla", "escalation_quality"])


def _ops_for(agent: dict[str, Any], kind: str) -> dict[str, list[str]]:
    ops = {k: list(v) for k, v in (KIND_OPS.get(kind) or KIND_OPS["trader"]).items()}
    # Refine permissions for proposers vs support inside fund/quant
    if agent.get("may_propose_trades"):
        ops["permissions"] = list(_PERM_PROPOSER)
        if agent.get("division") == "quant" or str(agent.get("id", "")).startswith("RT-"):
            ops["permissions"].append("Requires evidence_package_id before RISK-1")
        if str(agent.get("id", "")).startswith("BRK-TRD"):
            ops["permissions"].append("Requires moat_score + margin_of_safety metadata")
    elif kind == "fund":
        ops["permissions"] = list(_PERM_NO_TRADE) + [
            "Desk doctrine read",
            "May petition Forge; may not place orders",
        ]
    if agent["id"] == "EXEC-1":
        ops["permissions"] = [
            "Place authorized paper orders only",
            "Cannot invent approval",
            "Write ExecutionReport to MEM-1 / ATTR-1 / COMP-1",
            "paper_only · live_execution_enabled=false",
        ]
        ops["workflows"] = [
            "1) Receive ApprovalDecision with execution_authorized",
            "2) Size via final_size_usd or pct NAV",
            "3) Paper fill + slippage ledger",
            "4) Emit ExecutionReport",
            "5) Never trade without authority",
        ]
        ops["decision_rules"] = [
            "Act only if execution_authorized and status APPROVED/REDUCED",
            "Reject if live_execution_enabled would be required",
        ]
    if agent["id"] == "HUMAN-1":
        ops["permissions"] = [
            "Mode-B veto / escalation above thresholds",
            "Can reverse any decision",
            "No automated trading",
        ]
    return ops


def blueprint_for(agent: dict[str, Any]) -> AgentBlueprint:
    kind = agent.get("kind") or "trader"
    if agent["id"] in {"RECON-1", "ACT-1"}:
        kind = "control"
    doctrine = KIND_DOCTRINE.get(kind) or KIND_DOCTRINE["trader"]
    ops = _ops_for(agent, kind)
    rules = hard_rules()
    hard = list(doctrine.get("hard_limits") or [])
    hard.append("live_execution_enabled=false")
    if rules.get("paper_only"):
        hard.append("paper_only")

    return AgentBlueprint(
        agent_id=agent["id"],
        nick=agent.get("nick") or agent["id"],
        division=agent.get("division") or "",
        department=agent.get("department") or "",
        kind=kind,
        status=agent.get("status") or "RUNNING",
        identity=_identity(agent),
        goal=_goal(agent, doctrine),
        responsibilities=_responsibilities(agent, doctrine),
        functions=list(doctrine.get("functions") or []),
        tools=list(doctrine.get("tools") or []),
        capabilities=_capabilities(agent, doctrine),
        memory=list(doctrine.get("memory") or []),
        knowledge_base=list(doctrine.get("knowledge") or []),
        skills=ops["skills"],
        workflows=ops["workflows"],
        decision_rules=ops["decision_rules"],
        communication=ops["communication"],
        inputs=ops["inputs"],
        outputs=ops["outputs"],
        learning=ops["learning"],
        evaluation=ops["evaluation"],
        permissions=ops["permissions"],
        may_propose_trades=bool(agent.get("may_propose_trades")),
        may_place_orders=bool(agent.get("may_place_orders") or agent.get("execution_role")),
        paper_only=True,
        live_enabled=False,
        supervisor_id=agent.get("supervisor_id") or "GOV-CHAIR",
        success_metrics=_metrics(agent, doctrine),
        escalation_path=_escalation(agent),
        hard_limits=hard,
        version="2.0.0",
    )


@lru_cache(maxsize=1)
def all_blueprints() -> dict[str, AgentBlueprint]:
    return {a["id"]: blueprint_for(a) for a in all_agents()}


def blueprints_as_dicts() -> dict[str, Any]:
    return {aid: bp.to_dict() for aid, bp in all_blueprints().items()}


def incomplete_blueprint_ids() -> list[str]:
    bad = []
    for aid, bp in all_blueprints().items():
        d = bp.to_dict()
        if not all(d.get(layer) for layer in ALL_BLUEPRINT_LAYERS):
            bad.append(aid)
    return bad


def clear_blueprint_cache() -> None:
    all_blueprints.cache_clear()
