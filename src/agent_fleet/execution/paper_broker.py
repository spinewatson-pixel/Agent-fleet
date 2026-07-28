"""Paper broker — simulated fills only. Live path is hard-disabled."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_fleet import LIVE_EXECUTION_ENABLED
from agent_fleet.messaging.schemas import (
    ExecutionOrderPayload,
    FillReportPayload,
    OrderType,
    Side,
)


class LiveExecutionDisabledError(RuntimeError):
    pass


class PaperBroker:
    def __init__(self, default_slippage_bps: float = 5.0, fee_bps: float = 1.0) -> None:
        self.default_slippage_bps = default_slippage_bps
        self.fee_bps = fee_bps
        self.fills: list[FillReportPayload] = []

    def execute(self, order: ExecutionOrderPayload, last_price: float) -> FillReportPayload:
        if not order.paper or not LIVE_EXECUTION_ENABLED and not order.paper:
            # Always require paper=True while live disabled
            pass
        if not order.paper:
            raise LiveExecutionDisabledError(
                "Live execution is disabled until phase gates and explicit authorization"
            )

        px = order.limit_price if order.order_type == OrderType.LIMIT and order.limit_price else last_price
        # Adverse slippage model
        slip = self.default_slippage_bps / 10_000.0
        if order.side in {Side.BUY, Side.COVER}:
            fill_px = px * (1 + slip)
        else:
            fill_px = px * (1 - slip)

        notional = abs(order.quantity * fill_px)
        fees = notional * (self.fee_bps / 10_000.0)
        fill = FillReportPayload(
            order_id=order.order_id,
            fill_id=str(uuid4()),
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=round(fill_px, 6),
            fees=round(fees, 4),
            slippage_bps=self.default_slippage_bps,
            filled_at=datetime.now(timezone.utc),
            paper=True,
        )
        self.fills.append(fill)
        return fill
