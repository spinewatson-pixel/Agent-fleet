"""End-to-end institutional operating chain for paper trading."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent_fleet.agents.institutional import (
    AIInfrastructureAgent,
    AttributionAgent,
    CapitalStewardshipAgent,
    ChiefArchitectureAgent,
    ExecutionAgent,
    FundamentalResearchAgent,
    GovernanceAgent,
    LearningControlAgent,
    MarketInformationAgent,
    MonitoringAgent,
    PortfolioRiskAgent,
    QuantResearchAgent,
    SystemsIntelligenceAgent,
    TradingOperationsAgent,
)
from agent_fleet.agents.strategy import StrategyAgent, all_strategy_agents
from agent_fleet.core.authority import AuthorityResolver
from agent_fleet.core.bus import MessageBus
from agent_fleet.core.events import EventStore
from agent_fleet.core.memory import MemoryStore
from agent_fleet.paper.broker import PaperBroker
from agent_fleet.schemas.enums import Environment, MessageType, Side, Stage
from agent_fleet.schemas.messages import MarketEvent, MessageEnvelope


@dataclass
class Organization:
    """Fully wired paper-trading organization."""

    environment: Environment = Environment.PAPER
    nav_usd: float = 1_000_000.0
    live_execution_enabled: bool = False

    event_store: EventStore = field(default_factory=EventStore)
    memory: MemoryStore = field(default_factory=MemoryStore)
    bus: MessageBus | None = None
    authority: AuthorityResolver | None = None
    broker: PaperBroker | None = None

    agents: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.live_execution_enabled:
            raise PermissionError("Live execution remains disabled for this organization")
        self.authority = AuthorityResolver(live_execution_enabled=False)
        self.broker = PaperBroker(
            nav_usd=self.nav_usd,
            cash_usd=self.nav_usd,
            execution_agent_id="EXEC-OMS-001",
        )
        self.bus = MessageBus(event_store=self.event_store)

        # Institutional layer
        self.agents["MKT-INFO-001"] = MarketInformationAgent(self.environment)
        self.agents["FUND-RES-001"] = FundamentalResearchAgent(self.environment)
        self.agents["QUANT-RES-001"] = QuantResearchAgent(self.environment)
        self.agents["VAL-IND-001"] = self.agents.get("VAL-IND-001")
        from agent_fleet.agents.institutional import IndependentValidatorAgent

        self.agents["VAL-IND-001"] = IndependentValidatorAgent(self.environment)
        self.agents["PORT-RISK-001"] = PortfolioRiskAgent(self.environment)
        self.agents["CAP-STEW-001"] = CapitalStewardshipAgent(self.environment)
        self.agents["GOV-OPS-001"] = GovernanceAgent(self.environment)
        self.agents["SYS-INTEL-001"] = SystemsIntelligenceAgent(self.environment)
        self.agents["TRADE-OPS-001"] = TradingOperationsAgent(self.environment)
        self.agents["AI-INFRA-001"] = AIInfrastructureAgent(self.environment)
        self.agents["ARCH-CHIEF-001"] = ChiefArchitectureAgent(self.authority, self.environment)
        self.agents["EXEC-OMS-001"] = ExecutionAgent(self.broker, self.environment)
        self.agents["MON-LIVE-001"] = MonitoringAgent(self.environment)
        self.agents["ATTR-001"] = AttributionAgent(self.environment)
        self.agents["LEARN-001"] = LearningControlAgent(self.memory, self.environment)

        # Strategy layer
        self.agents.update(all_strategy_agents(self.environment))

        # Send permissions: strategies may only emit trade proposals / not approvals
        for aid, agent in self.agents.items():
            if aid.startswith("STRAT-"):
                self.bus.set_send_permission(aid, {MessageType.TRADE_PROPOSAL.value})
            elif aid == "EXEC-OMS-001":
                self.bus.set_send_permission(aid, {MessageType.EXECUTION_REPORT.value})
            elif aid == "MKT-INFO-001":
                self.bus.set_send_permission(
                    aid, {MessageType.MARKET_EVENT.value}
                )

    def route(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        """Synchronously push a message through owning agents and collect outputs."""
        out: list[MessageEnvelope] = []
        queue = [envelope]
        seen = 0
        while queue and seen < 100:
            current = queue.pop(0)
            seen += 1
            self.bus.publish(current)
            for recipient in current.recipient_ids:
                agent = self.agents.get(recipient)
                if agent is None:
                    continue
                produced = agent.handle(current)
                for msg in produced:
                    if msg.message_type == MessageType.EXECUTION_REPORT:
                        decision_size = float(
                            current.payload.get("decision", {}).get("final_size_pct_nav") or 0
                        )
                        proposal = msg.payload.get("proposal", {})
                        risk_agent = self.agents.get("PORT-RISK-001")
                        if risk_agent and decision_size > 0:
                            risk_agent.commit_exposure(
                                proposal.get("strategy_agent_id", "unknown"),
                                proposal.get("symbol", "unknown"),
                                decision_size,
                            )
                out.extend(produced)
                queue.extend(produced)
        return out

    def ingest_market_event(
        self,
        *,
        symbol: str,
        price: float,
        bias: str = "long",
        conviction: float = 0.7,
        event_type: str = "bar",
        source: str = "paper_feed",
        strategy_hint: str | None = None,
    ) -> dict[str, Any]:
        """Drive one event through the full operating chain."""
        event = MarketEvent(
            symbol=symbol,
            event_type=event_type,
            source=source,
            source_verified=True,
            timestamp=datetime.now(timezone.utc),
            tags=[event_type, symbol],
            normalized={
                "price": price,
                "close": price,
                "ATR_14": price * 0.02,
                "bias": bias,
                "conviction": conviction,
                "expected_edge_bps": 45,
                "suggested_size_pct_nav": 1.5,
                "confidence": conviction,
            },
            confidence=1.0,
        )
        envelope = MessageEnvelope(
            message_type=MessageType.MARKET_EVENT,
            stage=Stage.DATA_INGESTION,
            sender_id="MKT-INFO-001",
            recipient_ids=["MKT-INFO-001"],
            payload=event.model_dump(mode="json"),
            environment=self.environment.value,
        )
        # Inject strategy targeting via research recipients if requested
        results = self.route(envelope)

        # If strategy_hint provided, also directly feed that strategy a research signal path
        if strategy_hint and strategy_hint in self.agents:
            from agent_fleet.schemas.messages import ResearchSignal
            from agent_fleet.schemas.enums import MarketRegime

            signal = ResearchSignal(
                research_agent_id="FUND-RES-001",
                symbol=symbol,
                thesis=f"Targeted paper signal for {strategy_hint}",
                direction=Side.BUY if bias == "long" else Side.SELL,
                conviction=conviction,
                horizon_days=20,
                regime_context=[MarketRegime.TRENDING_BULL],
                features={
                    "close": price,
                    "price": price,
                    "ATR_14": price * 0.02,
                    "confidence": conviction,
                    "expected_edge_bps": 45,
                    "suggested_size_pct_nav": 1.5,
                    "force_setup": self.agents[strategy_hint].contract.setup_detection_rules[0].rule_id,
                },
            )
            strat_env = MessageEnvelope(
                message_type=MessageType.RESEARCH_SIGNAL,
                stage=Stage.SIGNAL_GENERATION,
                sender_id="FUND-RES-001",
                recipient_ids=[strategy_hint],
                payload=signal.model_dump(mode="json"),
                environment=self.environment.value,
            )
            results.extend(self.route(strat_env))

        fills = [
            r for r in results if r.message_type == MessageType.EXECUTION_REPORT
        ]
        decisions = [
            r for r in results if r.message_type == MessageType.APPROVAL_DECISION
        ]
        return {
            "messages": len(results),
            "fills": len(fills),
            "decisions": [d.payload.get("decision", {}) for d in decisions],
            "positions": list(self.broker.positions.keys()) if self.broker else [],
            "audit_events": len(self.event_store.events),
            "lineage_sample": fills[-1].lineage if fills else [],
        }

    def contracts(self) -> dict[str, Any]:
        return {aid: agent.contract.model_dump(mode="json") for aid, agent in self.agents.items()}

    def authority_map(self) -> dict[str, Any]:
        return {
            "veto_agents": sorted(self.authority.veto_agents),
            "approval_chain": list(self.authority.chain),
            "live_execution_enabled": False,
            "strategy_restrictions": {
                "may_approve_self": False,
                "may_execute": False,
                "may_set_capital_limits": False,
                "may_evaluate_own_performance": False,
            },
        }
