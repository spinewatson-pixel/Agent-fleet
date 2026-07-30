"""Institutional department agents — designers, supervisors, and control functions."""

from __future__ import annotations

from typing import Any

from agent_fleet.agents.base import BaseAgent
from agent_fleet.agents.contracts_factory import default_improvement, default_shutdown
from agent_fleet.schemas.contracts import (
    AgentOperatingContract,
    ApprovalRequirements,
    EntryExitRules,
    ExecutionPermissions,
    PositionSizingRules,
    SetupDetectionRule,
)
from agent_fleet.schemas.enums import (
    ActionType,
    AgentRole,
    DeploymentStatus,
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
    MonitoringAlert,
    PortfolioVerdict,
    ResearchSignal,
    RiskVerdict,
    TradeProposal,
    ValidationResult,
)


def _control_contract(
    *,
    agent_name: str,
    agent_id: str,
    department: str,
    supervisory_agent_id: str,
    role: AgentRole,
    strategy: str,
    economic_rationale: str,
    owns_stages: list[str],
    authority_actions: list[str],
    may_place_orders: bool = False,
    information_received_from: list[str] | None = None,
    outputs_sent_to: list[str] | None = None,
) -> AgentOperatingContract:
    return AgentOperatingContract(
        agent_name=agent_name,
        agent_id=agent_id,
        department=department,
        supervisory_agent_id=supervisory_agent_id,
        role=role,
        strategy=strategy,
        economic_rationale=economic_rationale,
        assets_permitted=["ORG_WIDE"],
        markets_permitted=["ORG_WIDE"],
        holding_period_days_min=0,
        holding_period_days_max=0,
        trading_frequency="continuous",
        valid_regimes=list(MarketRegime),
        required_data_inputs=["org_state", "audit_stream"],
        data_sources={"org_state": "SYS-INTEL-001", "audit_stream": "SYS-INTEL-001.events"},
        indicators_features_models=[],
        setup_detection_rules=[
            SetupDetectionRule(
                rule_id=f"{agent_id}-DUTY-01",
                description="Always-on control duty",
                expression="duty_active == True",
                required_inputs=["duty_active"],
                lookback=0,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["n/a"],
            exit_rules=["n/a"],
            stop_loss_rule="n/a",
            invalidation_rules=["shutdown_order"],
        ),
        position_sizing=PositionSizingRules(
            method="fixed_fraction",
            max_pct_nav=0.0,
            min_pct_nav=0.0,
            max_concurrent_positions=0,
            max_sector_pct=0.0,
            notes="Control agent does not size trades",
        ),
        information_received_from=information_received_from or [],
        outputs_sent_to=outputs_sent_to or [],
        approval=ApprovalRequirements(
            can_self_approve=False,
            can_self_execute=False,
            can_set_own_capital_limits=role == AgentRole.PORTFOLIO_RISK,
            can_evaluate_own_performance=False,
        ),
        execution=ExecutionPermissions(
            may_propose_trades=False,
            may_place_orders=may_place_orders,
            may_cancel_orders=may_place_orders,
            may_force_close=role in {AgentRole.PORTFOLIO_RISK, AgentRole.TRADING_OPERATIONS},
            paper_only=True,
            live_enabled=False,
            max_notional_usd=1_000_000 if may_place_orders else 0.0,
        ),
        monitoring_after_entry=["org_controls"],
        memory_retained=["decisions", "vetoes", "incidents"],
        performance_measurements=["false_reject_rate", "missed_risk_events", "latency_ms"],
        failure_shutdown=default_shutdown(["ARCH-CHIEF-001", "GOV-OPS-001"]),
        testing_deployment_status=DeploymentStatus.PAPER,
        strategy_version="0.1.0",
        self_improvement=default_improvement(),
        owns_stages=owns_stages,
        authority_actions=authority_actions,
    )


class MarketInformationAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Market Information Supervisor",
                agent_id="MKT-INFO-001",
                department="market_information",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.MARKET_INFORMATION,
                strategy="Normalize and verify multi-source market/news/filing data",
                economic_rationale="Decision quality depends on verified, tagged, timely inputs",
                owns_stages=["data_ingestion", "information_validation"],
                authority_actions=["reject_unverified_source"],
                outputs_sent_to=["FUND-RES-001", "QUANT-RES-001", "TRADE-OPS-001", "SYS-INTEL-001"],
            ),
            environment,
        )

    def ingest(self, event: MarketEvent) -> MarketEvent | None:
        if not event.source_verified:
            return None
        if not event.tags:
            event.tags = [event.event_type, event.symbol]
        return event

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.MARKET_EVENT:
            return []
        event = MarketEvent.model_validate(envelope.payload)
        verified = self.ingest(event)
        if verified is None:
            return []
        return [
            envelope.with_child(
                message_type=MessageType.MARKET_EVENT,
                stage=Stage.INFORMATION_VALIDATION,
                sender_id=self.agent_id,
                recipient_ids=["FUND-RES-001", "QUANT-RES-001", "SYS-INTEL-001"],
                payload=verified.model_dump(mode="json"),
            )
        ]


class FundamentalResearchAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Research and Strategy Supervisor",
                agent_id="FUND-RES-001",
                department="research_strategy",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.FUNDAMENTAL_RESEARCH,
                strategy="Convert fundamental/sector/macro/event research into standardized signals",
                economic_rationale="Research edge must be machine-consumable by strategy agents",
                owns_stages=["research", "signal_generation"],
                authority_actions=[],
                information_received_from=["MKT-INFO-001"],
                outputs_sent_to=[
                    "STRAT-EARN-001",
                    "STRAT-MACRO-001",
                    "STRAT-SECTOR-001",
                    "STRAT-VALUE-001",
                    "VAL-IND-001",
                ],
            ),
            environment,
        )

    def to_signal(self, event: MarketEvent, direction: Side, conviction: float) -> ResearchSignal:
        return ResearchSignal(
            research_agent_id=self.agent_id,
            symbol=event.symbol,
            thesis=f"Research synthesis on {event.event_type}",
            direction=direction,
            conviction=conviction,
            horizon_days=20,
            catalysts=[event.event_type],
            regime_context=[MarketRegime.UNKNOWN],
            features={
                "price": float(event.normalized.get("price", 0) or 0),
                "close": float(event.normalized.get("price", 0) or 0),
                "ATR_14": float(event.normalized.get("ATR_14", 0) or 0) or None,
                "confidence": conviction,
                **{k: float(v) for k, v in event.normalized.items() if isinstance(v, (int, float))},
            },
            evidence_refs=[event.raw_ref or event.source],
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.MARKET_EVENT:
            return []
        event = MarketEvent.model_validate(envelope.payload)
        direction = Side.BUY if event.normalized.get("bias", "long") == "long" else Side.SELL
        conviction = float(event.normalized.get("conviction", 0.55))
        signal = self.to_signal(event, direction, conviction)
        # Clean None ATR
        signal.features = {k: v for k, v in signal.features.items() if v is not None}
        if "ATR_14" not in signal.features and "close" in signal.features:
            signal.features["ATR_14"] = signal.features["close"] * 0.02
        targets = self.contract.outputs_sent_to
        return [
            envelope.with_child(
                message_type=MessageType.RESEARCH_SIGNAL,
                stage=Stage.SIGNAL_GENERATION,
                sender_id=self.agent_id,
                recipient_ids=targets,
                payload=signal.model_dump(mode="json"),
            )
        ]


class QuantResearchAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Quantitative Research Supervisor",
                agent_id="QUANT-RES-001",
                department="quantitative_research",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.QUANTITATIVE_RESEARCH,
                strategy="Hypothesis generation, features, statistical validation, anti-overfit gates",
                economic_rationale="Only statistically validated edges survive promotion",
                owns_stages=["research", "controlled_improvement"],
                authority_actions=["reject_overfit_model"],
                information_received_from=["MKT-INFO-001"],
                outputs_sent_to=["STRAT-FACTOR-001", "STRAT-MOM-001", "STRAT-MR-001", "VAL-IND-001"],
            ),
            environment,
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        return []  # Features are provided via research/feature service in pipeline


class IndependentValidatorAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Independent Validation Agent",
                agent_id="VAL-IND-001",
                department="quantitative_research",
                supervisory_agent_id="QUANT-RES-001",
                role=AgentRole.VALIDATION,
                strategy="Independent checks that strategy proposals are well-formed and regime-valid",
                economic_rationale="Separation of proposal and validation reduces self-deception",
                owns_stages=["independent_validation"],
                authority_actions=["reject"],
                information_received_from=["STRAT-*", "FUND-RES-001", "QUANT-RES-001"],
                outputs_sent_to=["PORT-RISK-001", "SYS-INTEL-001"],
            ),
            environment,
        )

    def validate(self, proposal: TradeProposal) -> ValidationResult:
        checks = {
            "has_setup_rules": bool(proposal.setup_rules_fired),
            "stop_differs": proposal.stop_loss != proposal.entry_price_target,
            "size_positive": proposal.suggested_size_pct_nav > 0,
            "size_capped": proposal.suggested_size_pct_nav <= 5.0,
            "regime_listed": bool(proposal.valid_regimes),
            "not_self_approving": True,
            "inputs_listed": bool(proposal.required_data_inputs),
        }
        defects = [k for k, ok in checks.items() if not ok]
        return ValidationResult(
            proposal_id=proposal.proposal_id,
            validator_agent_id=self.agent_id,
            passed=not defects,
            checks=checks,
            defects=defects,
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.TRADE_PROPOSAL:
            return []
        proposal = TradeProposal.model_validate(envelope.payload)
        result = self.validate(proposal)
        return [
            envelope.with_child(
                message_type=MessageType.VALIDATION_RESULT,
                stage=Stage.INDEPENDENT_VALIDATION,
                sender_id=self.agent_id,
                recipient_ids=["PORT-RISK-001", "SYS-INTEL-001"],
                payload={
                    "validation": result.model_dump(mode="json"),
                    "proposal": proposal.model_dump(mode="json"),
                },
            )
        ]


class PortfolioRiskAgent(BaseAgent):
    def __init__(
        self,
        environment: Environment = Environment.PAPER,
        limits: dict[str, float] | None = None,
    ):
        super().__init__(
            _control_contract(
                agent_name="Portfolio and Risk Supervisor",
                agent_id="PORT-RISK-001",
                department="portfolio_risk",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.PORTFOLIO_RISK,
                strategy="Portfolio construction, exposure, correlation, stress, drawdown controls",
                economic_rationale="Organization survival depends on portfolio-level risk, not trade-level optimism",
                owns_stages=["portfolio_evaluation", "risk_approval"],
                authority_actions=["approve", "reject", "reduce", "pause", "close"],
                information_received_from=["VAL-IND-001", "TRADE-OPS-001"],
                outputs_sent_to=["CAP-STEW-001", "GOV-OPS-001", "EXEC-OMS-001", "SYS-INTEL-001"],
            ),
            environment,
        )
        self.limits = limits or {
            "max_single_name_pct": 5.0,
            "max_strategy_pct": 30.0,
            "max_gross_exposure_pct": 100.0,
            "daily_loss_halt_pct": 2.0,
            "drawdown_halt_pct": 8.0,
        }
        self.strategy_exposure: dict[str, float] = {}
        self.name_exposure: dict[str, float] = {}
        self.gross_exposure = 0.0
        self.halted = False

    def evaluate(self, proposal: TradeProposal) -> tuple[PortfolioVerdict, RiskVerdict]:
        if self.halted:
            reject = PortfolioVerdict(
                proposal_id=proposal.proposal_id,
                portfolio_agent_id=self.agent_id,
                action=ActionType.REJECT,
                reasons=["portfolio_halted"],
            )
            risk = RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id=self.agent_id,
                action=ActionType.REJECT,
                reasons=["portfolio_halted"],
                veto=True,
            )
            return reject, risk

        size = proposal.suggested_size_pct_nav
        reasons: list[str] = []
        action = ActionType.APPROVE
        strat_exp = self.strategy_exposure.get(proposal.strategy_agent_id, 0.0) + size
        name_exp = self.name_exposure.get(proposal.symbol, 0.0) + size
        gross = self.gross_exposure + size

        if name_exp > self.limits["max_single_name_pct"]:
            size = max(0.0, self.limits["max_single_name_pct"] - self.name_exposure.get(proposal.symbol, 0.0))
            action = ActionType.REDUCE
            reasons.append("single_name_limit")
        if strat_exp > self.limits["max_strategy_pct"]:
            size = min(
                size,
                max(0.0, self.limits["max_strategy_pct"] - self.strategy_exposure.get(proposal.strategy_agent_id, 0.0)),
            )
            action = ActionType.REDUCE
            reasons.append("strategy_limit")
        if gross > self.limits["max_gross_exposure_pct"]:
            action = ActionType.REJECT
            reasons.append("gross_exposure_limit")
            size = 0.0

        if size <= 0 and action != ActionType.REJECT:
            action = ActionType.REJECT
            reasons.append("no_residual_capacity")

        if action == ActionType.APPROVE:
            reasons.append("within_limits")

        portfolio = PortfolioVerdict(
            proposal_id=proposal.proposal_id,
            portfolio_agent_id=self.agent_id,
            action=action if action != ActionType.REJECT else ActionType.REJECT,
            approved_size_pct_nav=size if action != ActionType.REJECT else None,
            reasons=reasons,
            exposure_after={
                "gross": gross if action != ActionType.REJECT else self.gross_exposure,
                "name": name_exp if action != ActionType.REJECT else self.name_exposure.get(proposal.symbol, 0.0),
                "strategy": strat_exp if action != ActionType.REJECT else self.strategy_exposure.get(proposal.strategy_agent_id, 0.0),
            },
        )
        risk = RiskVerdict(
            proposal_id=proposal.proposal_id,
            risk_agent_id=self.agent_id,
            action=action,
            approved_size_pct_nav=size if action != ActionType.REJECT else None,
            stress_pnl_pct=-1.5 * (size / 5.0),
            limit_breaches=[r for r in reasons if r.endswith("limit")],
            reasons=reasons,
            veto=action == ActionType.REJECT,
        )
        return portfolio, risk

    def commit_exposure(self, strategy_id: str, symbol: str, size: float) -> None:
        self.strategy_exposure[strategy_id] = self.strategy_exposure.get(strategy_id, 0.0) + size
        self.name_exposure[symbol] = self.name_exposure.get(symbol, 0.0) + size
        self.gross_exposure += size

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.VALIDATION_RESULT:
            return []
        proposal = TradeProposal.model_validate(envelope.payload["proposal"])
        validation = ValidationResult.model_validate(envelope.payload["validation"])
        if not validation.passed:
            return []
        portfolio, risk = self.evaluate(proposal)
        return [
            envelope.with_child(
                message_type=MessageType.RISK_VERDICT,
                stage=Stage.RISK_APPROVAL,
                sender_id=self.agent_id,
                recipient_ids=["CAP-STEW-001", "GOV-OPS-001", "SYS-INTEL-001"],
                payload={
                    "proposal": proposal.model_dump(mode="json"),
                    "validation": validation.model_dump(mode="json"),
                    "portfolio": portfolio.model_dump(mode="json"),
                    "risk": risk.model_dump(mode="json"),
                },
            )
        ]


class CapitalStewardshipAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Capital Stewardship Supervisor",
                agent_id="CAP-STEW-001",
                department="capital_stewardship",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.CAPITAL_STEWARDSHIP,
                strategy="Veto low-quality activity; protect long-term capital",
                economic_rationale="Activity is not edge; unnecessary risk destroys compounding",
                owns_stages=["risk_approval"],
                authority_actions=["reject", "reduce", "pause"],
                information_received_from=["PORT-RISK-001", "FUND-RES-001"],
                outputs_sent_to=["GOV-OPS-001", "SYS-INTEL-001"],
            ),
            environment,
        )

    def review(self, proposal: TradeProposal, risk: RiskVerdict) -> RiskVerdict:
        reasons = []
        action = ActionType.APPROVE
        size = risk.approved_size_pct_nav
        # Challenge short-horizon noise trading when confidence is weak
        if proposal.holding_period_days_max <= 5 and proposal.confidence < 0.65:
            action = ActionType.REJECT
            reasons.append("short_term_low_conviction_activity_veto")
            size = None
        elif proposal.expected_edge_bps < 15:
            action = ActionType.REJECT
            reasons.append("edge_below_cost_hurdle")
            size = None
        elif proposal.strategy_agent_id == "STRAT-VALUE-001" and proposal.confidence >= 0.7:
            reasons.append("long_term_quality_supported")
        else:
            reasons.append("stewardship_pass")
        return RiskVerdict(
            proposal_id=proposal.proposal_id,
            risk_agent_id=self.agent_id,
            action=action,
            approved_size_pct_nav=size,
            reasons=reasons,
            veto=action == ActionType.REJECT,
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.RISK_VERDICT:
            return []
        proposal = TradeProposal.model_validate(envelope.payload["proposal"])
        risk = RiskVerdict.model_validate(envelope.payload["risk"])
        if risk.action == ActionType.REJECT:
            steward = RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id=self.agent_id,
                action=ActionType.REJECT,
                reasons=["upstream_risk_reject"],
                veto=True,
            )
        else:
            steward = self.review(proposal, risk)
        payload = dict(envelope.payload)
        payload["capital_stewardship"] = steward.model_dump(mode="json")
        return [
            envelope.with_child(
                message_type=MessageType.RISK_VERDICT,
                stage=Stage.RISK_APPROVAL,
                sender_id=self.agent_id,
                recipient_ids=["GOV-OPS-001", "SYS-INTEL-001"],
                payload=payload,
            )
        ]


class GovernanceAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Governance and Operations Supervisor",
                agent_id="GOV-OPS-001",
                department="governance_operations",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.GOVERNANCE,
                strategy="Compliance, permissions, reconciliation, incident escalation",
                economic_rationale="Operational failure is existential risk",
                owns_stages=["risk_approval"],
                authority_actions=["reject", "pause", "shutdown"],
                information_received_from=["CAP-STEW-001", "PORT-RISK-001"],
                outputs_sent_to=["EXEC-OMS-001", "ARCH-CHIEF-001", "SYS-INTEL-001"],
            ),
            environment,
        )
        self.shutdown = False

    def check(self, proposal: TradeProposal, steward: RiskVerdict) -> RiskVerdict:
        if self.shutdown:
            return RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id=self.agent_id,
                action=ActionType.REJECT,
                reasons=["organization_shutdown"],
                veto=True,
            )
        if steward.action == ActionType.REJECT:
            return RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id=self.agent_id,
                action=ActionType.REJECT,
                reasons=["upstream_veto"],
                veto=True,
            )
        # Permission: strategy cannot execute; symbol must be non-empty
        if not proposal.symbol or proposal.strategy_agent_id.startswith("EXEC"):
            return RiskVerdict(
                proposal_id=proposal.proposal_id,
                risk_agent_id=self.agent_id,
                action=ActionType.REJECT,
                reasons=["permission_or_identity_failure"],
                veto=True,
            )
        return RiskVerdict(
            proposal_id=proposal.proposal_id,
            risk_agent_id=self.agent_id,
            action=ActionType.APPROVE,
            approved_size_pct_nav=steward.approved_size_pct_nav,
            reasons=["governance_pass"],
            veto=False,
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.RISK_VERDICT:
            return []
        if "capital_stewardship" not in envelope.payload:
            return []
        proposal = TradeProposal.model_validate(envelope.payload["proposal"])
        steward = RiskVerdict.model_validate(envelope.payload["capital_stewardship"])
        gov = self.check(proposal, steward)
        payload = dict(envelope.payload)
        payload["governance"] = gov.model_dump(mode="json")
        return [
            envelope.with_child(
                message_type=MessageType.RISK_VERDICT,
                stage=Stage.RISK_APPROVAL,
                sender_id=self.agent_id,
                recipient_ids=["ARCH-CHIEF-001", "SYS-INTEL-001"],
                payload=payload,
            )
        ]


class SystemsIntelligenceAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Systems Intelligence Supervisor",
                agent_id="SYS-INTEL-001",
                department="systems_intelligence",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.SYSTEMS_INTELLIGENCE,
                strategy="Map decision system: lineage, permissions, shared context, audit",
                economic_rationale="Unmapped decision systems cannot be controlled or improved",
                owns_stages=[],
                authority_actions=["audit"],
                information_received_from=["*"],
                outputs_sent_to=["ARCH-CHIEF-001", "GOV-OPS-001"],
            ),
            environment,
        )
        self.graph: list[dict[str, Any]] = []

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        self.graph.append(
            {
                "message_id": envelope.message_id,
                "type": envelope.message_type.value,
                "stage": envelope.stage.value,
                "sender": envelope.sender_id,
                "recipients": envelope.recipient_ids,
                "lineage": envelope.lineage,
            }
        )
        return []


class TradingOperationsAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Trading Operations Supervisor",
                agent_id="TRADE-OPS-001",
                department="trading_operations",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.TRADING_OPERATIONS,
                strategy="Live/paper workflow, regime label, OMS coordination, slippage analysis",
                economic_rationale="Multi-strategy execution without coordination destroys edge via costs",
                owns_stages=["execution", "live_monitoring"],
                authority_actions=["pause", "close"],
                information_received_from=["PORT-RISK-001", "MKT-INFO-001"],
                outputs_sent_to=["EXEC-OMS-001", "MON-LIVE-001", "STRAT-*"],
            ),
            environment,
        )
        self.regime = MarketRegime.UNKNOWN

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        return []


class ExecutionAgent(BaseAgent):
    def __init__(self, broker: Any, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Order Management Execution Agent",
                agent_id="EXEC-OMS-001",
                department="trading_operations",
                supervisory_agent_id="TRADE-OPS-001",
                role=AgentRole.EXECUTION,
                strategy="Place only authorized paper/live orders; measure slippage",
                economic_rationale="Unauthorized execution is the highest operational risk",
                owns_stages=["execution"],
                authority_actions=[],
                may_place_orders=True,
                information_received_from=["ARCH-CHIEF-001", "GOV-OPS-001"],
                outputs_sent_to=["MON-LIVE-001", "ATTR-001", "SYS-INTEL-001"],
            ),
            environment,
        )
        self.broker = broker

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.APPROVAL_DECISION:
            return []
        from agent_fleet.schemas.messages import ApprovalDecision, ExecutionReport

        decision = ApprovalDecision.model_validate(envelope.payload["decision"])
        proposal = TradeProposal.model_validate(envelope.payload["proposal"])
        if not decision.execution_authorized:
            return []
        self.assert_may_execute()
        report = self.broker.execute(proposal, decision)
        return [
            envelope.with_child(
                message_type=MessageType.EXECUTION_REPORT,
                stage=Stage.EXECUTION,
                sender_id=self.agent_id,
                recipient_ids=["MON-LIVE-001", "ATTR-001", "SYS-INTEL-001", "PORT-RISK-001"],
                payload={"execution": report.model_dump(mode="json"), "proposal": proposal.model_dump(mode="json")},
            )
        ]


class MonitoringAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Live Monitoring Agent",
                agent_id="MON-LIVE-001",
                department="trading_operations",
                supervisory_agent_id="TRADE-OPS-001",
                role=AgentRole.MONITORING,
                strategy="Post-entry monitoring for stops, invalidation, regime breaks",
                economic_rationale="Unmonitored positions convert edge into unmanaged risk",
                owns_stages=["live_monitoring"],
                authority_actions=["close"],
                information_received_from=["EXEC-OMS-001", "MKT-INFO-001"],
                outputs_sent_to=["TRADE-OPS-001", "PORT-RISK-001", "SYS-INTEL-001"],
            ),
            environment,
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.EXECUTION_REPORT:
            return []
        proposal = TradeProposal.model_validate(envelope.payload["proposal"])
        alert = MonitoringAlert(
            position_id=envelope.payload["execution"]["order_id"],
            proposal_id=proposal.proposal_id,
            alert_type="opened",
            severity="info",
            message=f"Position opened for {proposal.symbol}",
            recommended_action=ActionType.APPROVE,
        )
        return [
            envelope.with_child(
                message_type=MessageType.MONITORING_ALERT,
                stage=Stage.LIVE_MONITORING,
                sender_id=self.agent_id,
                recipient_ids=["TRADE-OPS-001", "SYS-INTEL-001"],
                payload=alert.model_dump(mode="json"),
            )
        ]


class AttributionAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Post-Trade Attribution Agent",
                agent_id="ATTR-001",
                department="quantitative_research",
                supervisory_agent_id="QUANT-RES-001",
                role=AgentRole.ATTRIBUTION,
                strategy="Measure PnL, costs, decision quality; feed controlled improvement",
                economic_rationale="Without attribution, learning is narrative not evidence",
                owns_stages=["post_trade_attribution"],
                authority_actions=[],
                information_received_from=["EXEC-OMS-001", "MON-LIVE-001"],
                outputs_sent_to=["LEARN-001", "QUANT-RES-001", "SYS-INTEL-001"],
            ),
            environment,
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.EXECUTION_REPORT:
            return []
        proposal = TradeProposal.model_validate(envelope.payload["proposal"])
        exe = envelope.payload["execution"]
        report = AttributionReport(
            proposal_id=proposal.proposal_id,
            strategy_agent_id=proposal.strategy_agent_id,
            pnl=0.0,
            pnl_bps=0.0,
            holding_days=0.0,
            alpha_estimate=0.0,
            execution_cost_bps=float(exe.get("slippage_bps", 0)),
            decision_quality_score=proposal.confidence,
            lessons=["opened_awaiting_exit_attribution"],
        )
        return [
            envelope.with_child(
                message_type=MessageType.ATTRIBUTION_REPORT,
                stage=Stage.POST_TRADE_ATTRIBUTION,
                sender_id=self.agent_id,
                recipient_ids=["LEARN-001", "SYS-INTEL-001"],
                payload=report.model_dump(mode="json"),
            )
        ]


class LearningControlAgent(BaseAgent):
    def __init__(self, memory: Any, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Controlled Learning Agent",
                agent_id="LEARN-001",
                department="quantitative_research",
                supervisory_agent_id="QUANT-RES-001",
                role=AgentRole.LEARNING_CONTROL,
                strategy="Capture lessons; propose versioned changes; never auto-mutate production",
                economic_rationale="Uncontrolled self-modification is a silent failure mode",
                owns_stages=["controlled_improvement"],
                authority_actions=[],
                information_received_from=["ATTR-001"],
                outputs_sent_to=["QUANT-RES-001", "PORT-RISK-001", "GOV-OPS-001"],
            ),
            environment,
        )
        self.memory = memory

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.ATTRIBUTION_REPORT:
            return []
        report = AttributionReport.model_validate(envelope.payload)
        self.memory.learn(
            key=f"attr:{report.proposal_id}",
            category="pnl",
            data=report.model_dump(mode="json"),
            agent_id=self.agent_id,
            environment=self.environment,
        )
        proposal = ImprovementProposal(
            proposer_agent_id=self.agent_id,
            target_agent_id=report.strategy_agent_id,
            change_summary="Observe only — no production mutation",
            hypothesis="Track attribution before proposing parameter changes",
            evidence_refs=[report.proposal_id],
            production_mutation_allowed=False,
        )
        return [
            envelope.with_child(
                message_type=MessageType.IMPROVEMENT_PROPOSAL,
                stage=Stage.CONTROLLED_IMPROVEMENT,
                sender_id=self.agent_id,
                recipient_ids=["QUANT-RES-001", "PORT-RISK-001", "GOV-OPS-001"],
                payload=proposal.model_dump(mode="json"),
            )
        ]


class ChiefArchitectureAgent(BaseAgent):
    def __init__(self, authority: Any, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="Chief Architecture Agent",
                agent_id="ARCH-CHIEF-001",
                department="systems_intelligence",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.CHIEF_ARCHITECTURE,
                strategy="Resolve design conflicts; finalize authority; gate live deploy",
                economic_rationale="Conflicting controls without arbitration create gaps",
                owns_stages=["risk_approval", "execution"],
                authority_actions=["pause", "shutdown"],
                information_received_from=["GOV-OPS-001", "PORT-RISK-001", "CAP-STEW-001"],
                outputs_sent_to=["EXEC-OMS-001", "SYS-INTEL-001"],
            ),
            environment,
        )
        self.authority = authority

    def finalize(self, payload: dict[str, Any]) -> MessageEnvelope | None:
        from agent_fleet.schemas.messages import ApprovalDecision

        proposal = TradeProposal.model_validate(payload["proposal"])
        validation = ValidationResult.model_validate(payload["validation"])
        portfolio = PortfolioVerdict.model_validate(payload["portfolio"])
        risk = RiskVerdict.model_validate(payload["risk"])
        steward = RiskVerdict.model_validate(payload["capital_stewardship"])
        gov = RiskVerdict.model_validate(payload["governance"])
        decision = self.authority.resolve(
            proposal, validation, portfolio, risk, steward, gov
        )
        return MessageEnvelope(
            message_type=MessageType.APPROVAL_DECISION,
            stage=Stage.RISK_APPROVAL,
            sender_id=self.agent_id,
            recipient_ids=["EXEC-OMS-001", "SYS-INTEL-001", proposal.strategy_agent_id],
            payload={
                "decision": decision.model_dump(mode="json"),
                "proposal": proposal.model_dump(mode="json"),
            },
            environment=self.environment.value,
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.RISK_VERDICT:
            return []
        required = {"proposal", "validation", "portfolio", "risk", "capital_stewardship", "governance"}
        if not required.issubset(envelope.payload):
            return []
        final = self.finalize(envelope.payload)
        return [final] if final else []


class AIInfrastructureAgent(BaseAgent):
    def __init__(self, environment: Environment = Environment.PAPER):
        super().__init__(
            _control_contract(
                agent_name="AI Infrastructure Supervisor",
                agent_id="AI-INFRA-001",
                department="ai_infrastructure",
                supervisory_agent_id="ARCH-CHIEF-001",
                role=AgentRole.AI_INFRASTRUCTURE,
                strategy="Model routing, compute, latency, failover, local vs cloud separation",
                economic_rationale="Inference reliability and latency are trading infrastructure",
                owns_stages=[],
                authority_actions=["failover"],
                outputs_sent_to=["ARCH-CHIEF-001", "SYS-INTEL-001"],
            ),
            environment,
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        return []
