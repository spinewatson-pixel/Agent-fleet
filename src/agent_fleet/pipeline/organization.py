"""End-to-end paper-trading operating chain.

Data → validate → research/signal → strategy proposal → independent validation →
portfolio eval → risk approval → capital stewardship → paper execution →
monitor → attribution → controlled improvement

Strategy agents propose only. Risk/governance hold veto. Live execution disabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agent_fleet.contracts.models import ApprovalAuthority
from agent_fleet.contracts.registry import build_all_contracts
from agent_fleet.execution.paper_broker import PaperBroker
from agent_fleet.memory.learning import ChangeRequest, LearningRegistry, LearningStage
from agent_fleet.messaging.bus import MessageBus
from agent_fleet.messaging.schemas import (
    CapitalStewardDecisionPayload,
    DecisionAction,
    Envelope,
    ExecutionOrderPayload,
    MessageType,
    OrderType,
    PortfolioEvaluationPayload,
    RiskDecisionPayload,
    Side,
    TradeProposalPayload,
    ValidationResultPayload,
)
from agent_fleet.risk.engine import PortfolioState, RiskLimits, evaluate_proposal


@dataclass
class ChainResult:
    correlation_id: str
    stages: list[str] = field(default_factory=list)
    approved: bool = False
    rejected_by: str | None = None
    reasons: list[str] = field(default_factory=list)
    fill: dict[str, Any] | None = None
    envelopes: list[Envelope] = field(default_factory=list)


class OperatingOrganization:
    """Wires contracts, bus, risk, paper broker into one paper-trading org."""

    def __init__(
        self,
        nav: float = 100_000.0,
        risk_limits: RiskLimits | None = None,
    ) -> None:
        self.contracts = build_all_contracts()
        self.bus = MessageBus()
        self.broker = PaperBroker()
        self.state = PortfolioState(nav=nav, cash=nav)
        self.limits = risk_limits or RiskLimits()
        self.learning = LearningRegistry()
        self.prices: dict[str, float] = {}
        self.sectors: dict[str, str] = {}
        self._pending: dict[str, dict[str, Any]] = {}
        self._wire_handlers()

    def _wire_handlers(self) -> None:
        self.bus.subscribe_type(MessageType.EMERGENCY_HALT, self._on_halt)

    def _on_halt(self, envelope: Envelope) -> None:
        self.state.halted = True
        self.bus.emergency_halt()

    def set_price(self, symbol: str, price: float, sector: str | None = None) -> None:
        self.prices[symbol] = price
        self.state.prices[symbol] = price
        if sector:
            self.sectors[symbol] = sector

    def ingest_market_data(self, symbol: str, price: float, source_id: str = "SRC-MKT-OHLCV") -> Envelope:
        env = Envelope(
            message_type=MessageType.MARKET_DATA,
            source_agent_id="DATA-MKT-001",
            target_agent_ids=["DATA-VAL-001"],
            payload={
                "symbol": symbol,
                "venue": "PAPER",
                "ts": datetime.now(timezone.utc).isoformat(),
                "close": price,
                "source_id": source_id,
                "quality_score": 1.0,
            },
            audit_tags=["ingestion"],
        )
        self.bus.publish(env)
        # validation pass-through for paper bootstrap
        validated = Envelope(
            message_type=MessageType.DATA_VALIDATED,
            source_agent_id="DATA-VAL-001",
            target_agent_ids=["*"],
            correlation_id=env.correlation_id,
            causation_id=env.message_id,
            payload={**env.payload, "validated": True},
            audit_tags=["validation"],
        )
        self.bus.publish(validated)
        self.set_price(symbol, price)
        return validated

    def validate_proposal(self, proposal: TradeProposalPayload) -> ValidationResultPayload:
        contract = self.contracts.get(proposal.strategy_agent_id)
        checks: list[dict[str, Any]] = []
        reasons: list[str] = []
        passed = True

        if contract is None:
            return ValidationResultPayload(
                proposal_id=proposal.proposal_id,
                validator_agent_id="SIG-VAL-001",
                passed=False,
                checks=[{"check": "known_strategy", "ok": False}],
                reasons=["Unknown strategy agent"],
            )

        checks.append({"check": "contract_loaded", "ok": True})
        if proposal.symbol.split(":")[0] if False else proposal.symbol:
            # asset universe: allow if any permitted prefix match or explicit list contains class tags
            permitted = contract.assets_and_markets_permitted
            # For paper: symbols are allowed if universe tags exist (strategy declares classes)
            ok_universe = len(permitted) > 0
            checks.append({"check": "universe", "ok": ok_universe})
            if not ok_universe:
                passed = False
                reasons.append("Symbol/universe not permitted")

        if not proposal.setup_rules_fired:
            passed = False
            reasons.append("No setup rules fired")
            checks.append({"check": "setup_rules", "ok": False})
        else:
            checks.append({"check": "setup_rules", "ok": True})

        if proposal.strategy_version != contract.strategy_version:
            # warn but allow if design phase — hard fail when paper_active+
            checks.append(
                {
                    "check": "version_match",
                    "ok": proposal.strategy_version == contract.strategy_version,
                }
            )

        # Strategy must not self-approve — structural check
        if ApprovalAuthority.APPROVE in contract.authorities:
            passed = False
            reasons.append("Strategy contract illegally holds APPROVE")
            checks.append({"check": "separation_of_duties", "ok": False})
        else:
            checks.append({"check": "separation_of_duties", "ok": True})

        if proposal.symbol not in self.prices:
            passed = False
            reasons.append("No validated price for symbol")
            checks.append({"check": "price_available", "ok": False})
        else:
            checks.append({"check": "price_available", "ok": True})

        return ValidationResultPayload(
            proposal_id=proposal.proposal_id,
            validator_agent_id="SIG-VAL-001",
            passed=passed,
            checks=checks,
            reasons=reasons,
        )

    def run_proposal_chain(self, proposal: TradeProposalPayload) -> ChainResult:
        """Full authority chain for one trade proposal (paper only)."""
        result = ChainResult(correlation_id=str(uuid4()))
        corr = result.correlation_id

        # 1) Proposal published by strategy
        prop_env = Envelope(
            message_type=MessageType.TRADE_PROPOSAL,
            source_agent_id=proposal.strategy_agent_id,
            target_agent_ids=["SIG-VAL-001"],
            correlation_id=corr,
            payload=proposal.model_dump(mode="json"),
            audit_tags=["proposal"],
        )
        self.bus.publish(prop_env)
        result.envelopes.append(prop_env)
        result.stages.append("strategy_proposal")

        # 2) Independent validation
        validation = self.validate_proposal(proposal)
        val_env = Envelope(
            message_type=MessageType.VALIDATION_RESULT,
            source_agent_id="SIG-VAL-001",
            target_agent_ids=["PORT-ALLOC-001"],
            correlation_id=corr,
            causation_id=prop_env.message_id,
            payload=validation.model_dump(mode="json"),
            audit_tags=["validation"],
        )
        self.bus.publish(val_env)
        result.envelopes.append(val_env)
        result.stages.append("independent_validation")
        if not validation.passed:
            result.rejected_by = "SIG-VAL-001"
            result.reasons = validation.reasons
            return result

        price = self.prices[proposal.symbol]
        stop_distance_pct = None
        if proposal.stop_price and price:
            stop_distance_pct = abs(price - proposal.stop_price) / price

        # 3) Portfolio evaluation
        # Portfolio may reduce; does not final-approve risk
        port_qty_hint = None
        if proposal.quantity_hint:
            port_qty_hint = proposal.quantity_hint
        port_action = DecisionAction.APPROVE
        port_reasons = ["Fits allocation budget (paper heuristic)"]
        # crude concentration: reject if already large position
        existing = abs(self.state.positions.get(proposal.symbol, 0.0) * price) / self.state.nav
        if existing >= self.limits.max_position_pct_nav:
            port_action = DecisionAction.REJECT
            port_reasons = ["Existing position at max"]
        port_payload = PortfolioEvaluationPayload(
            proposal_id=proposal.proposal_id,
            action=port_action,
            recommended_quantity=port_qty_hint,
            recommended_risk_pct_nav=proposal.risk_per_trade_pct_nav_request,
            portfolio_impact={"existing_position_pct_nav": existing},
            reasons=port_reasons,
        )
        port_env = Envelope(
            message_type=MessageType.PORTFOLIO_EVALUATION,
            source_agent_id="PORT-ALLOC-001",
            target_agent_ids=["RISK-APPR-001"],
            correlation_id=corr,
            payload=port_payload.model_dump(mode="json"),
            audit_tags=["portfolio"],
        )
        self.bus.publish(port_env)
        result.envelopes.append(port_env)
        result.stages.append("portfolio_evaluation")
        if port_action == DecisionAction.REJECT:
            result.rejected_by = "PORT-ALLOC-001"
            result.reasons = port_reasons
            return result

        # 4) Risk approval (veto authority)
        verdict = evaluate_proposal(
            proposal,
            self.state,
            self.limits,
            price=price,
            sector=self.sectors.get(proposal.symbol),
            stop_distance_pct=stop_distance_pct,
        )
        risk_payload = RiskDecisionPayload(
            proposal_id=proposal.proposal_id,
            action=verdict.action,
            approved_quantity=verdict.approved_quantity,
            max_loss_pct_nav=self.limits.max_risk_per_trade_pct_nav,
            constraints_applied=verdict.constraints_applied,
            reasons=verdict.reasons,
            veto=verdict.veto,
        )
        risk_env = Envelope(
            message_type=MessageType.RISK_DECISION,
            source_agent_id="RISK-APPR-001",
            target_agent_ids=["CAP-STEW-001", "EXEC-PAPER-001"],
            correlation_id=corr,
            payload=risk_payload.model_dump(mode="json"),
            audit_tags=["risk"],
        )
        self.bus.publish(risk_env)
        result.envelopes.append(risk_env)
        result.stages.append("risk_approval")
        if verdict.action in {DecisionAction.REJECT, DecisionAction.PAUSE} or not verdict.approved_quantity:
            result.rejected_by = "RISK-APPR-001"
            result.reasons = verdict.reasons
            return result

        qty = verdict.approved_quantity
        if verdict.action == DecisionAction.REDUCE and verdict.approved_quantity:
            qty = verdict.approved_quantity

        # 5) Capital stewardship (quality / anti-churn veto)
        steward_action = DecisionAction.APPROVE
        steward_reasons = ["No stewardship objection"]
        steward_veto = False
        # Reject pure activity without thesis for QUAL path, or tiny edge churn
        if not proposal.thesis or len(proposal.thesis.strip()) < 10:
            steward_action = DecisionAction.REJECT
            steward_reasons = ["Insufficient economic thesis — unnecessary activity"]
            steward_veto = True
        # Long-term quality: require CAP review path mark
        if proposal.strategy_agent_id == "STRAT-QUAL-001" and "moat" not in proposal.thesis.lower() and "quality" not in proposal.thesis.lower():
            steward_action = DecisionAction.REJECT
            steward_reasons = ["QUAL proposals must reference quality/moat thesis"]
            steward_veto = True

        steward_payload = CapitalStewardDecisionPayload(
            proposal_id=proposal.proposal_id,
            action=steward_action,
            reasons=steward_reasons,
            quality_score=0.8 if steward_action == DecisionAction.APPROVE else 0.2,
            veto=steward_veto,
        )
        steward_env = Envelope(
            message_type=MessageType.CAPITAL_STEWARD_DECISION,
            source_agent_id="CAP-STEW-001",
            target_agent_ids=["EXEC-PAPER-001"],
            correlation_id=corr,
            payload=steward_payload.model_dump(mode="json"),
            audit_tags=["stewardship"],
        )
        self.bus.publish(steward_env)
        result.envelopes.append(steward_env)
        result.stages.append("capital_stewardship")
        if steward_action == DecisionAction.REJECT:
            result.rejected_by = "CAP-STEW-001"
            result.reasons = steward_reasons
            return result

        # 6) Paper execution — only if risk + steward approved
        order = ExecutionOrderPayload(
            order_id=str(uuid4()),
            proposal_id=proposal.proposal_id,
            symbol=proposal.symbol,
            side=proposal.side,
            order_type=proposal.order_type,
            quantity=qty,
            limit_price=proposal.limit_price or price,
            stop_price=proposal.stop_price,
            authorized_by=["RISK-APPR-001", "CAP-STEW-001", "PORT-ALLOC-001"],
            paper=True,
        )
        order_env = Envelope(
            message_type=MessageType.EXECUTION_ORDER,
            source_agent_id="EXEC-PAPER-001",
            target_agent_ids=["MON-LIVE-001", "REV-ATTR-001"],
            correlation_id=corr,
            payload=order.model_dump(mode="json"),
            audit_tags=["execution", "paper"],
        )
        self.bus.publish(order_env)
        result.envelopes.append(order_env)
        result.stages.append("execution")

        fill = self.broker.execute(order, last_price=price)
        fill_env = Envelope(
            message_type=MessageType.FILL_REPORT,
            source_agent_id="EXEC-PAPER-001",
            target_agent_ids=["MON-LIVE-001", "REV-ATTR-001", "PORT-ALLOC-001"],
            correlation_id=corr,
            payload=fill.model_dump(mode="json"),
            audit_tags=["fill", "paper"],
        )
        self.bus.publish(fill_env)
        result.envelopes.append(fill_env)
        result.stages.append("fill")

        # Update portfolio state
        signed_qty = fill.quantity if fill.side in {Side.BUY, Side.COVER} else -fill.quantity
        self.state.positions[fill.symbol] = self.state.positions.get(fill.symbol, 0.0) + signed_qty
        self.state.cash -= signed_qty * fill.price + fill.fees
        result.stages.append("live_monitoring_armed")
        result.stages.append("post_trade_attribution_queued")

        # Attribution stub
        attr_env = Envelope(
            message_type=MessageType.ATTRIBUTION_REPORT,
            source_agent_id="REV-ATTR-001",
            target_agent_ids=["LEARN-CTRL-001", "GOV-COMP-001"],
            correlation_id=corr,
            payload={
                "report_id": str(uuid4()),
                "proposal_id": proposal.proposal_id,
                "strategy_agent_id": proposal.strategy_agent_id,
                "pnl": 0.0,
                "alpha_attribution": {"entry": 0.0},
                "execution_quality": {"slippage_bps": fill.slippage_bps or 0.0},
                "lessons": [],
            },
            audit_tags=["attribution"],
        )
        self.bus.publish(attr_env)
        result.envelopes.append(attr_env)
        result.stages.append("post_trade_attribution")

        result.approved = True
        result.fill = fill.model_dump(mode="json")
        result.reasons = verdict.reasons + steward_reasons
        return result

    def emergency_halt(self, reason: str) -> None:
        env = Envelope(
            message_type=MessageType.EMERGENCY_HALT,
            source_agent_id="RISK-APPR-001",
            target_agent_ids=["*"],
            payload={"reason": reason},
            audit_tags=["emergency"],
        )
        self.bus.publish(env)

    def propose_improvement(self, change: ChangeRequest) -> ChangeRequest:
        if not change.experimental_only and change.production_rules_touched:
            # must start in experimental tracking anyway
            change.experimental_only = True
            change.notes.append("Forced experimental_only for production rule changes")
        self.learning.register(change)
        env = Envelope(
            message_type=MessageType.IMPROVEMENT_PROPOSAL,
            source_agent_id="LEARN-CTRL-001",
            target_agent_ids=["RISK-APPR-001", "GOV-COMP-001"],
            payload=change.model_dump(mode="json"),
            audit_tags=["learning"],
        )
        self.bus.publish(env)
        return change

    def org_map(self) -> dict[str, Any]:
        by_dept: dict[str, list[str]] = {}
        for c in self.contracts.values():
            by_dept.setdefault(c.department, []).append(c.agent_id)
        return {
            "live_execution_enabled": False,
            "environment": "paper",
            "departments": by_dept,
            "agent_count": len(self.contracts),
            "operating_chain": [
                "DATA-MKT-001/DATA-NEWS-001",
                "DATA-VAL-001",
                "RSH-FUND-001/RSH-QUANT-001",
                "STRAT-*",
                "SIG-VAL-001",
                "PORT-ALLOC-001",
                "RISK-APPR-001",
                "CAP-STEW-001",
                "EXEC-PAPER-001",
                "MON-LIVE-001",
                "REV-ATTR-001",
                "LEARN-CTRL-001",
            ],
        }
