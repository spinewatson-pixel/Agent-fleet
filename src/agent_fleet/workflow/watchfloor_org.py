"""Watchfloor-native paper organization.

Canonical agent IDs come from config/watchfloor_registry.json.
Provisional STRAT-* / PORT-RISK-* IDs remain available as compatibility
aliases for earlier Phase-0 tests only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_fleet.agents.watchfloor_contracts import (
    all_proposer_contracts,
    contract_is_complete,
)
from agent_fleet.core.authority import AuthorityResolver
from agent_fleet.core.bus import MessageBus
from agent_fleet.core.events import EventStore
from agent_fleet.core.memory import MemoryStore
from agent_fleet.core.regime import RegimeService
from agent_fleet.paper.broker import PaperBroker
from agent_fleet.registry.watchfloor import (
    assert_separation_of_duties,
    hard_rules,
    load_watchfloor_registry,
    proposers,
)
from agent_fleet.schemas.enums import (
    ActionType,
    ApprovalStatus,
    Environment,
    MarketRegime,
    MessageType,
    Side,
    Stage,
)
from agent_fleet.schemas.messages import (
    AttributionReport,
    ImprovementProposal,
    MarketEvent,
    MessageEnvelope,
    PortfolioVerdict,
    ResearchSignal,
    RiskVerdict,
    TradeProposal,
    ValidationResult,
)


# Compatibility aliases: legacy Phase-0 IDs → Watchfloor IDs
ALIAS_TO_WATCHFLOOR = {
    "PORT-RISK-001": "RISK-1",
    "GOV-OPS-001": "GOV-CHAIR",
    "CAP-STEW-001": "BRK-SAFE",
    "EXEC-OMS-001": "EXEC-1",
    "VAL-IND-001": "FIT-1",
    "MKT-INFO-001": "MKT-1",
    "ATTR-001": "ATTR-1",
    "LEARN-001": "SYNTH-1",
    "ARCH-CHIEF-001": "GOV-CHAIR",
    "TRADE-OPS-001": "HEAD-TRADE",
    "QUANT-RES-001": "MINE-1",
    "FUND-RES-001": "CORP-1",
    "SYS-INTEL-001": "MEM-1",
    "AI-INFRA-001": "ML-ARCH",
    "MON-LIVE-001": "COMP-1",
}


def _default_event_store() -> EventStore:
    return EventStore(path=Path("data/audit/events.jsonl"))


@dataclass
class WatchfloorOrganization:
    """Paper-trading org using Watchfloor agent identities."""

    environment: Environment = Environment.PAPER
    nav_usd: float = 1_000_000.0
    event_store: EventStore = field(default_factory=_default_event_store)
    memory: MemoryStore = field(default_factory=MemoryStore)
    bus: MessageBus | None = None
    authority: AuthorityResolver | None = None
    broker: PaperBroker | None = None
    regime: RegimeService = field(default_factory=RegimeService)
    registry: dict[str, Any] = field(default_factory=dict)
    contracts: dict[str, Any] = field(default_factory=dict)
    halted: bool = False
    strategy_exposure: dict[str, float] = field(default_factory=dict)
    name_exposure: dict[str, float] = field(default_factory=dict)
    name_exposure_usd: dict[str, float] = field(default_factory=dict)
    gross_exposure: float = 0.0
    paper_experiment_capital_usd: float = 0.0
    stewardship_sleeve_capital_usd: float = 0.0
    orders_today_by_symbol: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        rules = hard_rules()
        if rules.get("live_execution_enabled"):
            raise PermissionError("Watchfloor hard rule forbids live execution")
        assert_separation_of_duties()
        self.registry = load_watchfloor_registry()
        self.contracts = all_proposer_contracts()
        self.authority = AuthorityResolver(
            live_execution_enabled=False,
            veto_agents=set(self.registry["veto_agents"]),
            chain=list(self.registry["approval_chain"]),
        )
        self.broker = PaperBroker(nav_usd=self.nav_usd, cash_usd=self.nav_usd)
        self.bus = MessageBus(event_store=self.event_store)
        for agent in proposers():
            self.bus.set_send_permission(agent["id"], {MessageType.TRADE_PROPOSAL.value})
        self.bus.set_send_permission("EXEC-1", {MessageType.EXECUTION_REPORT.value})
        self.bus.set_send_permission("MKT-1", {MessageType.MARKET_EVENT.value})
        self.bus.set_send_permission("CORP-1", {MessageType.RESEARCH_SIGNAL.value})
        self.bus.set_send_permission("REG-1", {MessageType.AUDIT_EVENT.value})

    def _cohort_size_usd(self, agent: dict[str, Any]) -> float | None:
        sizing = agent.get("sizing")
        lo, hi = hard_rules().get("default_sizing_usd", [1, 2])
        mid = float((lo + hi) / 2.0)
        if sizing == "fixed_1_2_usd":
            return mid
        if sizing in {"experimental_variable", "desk_set"}:
            return None
        if agent.get("division") == "trade" and sizing is None:
            return mid
        return None

    def validate_proposal(self, proposal: TradeProposal) -> ValidationResult:
        agent = next(
            (a for a in self.registry["agents"] if a["id"] == proposal.strategy_agent_id),
            None,
        )
        contract = self.contracts.get(proposal.strategy_agent_id)
        checks = {
            "known_proposer": agent is not None and bool(agent.get("may_propose_trades")),
            "contract_complete": contract is not None and contract_is_complete(contract),
            "has_setup_or_thesis": bool(proposal.setup_rules_fired) or bool(proposal.thesis),
            "setup_rules_from_contract": bool(proposal.setup_rules_fired),
            "stop_differs": proposal.stop_loss != proposal.entry_price_target,
            "size_positive": proposal.suggested_size_pct_nav > 0
            or (proposal.suggested_size_usd or 0) > 0,
            "not_halted": not self.halted,
            "paper_environment": self.environment == Environment.PAPER,
            "regime_admitted": self.regime.admits(
                list(proposal.valid_regimes),
                list(contract.invalid_regimes) if contract else None,
            ),
        }
        if agent and agent.get("thesis_required", True) and agent.get("division") != "quant":
            checks["thesis_present"] = len(proposal.thesis.strip()) >= 8
        # Quant thesis-exempt path still requires OOS evidence package
        if agent and (
            agent.get("division") == "quant" or str(agent.get("id", "")).startswith("RT-")
        ):
            checks["evidence_package_present"] = bool(proposal.evidence_package_id)
        defects = [k for k, ok in checks.items() if not ok]
        return ValidationResult(
            proposal_id=proposal.proposal_id,
            validator_agent_id="FIT-1",
            passed=not defects,
            checks=checks,
            defects=defects,
        )

    def portfolio_risk(self, proposal: TradeProposal) -> tuple[PortfolioVerdict, RiskVerdict]:
        if self.halted:
            return (
                PortfolioVerdict(
                    proposal_id=proposal.proposal_id,
                    portfolio_agent_id="RISK-1",
                    action=ActionType.REJECT,
                    reasons=["org_halted"],
                ),
                RiskVerdict(
                    proposal_id=proposal.proposal_id,
                    risk_agent_id="RISK-1",
                    action=ActionType.REJECT,
                    reasons=["org_halted"],
                    veto=True,
                ),
            )

        size_usd = proposal.suggested_size_usd
        if size_usd is not None and size_usd > 0:
            size = (size_usd / self.nav_usd) * 100.0
        else:
            size = min(proposal.suggested_size_pct_nav, 2.0)
            size_usd = self.nav_usd * (size / 100.0)

        reasons: list[str] = []
        corr_flags: list[str] = []
        action = ActionType.APPROVE

        # Simple correlation cluster: same-symbol concurrent notional
        cluster_usd = self.name_exposure_usd.get(proposal.symbol, 0.0) + size_usd
        max_cluster_pct = 40.0
        cluster_pct = (cluster_usd / self.nav_usd) * 100.0
        if cluster_pct > max_cluster_pct:
            action = ActionType.REJECT
            size = 0.0
            size_usd = 0.0
            reasons.append("correlated_cluster_limit")
            corr_flags.append(f"{proposal.symbol}:cluster>{max_cluster_pct}%")

        name_exp = self.name_exposure.get(proposal.symbol, 0.0) + size
        if name_exp > 5.0:
            action = ActionType.REDUCE
            remaining = max(0.0, 5.0 - self.name_exposure.get(proposal.symbol, 0.0))
            size = remaining
            size_usd = self.nav_usd * (size / 100.0)
            reasons.append("single_name_limit")
        if self.gross_exposure + size > 100.0:
            action = ActionType.REJECT
            size = 0.0
            size_usd = 0.0
            reasons.append("gross_exposure_limit")

        # Per-symbol daily order cap (paper coordination)
        if self.orders_today_by_symbol.get(proposal.symbol, 0) >= 20:
            action = ActionType.REJECT
            size = 0.0
            size_usd = 0.0
            reasons.append("daily_symbol_order_cap")

        if size <= 0 and action != ActionType.REJECT:
            action = ActionType.REJECT
            reasons.append("no_capacity")
        if action == ActionType.APPROVE:
            reasons.append("within_limits")
            if proposal.suggested_size_usd:
                reasons.append("fixed_dollar_cohort_sizing")

        portfolio = PortfolioVerdict(
            proposal_id=proposal.proposal_id,
            portfolio_agent_id="RISK-1",
            action=action,
            approved_size_pct_nav=size if action != ActionType.REJECT else None,
            approved_size_usd=size_usd if action != ActionType.REJECT else None,
            reasons=reasons,
            exposure_after={
                "gross_pct": self.gross_exposure + (size if action != ActionType.REJECT else 0),
                "name_usd": cluster_usd if action != ActionType.REJECT else self.name_exposure_usd.get(proposal.symbol, 0.0),
            },
            correlation_flags=corr_flags,
        )
        risk = RiskVerdict(
            proposal_id=proposal.proposal_id,
            risk_agent_id="RISK-1",
            action=action,
            approved_size_pct_nav=size if action != ActionType.REJECT else None,
            approved_size_usd=size_usd if action != ActionType.REJECT else None,
            reasons=reasons,
            veto=action == ActionType.REJECT,
        )
        return portfolio, risk

    def stewardship(self, proposal: TradeProposal, risk: RiskVerdict) -> RiskVerdict:
        if risk.action == ActionType.REJECT:
            return RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id="BRK-SAFE",
                action=ActionType.REJECT,
                reasons=["upstream_risk_reject"],
                veto=True,
            )
        if proposal.expected_edge_bps < 15 and proposal.holding_period_days_max <= 5:
            return RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id="BRK-SAFE",
                action=ActionType.REJECT,
                reasons=["edge_below_hurdle_short_horizon"],
                veto=True,
            )
        # Berkshire desk quality gate
        if proposal.strategy_agent_id.startswith("BRK-TRD"):
            moat = proposal.metadata.get("moat_score")
            mos = proposal.metadata.get("margin_of_safety")
            if moat is None or mos is None:
                return RiskVerdict(
                    proposal_id=proposal.proposal_id,
                    risk_agent_id="BRK-SAFE",
                    action=ActionType.REJECT,
                    reasons=["missing_moat_or_margin_of_safety"],
                    veto=True,
                )
        return RiskVerdict(
            proposal_id=proposal.proposal_id,
            risk_agent_id="BRK-SAFE",
            action=ActionType.APPROVE,
            approved_size_pct_nav=risk.approved_size_pct_nav,
            approved_size_usd=risk.approved_size_usd,
            reasons=["stewardship_pass"],
        )

    def governance(self, proposal: TradeProposal, steward: RiskVerdict) -> RiskVerdict:
        if self.halted:
            return RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id="GOV-CHAIR",
                action=ActionType.REJECT,
                reasons=["shutdown"],
                veto=True,
            )
        if steward.action == ActionType.REJECT:
            return RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id="COMP-1",
                action=ActionType.REJECT,
                reasons=["upstream_veto"],
                veto=True,
            )
        size = steward.approved_size_pct_nav or 0
        size_usd = steward.approved_size_usd
        if size > 2.0 and (size_usd is None or size_usd > 100):
            return RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id="HUMAN-1",
                action=ActionType.PAUSE,
                reasons=["mode_b_escalation_above_threshold"],
                veto=False,
            )
        return RiskVerdict(
            proposal_id=proposal.proposal_id,
            risk_agent_id="GOV-CHAIR",
            action=ActionType.APPROVE,
            approved_size_pct_nav=steward.approved_size_pct_nav,
            approved_size_usd=steward.approved_size_usd,
            reasons=["governance_pass_mode_b_auto"],
        )

    def propose_from_watchfloor_agent(
        self,
        agent_id: str,
        *,
        symbol: str,
        side: Side,
        price: float,
        thesis: str,
        confidence: float = 0.7,
        expected_edge_bps: float = 40.0,
        regime: MarketRegime | None = None,
        evidence_package_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        agent = next((a for a in self.registry["agents"] if a["id"] == agent_id), None)
        if agent is None or not agent.get("may_propose_trades"):
            raise PermissionError(f"{agent_id} may not propose trades")
        contract = self.contracts.get(agent_id)
        if contract is None or not contract_is_complete(contract):
            raise PermissionError(f"{agent_id} has incomplete operating contract")

        current_regime = regime or self.regime.label()
        if not self.regime.admits(list(contract.valid_regimes), list(contract.invalid_regimes)):
            # Still build proposal so FIT-1 records regime_admitted defect via chain
            pass

        atr = price * 0.02
        stop = price - 2 * atr if side in {Side.BUY, Side.COVER} else price + 2 * atr
        hold_min = contract.holding_period_days_min
        hold_max = contract.holding_period_days_max

        size_usd = self._cohort_size_usd(agent)
        if size_usd is not None:
            size_pct = max((size_usd / self.nav_usd) * 100.0, 1e-6)
        else:
            size_pct = min(contract.position_sizing.max_pct_nav, 1.0)
            size_usd = None

        setup_ids = [r.rule_id for r in contract.setup_detection_rules]
        meta = dict(metadata or {})
        meta["sizing_mode"] = contract.extra.get("sizing_mode")
        meta["contract_version"] = contract.strategy_version

        # Quant proposals need evidence; allow callers to supply, else paper stub for RT lab
        evid = evidence_package_id
        if evid is None and (
            agent.get("division") == "quant" or agent_id.startswith("RT-")
        ):
            evid = meta.get("evidence_package_id")

        proposal = TradeProposal(
            strategy_agent_id=agent_id,
            strategy_version=contract.strategy_version,
            symbol=symbol,
            side=side,
            thesis=thesis,
            setup_rules_fired=setup_ids,
            entry_price_target=price,
            stop_loss=stop,
            invalidation_rules=list(contract.entry_exit.invalidation_rules),
            suggested_size_pct_nav=size_pct,
            suggested_size_usd=size_usd,
            holding_period_days_min=hold_min,
            holding_period_days_max=hold_max,
            valid_regimes=list(contract.valid_regimes),
            current_regime=current_regime,
            required_data_inputs=list(contract.required_data_inputs),
            evidence_package_id=evid,
            confidence=confidence,
            expected_edge_bps=expected_edge_bps,
            metadata=meta,
        )
        return self.run_approval_chain(proposal)

    def run_approval_chain(self, proposal: TradeProposal) -> dict[str, Any]:
        assert self.authority and self.broker and self.bus
        correlation = proposal.proposal_id
        envelopes: list[MessageEnvelope] = []

        def track(env: MessageEnvelope) -> MessageEnvelope:
            self.bus.publish(env)
            envelopes.append(env)
            return env

        track(
            MessageEnvelope(
                message_type=MessageType.TRADE_PROPOSAL,
                stage=Stage.STRATEGY_PROPOSAL,
                sender_id=proposal.strategy_agent_id,
                recipient_ids=["FIT-1", "MEM-1"],
                correlation_id=correlation,
                payload=proposal.model_dump(mode="json"),
            )
        )
        validation = self.validate_proposal(proposal)
        track(
            MessageEnvelope(
                message_type=MessageType.VALIDATION_RESULT,
                stage=Stage.INDEPENDENT_VALIDATION,
                sender_id="FIT-1",
                recipient_ids=["RISK-1", "MEM-1"],
                correlation_id=correlation,
                payload={
                    "validation": validation.model_dump(mode="json"),
                    "proposal": proposal.model_dump(mode="json"),
                },
            )
        )
        portfolio, risk = self.portfolio_risk(proposal)
        steward = self.stewardship(proposal, risk)
        gov = self.governance(proposal, steward)
        decision = self.authority.resolve(
            proposal, validation, portfolio, risk, steward, gov
        )
        track(
            MessageEnvelope(
                message_type=MessageType.APPROVAL_DECISION,
                stage=Stage.RISK_APPROVAL,
                sender_id="GOV-CHAIR",
                recipient_ids=["EXEC-1", "MEM-1", proposal.strategy_agent_id],
                correlation_id=correlation,
                payload={
                    "decision": decision.model_dump(mode="json"),
                    "proposal": proposal.model_dump(mode="json"),
                },
            )
        )
        fill = None
        if decision.execution_authorized and decision.status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REDUCED,
        }:
            fill = self.broker.execute(proposal, decision)
            if fill.status == "filled":
                if decision.final_size_pct_nav:
                    self.strategy_exposure[proposal.strategy_agent_id] = (
                        self.strategy_exposure.get(proposal.strategy_agent_id, 0.0)
                        + decision.final_size_pct_nav
                    )
                    self.name_exposure[proposal.symbol] = (
                        self.name_exposure.get(proposal.symbol, 0.0)
                        + decision.final_size_pct_nav
                    )
                    self.gross_exposure += decision.final_size_pct_nav
                filled_usd = decision.final_size_usd or (
                    self.nav_usd * ((decision.final_size_pct_nav or 0) / 100.0)
                )
                self.name_exposure_usd[proposal.symbol] = (
                    self.name_exposure_usd.get(proposal.symbol, 0.0) + filled_usd
                )
                self.paper_experiment_capital_usd += filled_usd
                self.orders_today_by_symbol[proposal.symbol] = (
                    self.orders_today_by_symbol.get(proposal.symbol, 0) + 1
                )
            track(
                MessageEnvelope(
                    message_type=MessageType.EXECUTION_REPORT,
                    stage=Stage.EXECUTION,
                    sender_id="EXEC-1",
                    recipient_ids=["COMP-1", "ATTR-1", "MEM-1", "RISK-1"],
                    correlation_id=correlation,
                    payload={
                        "execution": fill.model_dump(mode="json"),
                        "proposal": proposal.model_dump(mode="json"),
                    },
                )
            )
            attr = AttributionReport(
                proposal_id=proposal.proposal_id,
                strategy_agent_id=proposal.strategy_agent_id,
                pnl=0.0,
                pnl_bps=0.0,
                holding_days=0.0,
                alpha_estimate=0.0,
                execution_cost_bps=fill.slippage_bps,
                decision_quality_score=proposal.confidence,
                lessons=["opened_awaiting_exit"],
            )
            self.memory.learn(
                key=f"attr:{proposal.proposal_id}",
                category="pnl",
                data=attr.model_dump(mode="json"),
                agent_id="ATTR-1",
                environment=self.environment,
            )
            improvement = ImprovementProposal(
                proposer_agent_id="SYNTH-1",
                target_agent_id=proposal.strategy_agent_id,
                change_summary="Observe only — no production mutation",
                hypothesis="Track attribution before proposing changes",
                evidence_refs=[proposal.proposal_id],
                production_mutation_allowed=False,
            )
            track(
                MessageEnvelope(
                    message_type=MessageType.IMPROVEMENT_PROPOSAL,
                    stage=Stage.CONTROLLED_IMPROVEMENT,
                    sender_id="SYNTH-1",
                    recipient_ids=["LIFE-1", "RISK-1", "GOV-CHAIR"],
                    correlation_id=correlation,
                    payload=improvement.model_dump(mode="json"),
                )
            )
        return {
            "proposal_id": proposal.proposal_id,
            "strategy_agent_id": proposal.strategy_agent_id,
            "decision": decision.model_dump(mode="json"),
            "fill": fill.model_dump(mode="json") if fill else None,
            "messages": len(envelopes),
            "audit_events": len(self.event_store.events),
            "live_execution_enabled": False,
            "sizing_usd": decision.final_size_usd,
            "event_store_path": str(self.event_store.path) if self.event_store.path else None,
        }

    def ingest_market_event(self, *, symbol: str, price: float, agent_id: str = "AAPL-L") -> dict[str, Any]:
        """Paper path: verified tape event → research signal → watchfloor proposer."""
        assert self.bus
        event = MarketEvent(
            symbol=symbol,
            event_type="bar",
            source="paper_feed",
            source_verified=True,
            timestamp=datetime.now(timezone.utc),
            tags=["bar", symbol],
            normalized={"price": price, "close": price},
        )
        self.bus.publish(
            MessageEnvelope(
                message_type=MessageType.MARKET_EVENT,
                stage=Stage.DATA_INGESTION,
                sender_id="MKT-1",
                recipient_ids=["DQ-1", "MEM-1", "CORP-1"],
                payload=event.model_dump(mode="json"),
            )
        )
        signal = ResearchSignal(
            research_agent_id="CORP-1",
            symbol=symbol,
            thesis=f"Watchfloor research handoff for {symbol}",
            direction=Side.BUY,
            conviction=0.7,
            horizon_days=1,
            features={"close": price, "price": price},
        )
        self.bus.publish(
            MessageEnvelope(
                message_type=MessageType.RESEARCH_SIGNAL,
                stage=Stage.SIGNAL_GENERATION,
                sender_id="CORP-1",
                recipient_ids=[agent_id, "FORE-1", "MEM-1"],
                payload=signal.model_dump(mode="json"),
            )
        )
        return self.propose_from_watchfloor_agent(
            agent_id,
            symbol=symbol,
            side=Side.BUY,
            price=price,
            thesis=f"Logged thesis: {agent_id} reacts to verified tape on {symbol}",
            confidence=0.72,
            expected_edge_bps=35,
        )

    def emergency_halt(self, by_agent: str = "SEC-HALT", reason: str = "emergency") -> None:
        if by_agent not in self.registry["veto_agents"] and by_agent != "SEC-HALT":
            raise PermissionError(f"{by_agent} cannot halt the org")
        self.halted = True
        assert self.bus
        self.bus.event_store.append(
            actor_id=by_agent,
            event_type="shutdown.halt",
            correlation_id="halt",
            payload={"reason": reason},
        )
