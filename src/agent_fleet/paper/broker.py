"""Paper broker — simulated fills only. Live execution permanently gated here too."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from agent_fleet import LIVE_EXECUTION_ENABLED
from agent_fleet.schemas.messages import ApprovalDecision, ExecutionReport, TradeProposal
from agent_fleet.schemas.enums import Side


@dataclass
class PaperPosition:
    proposal_id: str
    strategy_agent_id: str
    symbol: str
    side: Side
    qty: float
    avg_price: float
    stop_loss: float
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PaperBroker:
    nav_usd: float = 1_000_000.0
    cash_usd: float = 1_000_000.0
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    slippage_bps_default: float = 5.0
    live_execution_enabled: bool = False
    execution_agent_id: str = "EXEC-1"

    def __post_init__(self) -> None:
        if self.live_execution_enabled or LIVE_EXECUTION_ENABLED:
            raise PermissionError(
                "Live execution is disabled until explicit Phase-5+ authorization"
            )

    def execute(self, proposal: TradeProposal, decision: ApprovalDecision) -> ExecutionReport:
        if not decision.execution_authorized:
            return ExecutionReport(
                proposal_id=proposal.proposal_id,
                execution_agent_id=self.execution_agent_id,
                symbol=proposal.symbol,
                side=proposal.side,
                requested_qty=0,
                filled_qty=0,
                avg_price=0,
                slippage_bps=0,
                status="rejected",
                paper=True,
            )
        size_pct = decision.final_size_pct_nav or 0.0
        if decision.final_size_usd is not None and decision.final_size_usd > 0:
            notional = float(decision.final_size_usd)
        else:
            notional = self.nav_usd * (size_pct / 100.0)
        price = proposal.entry_price_target
        slip = min(self.slippage_bps_default, proposal.max_slippage_bps)
        if proposal.side in {Side.BUY, Side.COVER}:
            fill_price = price * (1 + slip / 10_000)
        else:
            fill_price = price * (1 - slip / 10_000)
        qty = 0.0 if fill_price == 0 else notional / fill_price
        self.cash_usd -= notional if proposal.side in {Side.BUY, Side.COVER} else -notional
        self.positions[proposal.proposal_id] = PaperPosition(
            proposal_id=proposal.proposal_id,
            strategy_agent_id=proposal.strategy_agent_id,
            symbol=proposal.symbol,
            side=proposal.side,
            qty=qty,
            avg_price=fill_price,
            stop_loss=proposal.stop_loss,
        )
        return ExecutionReport(
            proposal_id=proposal.proposal_id,
            execution_agent_id=self.execution_agent_id,
            symbol=proposal.symbol,
            side=proposal.side,
            requested_qty=qty,
            filled_qty=qty,
            avg_price=fill_price,
            slippage_bps=slip,
            status="filled",
            paper=True,
        )
