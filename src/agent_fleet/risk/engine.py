"""Risk limits and evaluation helpers (BlackRock / Citadel controls)."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_fleet.messaging.schemas import DecisionAction, TradeProposalPayload


@dataclass
class PortfolioState:
    nav: float = 100_000.0
    cash: float = 100_000.0
    positions: dict[str, float] = field(default_factory=dict)  # symbol -> qty
    prices: dict[str, float] = field(default_factory=dict)
    sector_exposure_pct: dict[str, float] = field(default_factory=dict)
    strategy_gross_pct: dict[str, float] = field(default_factory=dict)
    daily_pnl_pct: float = 0.0
    drawdown_pct: float = 0.0
    halted: bool = False


@dataclass
class RiskLimits:
    max_position_pct_nav: float = 0.05
    max_risk_per_trade_pct_nav: float = 0.005
    max_gross_exposure_pct_nav: float = 1.0
    max_net_exposure_pct_nav: float = 0.6
    max_sector_pct_nav: float = 0.25
    max_strategy_pct_nav: float = 0.30
    max_daily_loss_pct_nav: float = 0.02
    max_drawdown_pct_nav: float = 0.10
    max_correlated_group_pct_nav: float = 0.35
    min_cash_pct_nav: float = 0.05


@dataclass
class RiskVerdict:
    action: DecisionAction
    approved_quantity: float | None
    reasons: list[str]
    constraints_applied: list[str]
    veto: bool = False


def gross_exposure_pct(state: PortfolioState) -> float:
    if state.nav <= 0:
        return 0.0
    gross = 0.0
    for sym, qty in state.positions.items():
        px = state.prices.get(sym, 0.0)
        gross += abs(qty * px)
    return gross / state.nav


def evaluate_proposal(
    proposal: TradeProposalPayload,
    state: PortfolioState,
    limits: RiskLimits,
    price: float,
    sector: str | None = None,
    stop_distance_pct: float | None = None,
) -> RiskVerdict:
    reasons: list[str] = []
    constraints: list[str] = []

    if state.halted:
        return RiskVerdict(
            action=DecisionAction.REJECT,
            approved_quantity=None,
            reasons=["Portfolio halted"],
            constraints_applied=["emergency_halt"],
            veto=True,
        )

    if state.drawdown_pct >= limits.max_drawdown_pct_nav:
        return RiskVerdict(
            action=DecisionAction.REJECT,
            approved_quantity=None,
            reasons=[f"Drawdown {state.drawdown_pct:.2%} >= limit {limits.max_drawdown_pct_nav:.2%}"],
            constraints_applied=["max_drawdown"],
            veto=True,
        )

    if abs(state.daily_pnl_pct) >= limits.max_daily_loss_pct_nav and state.daily_pnl_pct < 0:
        return RiskVerdict(
            action=DecisionAction.PAUSE,
            approved_quantity=None,
            reasons=["Daily loss limit breached"],
            constraints_applied=["max_daily_loss"],
            veto=True,
        )

    # Size by risk-per-trade if stop known, else by max position
    risk_pct = proposal.risk_per_trade_pct_nav_request or limits.max_risk_per_trade_pct_nav
    risk_pct = min(risk_pct, limits.max_risk_per_trade_pct_nav)
    constraints.append("max_risk_per_trade")

    if stop_distance_pct and stop_distance_pct > 0:
        dollar_risk = state.nav * risk_pct
        qty = dollar_risk / (price * stop_distance_pct)
    else:
        qty = (state.nav * limits.max_position_pct_nav) / price
        constraints.append("max_position_fallback")

    max_qty_by_position = (state.nav * limits.max_position_pct_nav) / price
    if qty > max_qty_by_position:
        qty = max_qty_by_position
        constraints.append("max_position_pct_nav")
        reasons.append("Quantity reduced to max position limit")

    # Gross exposure check
    incremental = abs(qty * price) / state.nav
    if gross_exposure_pct(state) + incremental > limits.max_gross_exposure_pct_nav:
        # try reduce
        room = limits.max_gross_exposure_pct_nav - gross_exposure_pct(state)
        if room <= 0:
            return RiskVerdict(
                action=DecisionAction.REJECT,
                approved_quantity=None,
                reasons=["Gross exposure limit reached"],
                constraints_applied=constraints + ["max_gross_exposure"],
                veto=False,
            )
        qty = (room * state.nav) / price
        constraints.append("max_gross_exposure_reduce")
        reasons.append("Quantity reduced for gross exposure")

    if sector:
        sec_pct = state.sector_exposure_pct.get(sector, 0.0) + incremental
        if sec_pct > limits.max_sector_pct_nav:
            return RiskVerdict(
                action=DecisionAction.REJECT,
                approved_quantity=None,
                reasons=[f"Sector {sector} exposure would exceed limit"],
                constraints_applied=constraints + ["max_sector"],
                veto=False,
            )

    strat_pct = state.strategy_gross_pct.get(proposal.strategy_agent_id, 0.0) + incremental
    if strat_pct > limits.max_strategy_pct_nav:
        return RiskVerdict(
            action=DecisionAction.REDUCE,
            approved_quantity=max(
                0.0,
                (limits.max_strategy_pct_nav - state.strategy_gross_pct.get(proposal.strategy_agent_id, 0.0))
                * state.nav
                / price,
            ),
            reasons=["Strategy allocation cap applied"],
            constraints_applied=constraints + ["max_strategy_pct_nav"],
            veto=False,
        )

    cash_pct = state.cash / state.nav
    if cash_pct - incremental < limits.min_cash_pct_nav:
        return RiskVerdict(
            action=DecisionAction.REJECT,
            approved_quantity=None,
            reasons=["Insufficient cash buffer"],
            constraints_applied=constraints + ["min_cash"],
            veto=False,
        )

    if qty <= 0:
        return RiskVerdict(
            action=DecisionAction.REJECT,
            approved_quantity=None,
            reasons=["Computed quantity <= 0"],
            constraints_applied=constraints,
            veto=False,
        )

    return RiskVerdict(
        action=DecisionAction.APPROVE,
        approved_quantity=round(qty, 4),
        reasons=reasons or ["Within all risk limits"],
        constraints_applied=constraints,
        veto=False,
    )
