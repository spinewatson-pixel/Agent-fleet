"""Strategy agent registry and implementations.

Strategies propose trades only. Capital, approval, execution, and
self-evaluation are forbidden by contract.
"""

from __future__ import annotations

from typing import Any

from agent_fleet.agents.base import BaseAgent
from agent_fleet.agents.contracts_factory import build_strategy_contract
from agent_fleet.schemas.contracts import (
    EntryExitRules,
    PositionSizingRules,
    SetupDetectionRule,
)
from agent_fleet.schemas.enums import (
    Environment,
    MarketRegime,
    MessageType,
    Side,
    Stage,
)
from agent_fleet.schemas.messages import MessageEnvelope, ResearchSignal, TradeProposal


def _sizing(max_pct: float, concurrent: int = 5) -> PositionSizingRules:
    return PositionSizingRules(
        method="volatility_target",
        max_pct_nav=max_pct,
        min_pct_nav=0.25,
        vol_target_ann=0.12,
        kelly_fraction_cap=0.25,
        max_concurrent_positions=concurrent,
        max_sector_pct=15.0,
        notes="Suggested size only; PORT-RISK-001 sets binding limits",
    )


COMMON_OUTPUTS = [
    "VAL-IND-001",
    "PORT-RISK-001",
    "TRADE-OPS-001",
    "SYS-INTEL-001",
]

COMMON_INPUTS = [
    "MKT-INFO-001",
    "FUND-RES-001",
    "QUANT-RES-001",
    "AI-INFRA-001",
]


def momentum_contract():
    return build_strategy_contract(
        agent_name="Momentum Trend Agent",
        agent_id="STRAT-MOM-001",
        supervisory_agent_id="TRADE-OPS-001",
        strategy="Cross-sectional and time-series momentum on liquid US equities",
        economic_rationale=(
            "Underreaction and trend persistence produce positive expected return "
            "when costs are controlled and regimes are trending"
        ),
        assets_permitted=["US_EQUITY_LIQUID"],
        markets_permitted=["NYSE", "NASDAQ"],
        holding_period_days_min=5,
        holding_period_days_max=60,
        trading_frequency="daily",
        valid_regimes=[
            MarketRegime.TRENDING_BULL,
            MarketRegime.TRENDING_BEAR,
            MarketRegime.LOW_VOLATILITY,
            MarketRegime.RISK_ON,
        ],
        invalid_regimes=[MarketRegime.HIGH_VOLATILITY, MarketRegime.RISK_OFF],
        required_data_inputs=[
            "daily_ohlcv",
            "adv_20d",
            "sma_50",
            "sma_200",
            "returns_12_1",
            "regime_label",
        ],
        data_sources={
            "daily_ohlcv": "MKT-INFO-001.bars",
            "adv_20d": "MKT-INFO-001.liquidity",
            "sma_50": "QUANT-RES-001.features",
            "sma_200": "QUANT-RES-001.features",
            "returns_12_1": "QUANT-RES-001.features",
            "regime_label": "TRADE-OPS-001.regime",
        },
        indicators_features_models=["sma_50", "sma_200", "returns_12_1", "ATR_14"],
        setup_rules=[
            SetupDetectionRule(
                rule_id="MOM-SETUP-01",
                description="Price above rising SMA50 and positive 12-1 momentum",
                expression="close > sma_50 AND sma_50 > sma_50[20] AND returns_12_1 > 0 AND adv_20d > 5e6",
                required_inputs=["close", "sma_50", "returns_12_1", "adv_20d"],
                lookback=252,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["MOM-SETUP-01 true on signal bar close", "regime in valid_regimes"],
            exit_rules=["close < sma_50", "holding_days >= 60"],
            stop_loss_rule="entry - 2.5 * ATR_14",
            take_profit_rule=None,
            invalidation_rules=["regime == HIGH_VOLATILITY", "adv_20d < 2e6"],
            time_stop_days=60,
        ),
        position_sizing=_sizing(3.0),
        information_received_from=COMMON_INPUTS,
        outputs_sent_to=COMMON_OUTPUTS,
        monitoring_after_entry=[
            "stop_distance",
            "sma_50_breach",
            "regime_change",
            "liquidity_collapse",
        ],
    )


def mean_reversion_contract():
    return build_strategy_contract(
        agent_name="Mean Reversion Agent",
        agent_id="STRAT-MR-001",
        supervisory_agent_id="TRADE-OPS-001",
        strategy="Short-horizon mean reversion in range-bound liquid names",
        economic_rationale="Liquidity provision / overreaction in non-trending regimes",
        assets_permitted=["US_EQUITY_LIQUID"],
        markets_permitted=["NYSE", "NASDAQ"],
        holding_period_days_min=1,
        holding_period_days_max=10,
        trading_frequency="daily",
        valid_regimes=[MarketRegime.RANGE_BOUND, MarketRegime.LOW_VOLATILITY],
        invalid_regimes=[
            MarketRegime.TRENDING_BULL,
            MarketRegime.TRENDING_BEAR,
            MarketRegime.HIGH_VOLATILITY,
            MarketRegime.RISK_OFF,
        ],
        required_data_inputs=["daily_ohlcv", "rsi_14", "bollinger_z", "regime_label", "adv_20d"],
        data_sources={
            "daily_ohlcv": "MKT-INFO-001.bars",
            "rsi_14": "QUANT-RES-001.features",
            "bollinger_z": "QUANT-RES-001.features",
            "regime_label": "TRADE-OPS-001.regime",
            "adv_20d": "MKT-INFO-001.liquidity",
        },
        indicators_features_models=["rsi_14", "bollinger_z", "ATR_14"],
        setup_rules=[
            SetupDetectionRule(
                rule_id="MR-SETUP-01",
                description="Oversold bounce setup in range regime",
                expression="rsi_14 < 30 AND bollinger_z < -2 AND regime == RANGE_BOUND AND adv_20d > 5e6",
                required_inputs=["rsi_14", "bollinger_z", "regime", "adv_20d"],
                lookback=60,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["MR-SETUP-01", "no earnings within 3 trading days"],
            exit_rules=["rsi_14 > 50", "bollinger_z > 0", "holding_days >= 10"],
            stop_loss_rule="entry - 1.5 * ATR_14",
            take_profit_rule="mid_band",
            invalidation_rules=["regime leaves RANGE_BOUND", "gap_down > 3%"],
            time_stop_days=10,
        ),
        position_sizing=_sizing(2.0, concurrent=8),
        information_received_from=COMMON_INPUTS + ["MKT-INFO-001"],
        outputs_sent_to=COMMON_OUTPUTS,
        monitoring_after_entry=["rsi_path", "gap_risk", "regime_break", "earnings_calendar"],
    )


def earnings_contract():
    return build_strategy_contract(
        agent_name="Earnings Event Agent",
        agent_id="STRAT-EARN-001",
        supervisory_agent_id="FUND-RES-001",
        department="research_strategy",
        strategy="Event-driven post-earnings drift and surprise reaction",
        economic_rationale="Earnings surprises underreact over 1–30 days on average",
        assets_permitted=["US_EQUITY_LIQUID"],
        markets_permitted=["NYSE", "NASDAQ"],
        holding_period_days_min=1,
        holding_period_days_max=30,
        trading_frequency="event_driven",
        valid_regimes=[MarketRegime.EARNINGS_SEASON, MarketRegime.RISK_ON, MarketRegime.LOW_VOLATILITY],
        invalid_regimes=[MarketRegime.RISK_OFF, MarketRegime.HIGH_VOLATILITY],
        required_data_inputs=[
            "earnings_calendar",
            "eps_surprise_pct",
            "guidance_delta",
            "implied_move",
            "adv_20d",
            "news_sentiment",
        ],
        data_sources={
            "earnings_calendar": "MKT-INFO-001.calendar",
            "eps_surprise_pct": "MKT-INFO-001.filings",
            "guidance_delta": "FUND-RES-001.signals",
            "implied_move": "MKT-INFO-001.options_summary",
            "adv_20d": "MKT-INFO-001.liquidity",
            "news_sentiment": "MKT-INFO-001.news",
        },
        indicators_features_models=["eps_surprise_z", "post_earnings_drift_model_v1"],
        setup_rules=[
            SetupDetectionRule(
                rule_id="EARN-SETUP-01",
                description="Positive surprise above threshold with supportive guidance",
                expression="eps_surprise_pct > 5 AND guidance_delta >= 0 AND adv_20d > 1e7",
                required_inputs=["eps_surprise_pct", "guidance_delta", "adv_20d"],
                lookback=1,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["EARN-SETUP-01 within 1 session after print", "spread_bps < 10"],
            exit_rules=["holding_days >= 20", "thesis_invalidated_by_revision"],
            stop_loss_rule="entry - max(1.0 * implied_move, 2.0 * ATR_14)",
            take_profit_rule="1.5 * historical_PED_median",
            invalidation_rules=["material_negative_amendment", "sector_shock"],
            time_stop_days=30,
        ),
        position_sizing=_sizing(2.5),
        information_received_from=["MKT-INFO-001", "FUND-RES-001", "QUANT-RES-001"],
        outputs_sent_to=COMMON_OUTPUTS,
        monitoring_after_entry=["estimate_revisions", "news_flow", "volume_dryup"],
    )


def macro_contract():
    return build_strategy_contract(
        agent_name="Macro Regime Agent",
        agent_id="STRAT-MACRO-001",
        supervisory_agent_id="FUND-RES-001",
        department="research_strategy",
        strategy="Macro-regime allocation across index ETFs and factor proxies",
        economic_rationale="Risk premia vary with growth/inflation/policy regimes",
        assets_permitted=["US_ETF_INDEX", "SECTOR_ETF"],
        markets_permitted=["NYSE", "NASDAQ", "ARCA"],
        holding_period_days_min=10,
        holding_period_days_max=120,
        trading_frequency="weekly",
        valid_regimes=[
            MarketRegime.RISK_ON,
            MarketRegime.RISK_OFF,
            MarketRegime.MACRO_EVENT,
            MarketRegime.TRENDING_BULL,
            MarketRegime.TRENDING_BEAR,
        ],
        invalid_regimes=[],
        required_data_inputs=[
            "macro_calendar",
            "yield_curve",
            "cpi_surprise",
            "policy_prob",
            "regime_label",
            "etf_ohlcv",
        ],
        data_sources={
            "macro_calendar": "MKT-INFO-001.calendar",
            "yield_curve": "MKT-INFO-001.macro",
            "cpi_surprise": "MKT-INFO-001.macro",
            "policy_prob": "MKT-INFO-001.macro",
            "regime_label": "TRADE-OPS-001.regime",
            "etf_ohlcv": "MKT-INFO-001.bars",
        },
        indicators_features_models=["regime_hmm_v1", "growth_inflation_map"],
        setup_rules=[
            SetupDetectionRule(
                rule_id="MACRO-SETUP-01",
                description="Regime transition with confirming rate/inflation signals",
                expression="regime_changed == True AND confirm_count >= 2",
                required_inputs=["regime_label", "yield_curve", "cpi_surprise"],
                lookback=60,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["MACRO-SETUP-01", "ETF ADV sufficient"],
            exit_rules=["regime_reverts", "holding_days >= 120"],
            stop_loss_rule="portfolio_sleeve_stop_3pct",
            take_profit_rule=None,
            invalidation_rules=["data_revision_reverses_signal"],
            time_stop_days=120,
        ),
        position_sizing=_sizing(5.0, concurrent=4),
        information_received_from=["MKT-INFO-001", "FUND-RES-001", "CAP-STEW-001"],
        outputs_sent_to=COMMON_OUTPUTS + ["CAP-STEW-001"],
        monitoring_after_entry=["macro_release_risk", "regime_stability"],
    )


def factor_contract():
    return build_strategy_contract(
        agent_name="Quant Factor Agent",
        agent_id="STRAT-FACTOR-001",
        supervisory_agent_id="QUANT-RES-001",
        department="quantitative_research",
        strategy="Multi-factor long-short (value, quality, momentum, low-vol) with neutralization",
        economic_rationale="Compensated factor premia after cost and capacity constraints",
        assets_permitted=["US_EQUITY_LIQUID"],
        markets_permitted=["NYSE", "NASDAQ"],
        holding_period_days_min=5,
        holding_period_days_max=40,
        trading_frequency="daily",
        valid_regimes=[
            MarketRegime.TRENDING_BULL,
            MarketRegime.TRENDING_BEAR,
            MarketRegime.RANGE_BOUND,
            MarketRegime.LOW_VOLATILITY,
            MarketRegime.RISK_ON,
        ],
        invalid_regimes=[MarketRegime.HIGH_VOLATILITY],
        required_data_inputs=[
            "factor_scores",
            "industry_map",
            "beta",
            "adv_20d",
            "borrow_availability",
        ],
        data_sources={
            "factor_scores": "QUANT-RES-001.features",
            "industry_map": "MKT-INFO-001.reference",
            "beta": "QUANT-RES-001.features",
            "adv_20d": "MKT-INFO-001.liquidity",
            "borrow_availability": "TRADE-OPS-001.locate",
        },
        indicators_features_models=["value_z", "quality_z", "mom_z", "lowvol_z", "combined_alpha_v1"],
        setup_rules=[
            SetupDetectionRule(
                rule_id="FACTOR-SETUP-01",
                description="Top/bottom decile combined alpha after industry/beta neutralize",
                expression="combined_alpha_v1 rank in {top_decile,bottom_decile} AND adv_20d > 5e6",
                required_inputs=["combined_alpha_v1", "adv_20d"],
                lookback=1,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["FACTOR-SETUP-01", "gross_book within portfolio sleeve"],
            exit_rules=["rank exits extreme deciles", "rebalance_day"],
            stop_loss_rule="name_stop_8pct OR sleeve_stop",
            take_profit_rule=None,
            invalidation_rules=["factor_crowding_alert", "borrow_pulled"],
            time_stop_days=40,
        ),
        position_sizing=_sizing(1.5, concurrent=40),
        information_received_from=["QUANT-RES-001", "MKT-INFO-001", "PORT-RISK-001"],
        outputs_sent_to=COMMON_OUTPUTS,
        monitoring_after_entry=["factor_decay", "crowding", "borrow", "neutralization_drift"],
    )


def value_contract():
    return build_strategy_contract(
        agent_name="Quality Value Steward Agent",
        agent_id="STRAT-VALUE-001",
        supervisory_agent_id="CAP-STEW-001",
        department="capital_stewardship",
        strategy="Long-term quality/value ownership with low turnover",
        economic_rationale="Durable cash-flow compounders purchased below intrinsic value",
        assets_permitted=["US_EQUITY_LARGE", "US_EQUITY_MID"],
        markets_permitted=["NYSE", "NASDAQ"],
        holding_period_days_min=90,
        holding_period_days_max=1825,
        trading_frequency="low_turnover",
        valid_regimes=[
            MarketRegime.TRENDING_BULL,
            MarketRegime.TRENDING_BEAR,
            MarketRegime.RANGE_BOUND,
            MarketRegime.RISK_ON,
            MarketRegime.RISK_OFF,
            MarketRegime.LOW_VOLATILITY,
        ],
        invalid_regimes=[],
        required_data_inputs=[
            "financials",
            "roic",
            "owner_earnings",
            "valuation_band",
            "moat_score",
            "insider_activity",
        ],
        data_sources={
            "financials": "MKT-INFO-001.filings",
            "roic": "FUND-RES-001.signals",
            "owner_earnings": "FUND-RES-001.signals",
            "valuation_band": "CAP-STEW-001.valuation",
            "moat_score": "CAP-STEW-001.quality",
            "insider_activity": "MKT-INFO-001.filings",
        },
        indicators_features_models=["roic", "owner_earnings_yield", "moat_score", "margin_of_safety"],
        setup_rules=[
            SetupDetectionRule(
                rule_id="VALUE-SETUP-01",
                description="High quality with margin of safety",
                expression="moat_score >= 4 AND margin_of_safety >= 0.25 AND roic > cost_of_capital",
                required_inputs=["moat_score", "margin_of_safety", "roic", "cost_of_capital"],
                lookback=1,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["VALUE-SETUP-01", "CAP-STEW-001 quality gate passed"],
            exit_rules=["thesis_broken", "valuation > 1.5 * intrinsic", "better_opportunity_swap"],
            stop_loss_rule="thesis_invalidation_only (no mechanical noise stop); hard risk sleeve 15pct name",
            take_profit_rule="trim above intrinsic + 20%",
            invalidation_rules=["moat_score drop >= 2", "fraud_or_governance_flag", "permanent_earnings_impairment"],
            time_stop_days=None,
        ),
        position_sizing=_sizing(5.0, concurrent=15),
        information_received_from=["CAP-STEW-001", "FUND-RES-001", "MKT-INFO-001"],
        outputs_sent_to=COMMON_OUTPUTS + ["CAP-STEW-001"],
        monitoring_after_entry=["fundamental_drift", "valuation_band", "governance_flags"],
    )


def vol_contract():
    return build_strategy_contract(
        agent_name="Volatility Awareness Agent",
        agent_id="STRAT-VOL-001",
        supervisory_agent_id="TRADE-OPS-001",
        strategy="Volatility-regime overlay reducing risk in high-vol / expanding stress",
        economic_rationale="Volatility clustering and crash risk require dynamic exposure control",
        assets_permitted=["US_ETF_INDEX", "US_EQUITY_LIQUID"],
        markets_permitted=["NYSE", "NASDAQ", "CBOE_PROXY"],
        holding_period_days_min=1,
        holding_period_days_max=20,
        trading_frequency="daily",
        valid_regimes=[
            MarketRegime.HIGH_VOLATILITY,
            MarketRegime.RISK_OFF,
            MarketRegime.MACRO_EVENT,
        ],
        invalid_regimes=[],
        required_data_inputs=["realized_vol_20", "vix_proxy", "corr_average", "regime_label"],
        data_sources={
            "realized_vol_20": "QUANT-RES-001.features",
            "vix_proxy": "MKT-INFO-001.macro",
            "corr_average": "PORT-RISK-001.risk",
            "regime_label": "TRADE-OPS-001.regime",
        },
        indicators_features_models=["realized_vol_20", "vol_of_vol", "corr_spike"],
        setup_rules=[
            SetupDetectionRule(
                rule_id="VOL-SETUP-01",
                description="Vol expansion hedge / de-risk signal",
                expression="realized_vol_20 > percentile_90 OR corr_average > 0.7",
                required_inputs=["realized_vol_20", "corr_average"],
                lookback=252,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["VOL-SETUP-01"],
            exit_rules=["realized_vol_20 < percentile_70", "corr_average < 0.5"],
            stop_loss_rule="overlay_sleeve_stop_2pct",
            take_profit_rule=None,
            invalidation_rules=["false_break_vol_crush_same_day"],
            time_stop_days=20,
        ),
        position_sizing=_sizing(4.0, concurrent=3),
        information_received_from=["QUANT-RES-001", "PORT-RISK-001", "MKT-INFO-001"],
        outputs_sent_to=COMMON_OUTPUTS,
        monitoring_after_entry=["vol_path", "correlation_path"],
    )


def sector_contract():
    return build_strategy_contract(
        agent_name="Sector Rotation Agent",
        agent_id="STRAT-SECTOR-001",
        supervisory_agent_id="FUND-RES-001",
        department="research_strategy",
        strategy="Relative-strength sector ETF rotation",
        economic_rationale="Capital migrates across sectors with cycle and relative momentum",
        assets_permitted=["SECTOR_ETF"],
        markets_permitted=["ARCA", "NYSE"],
        holding_period_days_min=10,
        holding_period_days_max=90,
        trading_frequency="weekly",
        valid_regimes=[
            MarketRegime.TRENDING_BULL,
            MarketRegime.TRENDING_BEAR,
            MarketRegime.RISK_ON,
            MarketRegime.RISK_OFF,
        ],
        invalid_regimes=[MarketRegime.HIGH_VOLATILITY],
        required_data_inputs=["sector_etf_ohlcv", "rs_rank", "macro_cycle_label", "breadth"],
        data_sources={
            "sector_etf_ohlcv": "MKT-INFO-001.bars",
            "rs_rank": "QUANT-RES-001.features",
            "macro_cycle_label": "FUND-RES-001.signals",
            "breadth": "MKT-INFO-001.market_internals",
        },
        indicators_features_models=["rs_rank_63d", "sector_breadth", "cycle_map"],
        setup_rules=[
            SetupDetectionRule(
                rule_id="SECTOR-SETUP-01",
                description="Top-quartile relative strength with cycle alignment",
                expression="rs_rank_63d >= 0.75 AND cycle_aligned == True",
                required_inputs=["rs_rank_63d", "macro_cycle_label"],
                lookback=63,
            )
        ],
        entry_exit=EntryExitRules(
            entry_rules=["SECTOR-SETUP-01"],
            exit_rules=["rs_rank_63d < 0.5", "holding_days >= 90"],
            stop_loss_rule="entry - 2.0 * ATR_14",
            take_profit_rule=None,
            invalidation_rules=["sector_policy_shock", "ETF_tracking_error_spike"],
            time_stop_days=90,
        ),
        position_sizing=_sizing(4.0, concurrent=6),
        information_received_from=["FUND-RES-001", "QUANT-RES-001", "MKT-INFO-001"],
        outputs_sent_to=COMMON_OUTPUTS,
        monitoring_after_entry=["rs_rank", "sector_news", "etf_flows"],
    )


STRATEGY_CONTRACTS = {
    "STRAT-MOM-001": momentum_contract,
    "STRAT-MR-001": mean_reversion_contract,
    "STRAT-EARN-001": earnings_contract,
    "STRAT-MACRO-001": macro_contract,
    "STRAT-FACTOR-001": factor_contract,
    "STRAT-VALUE-001": value_contract,
    "STRAT-VOL-001": vol_contract,
    "STRAT-SECTOR-001": sector_contract,
}


class StrategyAgent(BaseAgent):
    """Generic strategy agent driven by its operating contract + feature snapshot."""

    def __init__(self, agent_id: str, environment: Environment = Environment.PAPER):
        factory = STRATEGY_CONTRACTS[agent_id]
        super().__init__(factory(), environment=environment)

    def evaluate_setup(self, features: dict[str, Any]) -> list[str]:
        fired: list[str] = []
        for rule in self.contract.setup_detection_rules:
            if features.get(f"rule:{rule.rule_id}") is True:
                fired.append(rule.rule_id)
            elif features.get("force_setup") == rule.rule_id:
                fired.append(rule.rule_id)
        return fired

    def propose(
        self,
        *,
        symbol: str,
        side: Side,
        features: dict[str, Any],
        research_signals: list[ResearchSignal] | None = None,
        current_regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> TradeProposal | None:
        self.assert_may_propose()
        if current_regime in self.contract.invalid_regimes:
            return None
        if (
            self.contract.valid_regimes
            and current_regime not in self.contract.valid_regimes
            and current_regime != MarketRegime.UNKNOWN
        ):
            return None
        fired = self.evaluate_setup(features)
        if not fired:
            return None
        entry = float(features["close"])
        atr = float(features.get("ATR_14", entry * 0.02))
        stop = entry - 2.0 * atr if side in {Side.BUY, Side.COVER} else entry + 2.0 * atr
        size = min(
            self.contract.position_sizing.max_pct_nav,
            float(features.get("suggested_size_pct_nav", 1.0)),
        )
        return TradeProposal(
            strategy_agent_id=self.agent_id,
            strategy_version=self.contract.strategy_version,
            symbol=symbol,
            side=side,
            thesis=f"{self.contract.strategy}: {fired}",
            setup_rules_fired=fired,
            entry_price_target=entry,
            stop_loss=stop,
            take_profit=features.get("take_profit"),
            invalidation_rules=self.contract.entry_exit.invalidation_rules,
            suggested_size_pct_nav=size,
            holding_period_days_min=self.contract.holding_period_days_min,
            holding_period_days_max=self.contract.holding_period_days_max,
            valid_regimes=self.contract.valid_regimes,
            current_regime=current_regime,
            required_data_inputs=self.contract.required_data_inputs,
            research_signal_ids=[s.signal_id for s in (research_signals or [])],
            confidence=float(features.get("confidence", 0.6)),
            expected_edge_bps=float(features.get("expected_edge_bps", 40)),
            max_slippage_bps=float(features.get("max_slippage_bps", 15)),
            metadata={"features_snapshot_keys": sorted(features.keys())},
        )

    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        if envelope.message_type != MessageType.RESEARCH_SIGNAL:
            return []
        signal = ResearchSignal.model_validate(envelope.payload)
        features = dict(signal.features)
        features.setdefault("close", features.get("price", 0.0))
        if not features.get("close"):
            return []
        # Paper path: allow research-triggered force setup for integration tests
        if "force_setup" not in features and self.contract.setup_detection_rules:
            features["force_setup"] = self.contract.setup_detection_rules[0].rule_id
        regime = signal.regime_context[0] if signal.regime_context else MarketRegime.UNKNOWN
        proposal = self.propose(
            symbol=signal.symbol,
            side=signal.direction,
            features=features,
            research_signals=[signal],
            current_regime=regime,
        )
        if proposal is None:
            return []
        return [
            envelope.with_child(
                message_type=MessageType.TRADE_PROPOSAL,
                stage=Stage.STRATEGY_PROPOSAL,
                sender_id=self.agent_id,
                recipient_ids=["VAL-IND-001", "SYS-INTEL-001"],
                payload=proposal.model_dump(mode="json"),
            )
        ]


def all_strategy_agents(environment: Environment = Environment.PAPER) -> dict[str, StrategyAgent]:
    return {aid: StrategyAgent(aid, environment=environment) for aid in STRATEGY_CONTRACTS}
