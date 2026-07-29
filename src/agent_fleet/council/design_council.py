"""Institutional Design Council — executable enhance fleet.

Nine specialty teams + chief architecture audit the Watchfloor setup,
critique each other, apply vetoes, and emit a concrete enhancement plan.
No theatrical role-play: every finding is a missing capability, weakness,
unsafe permission, duplicate, or implementation task.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from agent_fleet.registry.watchfloor import (
    institutional_council_map,
    load_watchfloor_registry,
)


class Priority(str, Enum):
    P0 = "P0"  # safety / correctness — do before paper hardening
    P1 = "P1"  # required for reliable paper org
    P2 = "P2"  # research / data depth
    P3 = "P3"  # live readiness (gated)


class FindingKind(str, Enum):
    MISSING = "missing_capability"
    WEAKNESS = "structural_weakness"
    DUPLICATE = "duplicated_role"
    UNSAFE = "unsafe_permission"
    IMPROVEMENT = "recommended_improvement"
    DISSENT = "dissent"
    VETO = "veto"
    DECISION = "architecture_decision"
    TASK = "implementation_task"


@dataclass
class Finding:
    team_id: str
    team_name: str
    kind: FindingKind
    title: str
    detail: str
    evidence: list[str] = field(default_factory=list)
    watchfloor_ids: list[str] = field(default_factory=list)
    priority: Priority = Priority.P1
    vetoable: bool = False
    vetoed: bool = False
    veto_reason: str = ""
    implementation_task: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["priority"] = self.priority.value
        return d


@dataclass
class CouncilTeam:
    team_id: str
    name: str
    inspired_by: str
    responsibility: str
    watchfloor_seats: list[str]
    has_veto: bool = False
    audit_fn: Callable[[dict[str, Any]], list[Finding]] | None = None

    def audit(self, registry: dict[str, Any]) -> list[Finding]:
        if self.audit_fn is None:
            return []
        return self.audit_fn(registry)


def _proposers_without_setup_rules(registry: dict[str, Any]) -> list[str]:
    """Prefer generated contract store; fall back to registry field inspection."""
    try:
        from agent_fleet.agents.watchfloor_contracts import incomplete_proposer_ids

        return incomplete_proposer_ids()
    except Exception:
        missing = []
        for agent in registry["agents"]:
            if not agent.get("may_propose_trades"):
                continue
            if not agent.get("setup_detection_rules") and not agent.get("entry_exit"):
                missing.append(agent["id"])
        return missing


def audit_systems_intelligence(registry: dict[str, Any]) -> list[Finding]:
    agents = registry["agents"]
    ids = {a["id"] for a in agents}
    findings = [
        Finding(
            team_id="IDC-PALANTIR",
            team_name="Systems Intelligence",
            kind=FindingKind.IMPROVEMENT,
            title="Durable EventStore path exists; UI still lacks MEM-1 audit export",
            detail=(
                "Paper org now writes lineage to data/audit/events.jsonl by default. "
                "Remaining gap: Watchfloor UI does not surface or export that graph."
            ),
            evidence=["WatchfloorOrganization EventStore path", "ui/watchfloor.html"],
            watchfloor_ids=["MEM-1", "DQ-1", "UI-1", "TOOL-1"],
            priority=Priority.P2,
            implementation_task=(
                "Add MEM-1 audit export endpoint/bridge so the UI can read "
                "data/audit/events.jsonl lineage for each proposal_id."
            ),
        ),
        Finding(
            team_id="IDC-PALANTIR",
            team_name="Systems Intelligence",
            kind=FindingKind.WEAKNESS,
            title="Permissions exist in registry flags but are not enforced in the UI",
            detail=(
                "UI create-agent flow can invent custom agents without going through "
                "GOV-CHAIR proposal queue or ceiling checks in code."
            ),
            evidence=["ui/watchfloor.html CUSTOM.agents push path"],
            watchfloor_ids=["GOV-CHAIR", "HUMAN-1", "UI-1"],
            priority=Priority.P1,
            implementation_task=(
                "Gate UI agent creation behind council proposal objects validated "
                "against agent_ceiling and COMP-1 mandate checks."
            ),
        ),
    ]
    required = ["MEM-1", "DQ-1", "MKT-1", "EXEC-1", "RISK-1", "GOV-CHAIR", "SEC-HALT"]
    missing_seats = [r for r in required if r not in ids]
    if missing_seats:
        findings.append(
            Finding(
                team_id="IDC-PALANTIR",
                team_name="Systems Intelligence",
                kind=FindingKind.MISSING,
                title="Critical control seats absent from registry",
                detail=f"Missing: {missing_seats}",
                evidence=missing_seats,
                watchfloor_ids=missing_seats,
                priority=Priority.P0,
                vetoable=True,
                implementation_task="Restore missing control seats before any paper expansion.",
            )
        )
    return findings


def audit_market_information(registry: dict[str, Any]) -> list[Finding]:
    return [
        Finding(
            team_id="IDC-BLOOMBERG",
            team_name="Market Information",
            kind=FindingKind.MISSING,
            title="No real market/news/filings adapters behind MKT-1/ALT-1",
            detail=(
                "Paper path uses synthetic verified bars. Intel desks (GEO/MACRO/…) "
                "have mandates but no normalized MarketEvent feed contract wired in."
            ),
            evidence=["WatchfloorOrganization.ingest_market_event uses paper_feed"],
            watchfloor_ids=["MKT-1", "ALT-1", "DQ-1", "GEO-1", "MACRO-1"],
            priority=Priority.P2,
            implementation_task=(
                "Implement MarketEvent adapters (bars, calendar, filings, news) with "
                "source_verified + tagging, delivering slices to intel/pred consumers."
            ),
        ),
        Finding(
            team_id="IDC-BLOOMBERG",
            team_name="Market Information",
            kind=FindingKind.IMPROVEMENT,
            title="Dual-source confirmation for macro prints not encoded",
            detail="MACRO-1 / POLICY-1 should require two-source confirm before FORE-1 publishes high-confidence calls.",
            evidence=["hard_rules lack dual_source_macro"],
            watchfloor_ids=["MACRO-1", "FORE-1", "DQ-1"],
            priority=Priority.P2,
            implementation_task="Add dual_source_required flag for macro event types in DQ-1.",
        ),
    ]


def audit_ai_infrastructure(registry: dict[str, Any]) -> list[Finding]:
    return [
        Finding(
            team_id="IDC-NVIDIA",
            team_name="AI Infrastructure",
            kind=FindingKind.MISSING,
            title="ML-ARCH autonomy budget not instrumented",
            detail=(
                "Pattern Recognition ML claims self-building below compute ceiling, "
                "but there is no compute meter, model registry, or failover SLA."
            ),
            evidence=["ML-ARCH seat exists", "no compute budget in hard_rules"],
            watchfloor_ids=["ML-ARCH", "ML-VIT", "ML-SEQ", "TOOL-1"],
            priority=Priority.P2,
            implementation_task=(
                "Add hard_rules.compute_ceiling and a model-routing health endpoint; "
                "ML-ARCH proposals above ceiling require GOV-CHAIR."
            ),
        ),
        Finding(
            team_id="IDC-NVIDIA",
            team_name="AI Infrastructure",
            kind=FindingKind.IMPROVEMENT,
            title="Separate local paper inference from optional cloud workloads",
            detail="Phase-1 paper org should stay local/deterministic; cloud only for experimental ML cells.",
            evidence=["LIVE_EXECUTION_ENABLED false", "Environment buckets exist"],
            watchfloor_ids=["ML-ARCH", "RT-FORGE-1"],
            priority=Priority.P1,
            implementation_task="Document and enforce Environment.EXPERIMENTAL for ML self-builds.",
        ),
    ]


def audit_portfolio_risk(registry: dict[str, Any]) -> list[Finding]:
    rules = registry["hard_rules"]
    findings = [
        Finding(
            team_id="IDC-BLACKROCK",
            team_name="Portfolio and Risk",
            kind=FindingKind.IMPROVEMENT,
            title="Fixed-dollar cohort sizing wired; fund/quant sleeves still %NAV",
            detail=(
                "PaperBroker + RISK-1 honor suggested_size_usd for fixed_1_2_usd cohorts. "
                "Continue separating paper experiment capital from stewardship sleeve capital."
            ),
            evidence=[f"default_sizing_usd={rules.get('default_sizing_usd')}"],
            watchfloor_ids=["CAP-1", "RISK-1", "EXEC-1"],
            priority=Priority.P2,
            implementation_task=(
                "Expose paper_experiment_capital_usd vs stewardship_sleeve_capital_usd "
                "in portfolio state exports for BRK-SAFE."
            ),
        ),
        Finding(
            team_id="IDC-BLACKROCK",
            team_name="Portfolio and Risk",
            kind=FindingKind.IMPROVEMENT,
            title="Same-symbol cluster check exists; full correlation matrix still missing",
            detail=(
                "RISK-1 rejects when same-symbol cluster exceeds max_correlated_cluster_pct. "
                "Cross-name rolling correlation matrix remains a P2 gap."
            ),
            evidence=["WatchfloorOrganization.portfolio_risk cluster check"],
            watchfloor_ids=["RISK-1", "CORR-Q", "CAP-1"],
            priority=Priority.P2,
            implementation_task="Add rolling cross-name correlation matrix feeding CORR-Q.",
        ),
    ]
    bad = [a["id"] for a in registry["agents"] if a.get("may_propose_trades") and a.get("may_place_orders")]
    if bad:
        findings.append(
            Finding(
                team_id="IDC-BLACKROCK",
                team_name="Portfolio and Risk",
                kind=FindingKind.UNSAFE,
                title="Proposers with execution permission",
                detail=f"Illegal dual role: {bad}",
                evidence=bad,
                watchfloor_ids=bad,
                priority=Priority.P0,
                vetoable=True,
                implementation_task="Strip may_place_orders from all proposers; keep EXEC-1 only.",
            )
        )
    return findings


def audit_trading_operations(registry: dict[str, Any]) -> list[Finding]:
    trade = [a for a in registry["agents"] if a["division"] == "trade"]
    return [
        Finding(
            team_id="IDC-CITADEL",
            team_name="Trading Operations",
            kind=FindingKind.IMPROVEMENT,
            title="REG-1 regime service admits proposals; richer regime engine still needed",
            detail=(
                "RegimeService gates FIT-1 admission against contract valid/invalid regimes. "
                "Next: data-driven regime labels owned by HEAD-TRADE / REG-1."
            ),
            evidence=["agent_fleet.core.regime.RegimeService"],
            watchfloor_ids=["HEAD-TRADE", "REG-1", "EXEC-1"],
            priority=Priority.P2,
            implementation_task="Replace static regime labels with tape/vol feature classifier.",
        ),
        Finding(
            team_id="IDC-CITADEL",
            team_name="Trading Operations",
            kind=FindingKind.IMPROVEMENT,
            title="Per-symbol daily order cap live; slippage ledger still thin",
            detail=f"{len(trade)} trading-division agents share a per-symbol daily cap of 20.",
            evidence=[f"trade_division_count={len(trade)}", "orders_today_by_symbol"],
            watchfloor_ids=["EXEC-1", "CAP-1", "HEAD-TRADE"],
            priority=Priority.P2,
            implementation_task="Persist EXEC-1 slippage scorecards per fill for ATTR-1.",
        ),
        Finding(
            team_id="IDC-CITADEL",
            team_name="Trading Operations",
            kind=FindingKind.WEAKNESS,
            title="EXEC-1 is both quality analyst and sole order placer",
            detail=(
                "Watchfloor nick 'Fill Check' mixes measurement with authority. "
                "Keep execution authority, but split attribution of fill quality to ATTR-1."
            ),
            evidence=["EXEC-1 tags SUPPORT/EXECUTION"],
            watchfloor_ids=["EXEC-1", "ATTR-1"],
            priority=Priority.P2,
            implementation_task="Clarify EXEC-1 contract: place authorized paper orders; ATTR-1 owns slippage scorecards.",
        ),
    ]


def audit_quant_research(registry: dict[str, Any]) -> list[Finding]:
    missing_rules = _proposers_without_setup_rules(registry)
    findings: list[Finding] = []
    if missing_rules:
        findings.append(
            Finding(
                team_id="IDC-RENTECH",
                team_name="Quantitative Research",
                kind=FindingKind.MISSING,
                title="Proposers lack measurable setup-detection rules in registry",
                detail=(
                    f"{len(missing_rules)} proposers still lack complete operating contracts."
                ),
                evidence=missing_rules[:12]
                + ([f"…+{len(missing_rules)-12}"] if len(missing_rules) > 12 else []),
                watchfloor_ids=["FIT-1", "STAT-1", "HYPO-1", "BACK-1"],
                priority=Priority.P0,
                implementation_task=(
                    "Generate AgentOperatingContract stubs for every proposer with "
                    "setup_detection_rules, entry/exit/stop, and invalidation fields; "
                    "block paper proposal if contract incomplete."
                ),
            )
        )
    else:
        findings.append(
            Finding(
                team_id="IDC-RENTECH",
                team_name="Quantitative Research",
                kind=FindingKind.IMPROVEMENT,
                title="Proposer contract stubs complete; promote from stub to validated",
                detail=(
                    "All proposers have measurable setup/entry/exit stubs and FIT-1 "
                    "blocks incomplete contracts. Next: empirically validate expressions."
                ),
                evidence=["agent_fleet.agents.watchfloor_contracts"],
                watchfloor_ids=["FIT-1", "STAT-1", "HYPO-1", "BACK-1"],
                priority=Priority.P2,
                implementation_task=(
                    "Run BACK-1/STAT-1 validation packs per contract; mark "
                    "contract_completeness=validated_v1 when OOS gates pass."
                ),
            )
        )
    findings.extend(
        [
            Finding(
                team_id="IDC-RENTECH",
                team_name="Quantitative Research",
                kind=FindingKind.MISSING,
                title="No walk-forward / OOS harness wired to HYPO-1 and BACK-1",
                detail="Lab seats exist; controlled improvement sequence is documented but not automated.",
                evidence=["ImprovementProposal required_tests exist", "no backtest runner module"],
                watchfloor_ids=["HYPO-1", "BACK-1", "STAT-1", "FIT-1", "COST-1"],
                priority=Priority.P2,
                implementation_task="Build hypothesis registry + point-in-time backtest queue with FIT-1/COST-1 veto.",
            ),
            Finding(
                team_id="IDC-RENTECH",
                team_name="Quantitative Research",
                kind=FindingKind.IMPROVEMENT,
                title="Quant evidence_package_id gate is live; packages still synthetic in paper",
                detail="FIT-1 requires evidence_package_id on RT/quant proposals before RISK-1.",
                evidence=["validate_proposal evidence_package_present"],
                watchfloor_ids=["FIT-1", "COST-1", "ENS-1"],
                priority=Priority.P2,
                implementation_task="Replace paper stub packages with FIT-1/COST-1 signed evidence objects.",
            ),
        ]
    )
    return findings


def audit_research_strategy(registry: dict[str, Any]) -> list[Finding]:
    return [
        Finding(
            team_id="IDC-GOLDMAN",
            team_name="Research and Strategy",
            kind=FindingKind.MISSING,
            title="ResearchSignal not produced by intel/pred desks in Watchfloor runtime",
            detail=(
                "CORP-1/BULL-1/BEAR-1/FORE-1 exist, but paper path synthesizes a single "
                "CORP-1 signal. Standardized research→signal handoff is incomplete."
            ),
            evidence=["FundamentalResearchAgent is legacy", "WatchfloorOrganization hardcodes CORP-1"],
            watchfloor_ids=["CORP-1", "BULL-1", "BEAR-1", "FORE-1", "HEAD-INTEL"],
            priority=Priority.P1,
            implementation_task=(
                "Route intel/pred outputs through ResearchSignal schema; strategies "
                "may only consume ResearchSignal IDs, never raw narrative blobs."
            ),
        ),
        Finding(
            team_id="IDC-GOLDMAN",
            team_name="Research and Strategy",
            kind=FindingKind.IMPROVEMENT,
            title="Bull/Bear split authors need conflict metadata on case files",
            detail="BULL-1 and BEAR-1 must never share authorship on the same case version.",
            evidence=["Bull/Bear Desk design in Watchfloor"],
            watchfloor_ids=["BULL-1", "BEAR-1", "MEM-1"],
            priority=Priority.P2,
            implementation_task="Enforce separate author_id on case file versions in org memory.",
        ),
    ]


def audit_governance(registry: dict[str, Any]) -> list[Finding]:
    counts = registry["counts"]
    ceiling = registry["hard_rules"].get("agent_ceiling", 150)
    ids = {a["id"] for a in registry["agents"]}
    findings: list[Finding] = []
    if counts["total_agents"] > ceiling:
        findings.append(
            Finding(
                team_id="IDC-JPM",
                team_name="Governance and Operations",
                kind=FindingKind.WEAKNESS,
                title="Agent ceiling exceeded by roster design",
                detail=(
                    f"Registry has {counts['total_agents']} agents vs ceiling {ceiling}. "
                    "Either raise ceiling via council vote or prune/retire cohorts."
                ),
                evidence=[f"total_agents={counts['total_agents']}", f"ceiling={ceiling}"],
                watchfloor_ids=["GOV-CHAIR", "HUMAN-1", "LIFE-1"],
                priority=Priority.P0,
                vetoable=True,
                implementation_task=(
                    "Open GOV-CHAIR proposal: (a) raise ceiling with written rationale, or "
                    "(b) mark excess cohorts ON-DEMAND/RETIRED until under ceiling."
                ),
            )
        )
    else:
        findings.append(
            Finding(
                team_id="IDC-JPM",
                team_name="Governance and Operations",
                kind=FindingKind.IMPROVEMENT,
                title="Agent ceiling decision in force; enforce in UI create flow",
                detail=(
                    f"Roster {counts['total_agents']} ≤ ceiling {ceiling} "
                    "(GOV-CEIL-2026-07-28). UI still needs hard gate."
                ),
                evidence=["docs/council/decisions/GOV-CEIL-2026-07-28.md"],
                watchfloor_ids=["GOV-CHAIR", "HUMAN-1", "LIFE-1", "UI-1"],
                priority=Priority.P1,
                implementation_task="Wire UI agent creation to agent_ceiling + GOV-CHAIR proposal queue.",
            )
        )
    if "RECON-1" not in ids:
        findings.append(
            Finding(
                team_id="IDC-JPM",
                team_name="Governance and Operations",
                kind=FindingKind.MISSING,
                title="No reconciliation agent between internal book and paper broker",
                detail="RECON seat planned but absent; breaks cannot halt new risk today.",
                evidence=["docs/07_missing_agents.md RECON-001"],
                watchfloor_ids=["COMP-1", "EXEC-1", "SEC-LEDGER"],
                priority=Priority.P1,
                implementation_task="Add RECON-1 agent; mismatch → COMP-1 halt on new proposals.",
            )
        )
    else:
        findings.append(
            Finding(
                team_id="IDC-JPM",
                team_name="Governance and Operations",
                kind=FindingKind.IMPROVEMENT,
                title="RECON-1 seat added; automate book vs broker mismatch halt",
                detail="Seat exists under COMP-1; runtime recon loop still to implement.",
                evidence=["RECON-1 in registry"],
                watchfloor_ids=["RECON-1", "COMP-1", "EXEC-1", "SEC-LEDGER"],
                priority=Priority.P2,
                implementation_task="Implement RECON-1 daily check; mismatch → COMP-1 halt.",
            )
        )
    findings.append(
        Finding(
            team_id="IDC-JPM",
            team_name="Governance and Operations",
            kind=FindingKind.IMPROVEMENT,
            title="Incident runbooks for SEC-HALT drills not versioned in repo",
            detail="Kill switch exists in code; drill scorecards and restore checklist need artifacts.",
            evidence=["SEC-HALT", "SEC-DRILL", "SEC-RESTORE seats"],
            watchfloor_ids=["SEC-HALT", "SEC-DRILL", "SEC-RESTORE", "SEC-LEDGER"],
            priority=Priority.P2,
            implementation_task="Add docs/runbooks/halt_drill.md and automate SEC-DRILL quarterly checklist.",
        )
    )
    return findings


def audit_capital_stewardship(registry: dict[str, Any]) -> list[Finding]:
    return [
        Finding(
            team_id="IDC-BERKSHIRE",
            team_name="Capital Stewardship",
            kind=FindingKind.WEAKNESS,
            title="Activity incentives still favor many small discretionary experiments",
            detail=(
                "100-trader floor + novel fleet can create trading-for-learning without "
                "quality filter. Stewardship veto exists for low edge but not for "
                "unnecessary concurrent identical setups."
            ),
            evidence=["Group A/B/C/E design", "BRK-SAFE veto on low edge only"],
            watchfloor_ids=["BRK-SAFE", "BRK-INV", "CAP-1", "HEAD-TRADE"],
            priority=Priority.P1,
            implementation_task=(
                "Add activity budget: max new discretionary proposals/day/cohort; "
                "BRK-INV reviews duplicates of the same thesis family."
            ),
        ),
        Finding(
            team_id="IDC-BERKSHIRE",
            team_name="Capital Stewardship",
            kind=FindingKind.IMPROVEMENT,
            title="Berkshire desk moat/MOS gate is live; scorecards still manual",
            detail="BRK-TRD* proposals require moat_score and margin_of_safety metadata before RISK-1.",
            evidence=["WatchfloorOrganization.stewardship BRK-TRD gate"],
            watchfloor_ids=["BRK-MOAT", "BRK-SAFE", "BRK-TRD1", "BRK-TRD2"],
            priority=Priority.P2,
            implementation_task="Have BRK-MOAT/BRK-SAFE publish signed score objects instead of free-form metadata.",
        ),
        Finding(
            team_id="IDC-BERKSHIRE",
            team_name="Capital Stewardship",
            kind=FindingKind.DISSENT,
            title="Dissent: retiring mean-reversion scouts entirely is too aggressive for a lab",
            detail=(
                "Keep SCOUT/MR-style cohorts in paper with stewardship veto and "
                "fixed $1–2 sizing; do not delete the experiment."
            ),
            evidence=["prior council dissent log"],
            watchfloor_ids=["SCOUT-L2", "SCOUT-S2", "BRK-SAFE"],
            priority=Priority.P2,
            implementation_task="Retain MR/scout cohorts; tag as experimental with elevated reject sensitivity.",
        ),
    ]


def build_council() -> list[CouncilTeam]:
    cmap = institutional_council_map()
    return [
        CouncilTeam(
            team_id="IDC-PALANTIR",
            name="Systems Intelligence",
            inspired_by="Palantir",
            responsibility="Decision system map, lineage, permissions, audit",
            watchfloor_seats=cmap["Palantir Systems Intelligence"],
            audit_fn=audit_systems_intelligence,
        ),
        CouncilTeam(
            team_id="IDC-BLOOMBERG",
            name="Market Information",
            inspired_by="Bloomberg",
            responsibility="Feeds, news, filings, calendars, verification, delivery",
            watchfloor_seats=cmap["Bloomberg Market Information"],
            audit_fn=audit_market_information,
        ),
        CouncilTeam(
            team_id="IDC-NVIDIA",
            name="AI Infrastructure",
            inspired_by="NVIDIA",
            responsibility="Model routing, compute, latency, local vs cloud",
            watchfloor_seats=cmap["NVIDIA AI Infrastructure"],
            audit_fn=audit_ai_infrastructure,
        ),
        CouncilTeam(
            team_id="IDC-BLACKROCK",
            name="Portfolio and Risk",
            inspired_by="BlackRock",
            responsibility="Portfolio construction, limits, stress, drawdown",
            watchfloor_seats=cmap["BlackRock Portfolio Risk"],
            has_veto=True,
            audit_fn=audit_portfolio_risk,
        ),
        CouncilTeam(
            team_id="IDC-CITADEL",
            name="Trading Operations",
            inspired_by="Citadel",
            responsibility="Live/paper workflow, OMS, slippage, multi-strategy coord",
            watchfloor_seats=cmap["Citadel Trading Operations"],
            audit_fn=audit_trading_operations,
        ),
        CouncilTeam(
            team_id="IDC-RENTECH",
            name="Quantitative Research",
            inspired_by="Renaissance Technologies",
            responsibility="Hypotheses, features, validation, anti-overfit",
            watchfloor_seats=cmap["Renaissance Quantitative Research"],
            audit_fn=audit_quant_research,
        ),
        CouncilTeam(
            team_id="IDC-GOLDMAN",
            name="Research and Strategy",
            inspired_by="Goldman Sachs",
            responsibility="Fundamental/sector/macro research → standardized signals",
            watchfloor_seats=cmap["Goldman Research Strategy"],
            audit_fn=audit_research_strategy,
        ),
        CouncilTeam(
            team_id="IDC-JPM",
            name="Governance and Operations",
            inspired_by="JPMorgan Chase",
            responsibility="Controls, compliance, reconciliation, escalation",
            watchfloor_seats=cmap["JPMorgan Governance Operations"],
            has_veto=True,
            audit_fn=audit_governance,
        ),
        CouncilTeam(
            team_id="IDC-BERKSHIRE",
            name="Capital Stewardship",
            inspired_by="Berkshire Hathaway",
            responsibility="Long-term quality, valuation discipline, activity veto",
            watchfloor_seats=cmap["Berkshire Capital Stewardship"],
            has_veto=True,
            audit_fn=audit_capital_stewardship,
        ),
    ]


@dataclass
class EnhancementPlan:
    generated_at: str
    organization: str
    registry_version: str
    agent_counts: dict[str, Any]
    findings: list[Finding]
    cross_critiques: list[Finding]
    vetoes: list[Finding]
    decisions: list[Finding]
    tasks_by_priority: dict[str, list[dict[str, Any]]]
    reasoning: str
    dissenting_views: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "organization": self.organization,
            "registry_version": self.registry_version,
            "agent_counts": self.agent_counts,
            "findings": [f.to_dict() for f in self.findings],
            "cross_critiques": [f.to_dict() for f in self.cross_critiques],
            "vetoes": [f.to_dict() for f in self.vetoes],
            "decisions": [f.to_dict() for f in self.decisions],
            "tasks_by_priority": self.tasks_by_priority,
            "reasoning": self.reasoning,
            "dissenting_views": self.dissenting_views,
        }


class InstitutionalDesignCouncil:
    """Collaborative enhance fleet for the Watchfloor organization."""

    def __init__(self) -> None:
        self.teams = build_council()
        self.registry = load_watchfloor_registry()

    def independent_audits(self) -> list[Finding]:
        findings: list[Finding] = []
        for team in self.teams:
            findings.extend(team.audit(self.registry))
        return findings

    def cross_critique(self, findings: list[Finding]) -> list[Finding]:
        critiques: list[Finding] = []
        # Risk critiques Trading Ops if they push live microstructure too early
        if any(f.team_id == "IDC-CITADEL" and f.priority == Priority.P1 for f in findings):
            critiques.append(
                Finding(
                    team_id="IDC-BLACKROCK",
                    team_name="Portfolio and Risk",
                    kind=FindingKind.DISSENT,
                    title="Critique: Trading Ops must not unlock live microstructure before correlation controls",
                    detail="Slippage ledgers are fine in paper; live hooks stay gated at Phase 5.",
                    evidence=["Citadel P1 trading findings"],
                    watchfloor_ids=["RISK-1", "EXEC-1"],
                    priority=Priority.P0,
                    implementation_task="Keep live_execution_enabled=false until correlation + halt drills pass.",
                )
            )
        # Quant critiques Fundamental on signal format wars — already resolved, reinforce
        critiques.append(
            Finding(
                team_id="IDC-RENTECH",
                team_name="Quantitative Research",
                kind=FindingKind.DECISION,
                title="Critique resolution: single ResearchSignal schema remains mandatory",
                detail="Intel and quant may both publish, but payload must be ResearchSignal.",
                evidence=["prior unified_design.md"],
                watchfloor_ids=["FORE-1", "MINE-1", "CORP-1"],
                priority=Priority.P1,
                implementation_task="Reject non-ResearchSignal handoffs in message bus permissions.",
            )
        )
        # Stewardship critiques activity without deleting lab cohorts
        critiques.append(
            Finding(
                team_id="IDC-BERKSHIRE",
                team_name="Capital Stewardship",
                kind=FindingKind.DISSENT,
                title="Critique: do not confuse lab breadth with production capital allocation",
                detail="Paper cohorts may be wide; binding capital stays tiny and comparable.",
                evidence=["default_sizing_usd", "paper_only"],
                watchfloor_ids=["CAP-1", "BRK-SAFE"],
                priority=Priority.P1,
                implementation_task="Separate paper experiment capital from stewardship sleeve capital in portfolio state.",
            )
        )
        return critiques

    def apply_vetoes(self, findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
        vetoes: list[Finding] = []
        surviving: list[Finding] = []
        for finding in findings:
            if finding.kind == FindingKind.UNSAFE or (
                finding.vetoable and finding.priority == Priority.P0 and "live" in finding.detail.lower()
            ):
                finding.vetoed = True
                finding.veto_reason = "Risk/Governance/Stewardship veto: unsafe or premature live path"
                vetoes.append(
                    Finding(
                        team_id="IDC-JPM",
                        team_name="Governance and Operations",
                        kind=FindingKind.VETO,
                        title=f"Veto applied: {finding.title}",
                        detail=finding.veto_reason,
                        evidence=[finding.team_id, finding.kind.value],
                        watchfloor_ids=finding.watchfloor_ids,
                        priority=Priority.P0,
                        implementation_task="Do not schedule vetoed items without HUMAN-1 override.",
                    )
                )
            # Ceiling breach is not a veto of the finding — it's a finding that must be fixed
            surviving.append(finding)
        # Explicit veto: any recommendation to enable live execution
        for finding in list(surviving):
            text = (finding.title + finding.detail + finding.implementation_task).lower()
            if "live_execution_enabled=true" in text or "enable live" in text:
                finding.vetoed = True
                finding.veto_reason = "Standing veto: live execution remains disabled"
                vetoes.append(
                    Finding(
                        team_id="IDC-BLACKROCK",
                        team_name="Portfolio and Risk",
                        kind=FindingKind.VETO,
                        title="Veto: enabling live execution",
                        detail=finding.veto_reason,
                        evidence=[finding.title],
                        watchfloor_ids=["RISK-1", "GOV-CHAIR", "SEC-HALT", "HUMAN-1"],
                        priority=Priority.P0,
                        implementation_task="Ignore live-enable tasks until Phase 5 authorization artifact exists.",
                    )
                )
        return surviving, vetoes

    def chief_decisions(self, findings: list[Finding], critiques: list[Finding]) -> list[Finding]:
        decisions = [
            Finding(
                team_id="IDC-CHIEF",
                team_name="Chief Architecture",
                kind=FindingKind.DECISION,
                title="Unified enhance sequence adopted",
                detail=(
                    "P0: separation + ceiling governance + measurable contracts. "
                    "P1: durable lineage, fixed-dollar sizing, regime gate, ResearchSignal wiring. "
                    "P2: data adapters, backtest factory, ML compute budget. "
                    "P3: limited live only with explicit HUMAN-1 authorization."
                ),
                evidence=[f.team_id for f in findings[:8]],
                watchfloor_ids=["GOV-CHAIR", "ARCH-1", "HUMAN-1"],
                priority=Priority.P0,
                implementation_task="Execute tasks_by_priority in order; do not skip P0.",
            ),
            Finding(
                team_id="IDC-CHIEF",
                team_name="Chief Architecture",
                kind=FindingKind.DECISION,
                title="Watchfloor IDs remain canonical; council is designer/supervisor layer",
                detail=(
                    "Institutional teams design and enhance; Watchfloor strategy agents propose; "
                    "RISK-1/COMP-1/GOV-CHAIR/SEC-HALT/HUMAN-1 decide; EXEC-1 executes paper."
                ),
                evidence=["user role separation mandate"],
                watchfloor_ids=["EXEC-1", "RISK-1", "GOV-CHAIR"],
                priority=Priority.P0,
                implementation_task="Keep IDC-* agents out of TradeProposal emission.",
            ),
        ]
        # Promote critique decisions
        decisions.extend([c for c in critiques if c.kind == FindingKind.DECISION])
        return decisions

    def run(self) -> EnhancementPlan:
        findings = self.independent_audits()
        critiques = self.cross_critique(findings)
        surviving, vetoes = self.apply_vetoes(findings + critiques)
        decisions = self.chief_decisions(surviving, critiques)

        tasks: dict[str, list[dict[str, Any]]] = {p.value: [] for p in Priority}
        seen: set[str] = set()
        for item in surviving + decisions:
            if item.vetoed or not item.implementation_task:
                continue
            key = item.implementation_task.strip()
            if key in seen:
                continue
            seen.add(key)
            tasks[item.priority.value].append(
                {
                    "title": item.title,
                    "task": item.implementation_task,
                    "owner_team": item.team_name,
                    "watchfloor_ids": item.watchfloor_ids,
                    "kind": item.kind.value,
                }
            )

        dissenting = [
            f.title + " — " + f.detail
            for f in surviving
            if f.kind == FindingKind.DISSENT
        ]

        return EnhancementPlan(
            generated_at=datetime.now(timezone.utc).isoformat(),
            organization=self.registry.get("organization", "watchfloor"),
            registry_version=str(self.registry.get("version")),
            agent_counts=dict(self.registry.get("counts", {})),
            findings=surviving,
            cross_critiques=critiques,
            vetoes=vetoes,
            decisions=decisions,
            tasks_by_priority=tasks,
            reasoning=(
                "Council ran independent audits against the Watchfloor registry and "
                "paper-org wiring, cross-critiqued trading vs risk vs stewardship "
                "tensions, applied standing live-execution vetoes, and ordered "
                "implementation by P0→P3."
            ),
            dissenting_views=dissenting,
        )


def plan_to_markdown(plan: EnhancementPlan) -> str:
    lines = [
        "# Institutional Design Council — Enhancement Plan",
        "",
        f"Generated: `{plan.generated_at}`",
        f"Organization: **{plan.organization}** (registry v{plan.registry_version})",
        f"Agents: `{plan.agent_counts}`",
        "",
        "## Reasoning",
        plan.reasoning,
        "",
        "## Decisions",
    ]
    for d in plan.decisions:
        lines.append(f"- **{d.title}** — {d.detail}")
        lines.append(f"  - Task: {d.implementation_task}")
    lines.append("")
    lines.append("## Vetoes")
    if not plan.vetoes:
        lines.append("- None beyond standing live-execution lock.")
    for v in plan.vetoes:
        lines.append(f"- **{v.title}**: {v.detail}")
    lines.append("")
    lines.append("## Dissenting views retained")
    for d in plan.dissenting_views or ["None"]:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("## Implementation tasks by priority")
    for priority in ["P0", "P1", "P2", "P3"]:
        lines.append(f"### {priority}")
        items = plan.tasks_by_priority.get(priority) or []
        if not items:
            lines.append("- (none)")
            continue
        for i, task in enumerate(items, 1):
            lines.append(f"{i}. **{task['title']}** ({task['owner_team']})")
            lines.append(f"   - {task['task']}")
            if task.get("watchfloor_ids"):
                lines.append(f"   - Seats: {', '.join(task['watchfloor_ids'])}")
    lines.append("")
    lines.append("## Full findings")
    for f in plan.findings:
        flag = " [VETOED]" if f.vetoed else ""
        lines.append(f"- `{f.priority.value}` `{f.kind.value}` **{f.team_name}**: {f.title}{flag}")
        lines.append(f"  - {f.detail}")
    lines.append("")
    return "\n".join(lines)
