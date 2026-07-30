"""Expert-level 8-layer blueprints for every Watchfloor agent.

Generates Identity / Goal / Responsibilities / Functions / Tools /
Capabilities / Memory / Knowledge Base from registry metadata + kind doctrine.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from agent_fleet.registry.watchfloor import all_agents, hard_rules
from agent_fleet.schemas.blueprint import AgentBlueprint, ToolAccess


def _tools(items: list[tuple[str, str, str]]) -> list[ToolAccess]:
    return [ToolAccess(name=n, access=a, purpose=p) for n, a, p in items]


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


def blueprint_for(agent: dict[str, Any]) -> AgentBlueprint:
    kind = agent.get("kind") or "trader"
    if agent["id"] == "RECON-1":
        kind = "control"
    doctrine = KIND_DOCTRINE.get(kind) or KIND_DOCTRINE["trader"]
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
        may_propose_trades=bool(agent.get("may_propose_trades")),
        may_place_orders=bool(agent.get("may_place_orders") or agent.get("execution_role")),
        paper_only=True,
        live_enabled=False,
        supervisor_id=agent.get("supervisor_id") or "GOV-CHAIR",
        success_metrics=_metrics(agent, doctrine),
        escalation_path=_escalation(agent),
        hard_limits=hard,
        version="1.0.0",
    )


@lru_cache(maxsize=1)
def all_blueprints() -> dict[str, AgentBlueprint]:
    return {a["id"]: blueprint_for(a) for a in all_agents()}


def blueprints_as_dicts() -> dict[str, Any]:
    return {aid: bp.to_dict() for aid, bp in all_blueprints().items()}


def incomplete_blueprint_ids() -> list[str]:
    bad = []
    for aid, bp in all_blueprints().items():
        if not all(
            [
                bp.identity,
                bp.goal,
                bp.responsibilities,
                bp.functions,
                bp.tools,
                bp.capabilities,
                bp.memory,
                bp.knowledge_base,
            ]
        ):
            bad.append(aid)
    return bad


def clear_blueprint_cache() -> None:
    all_blueprints.cache_clear()
