"""Registry of all agent operating contracts for the organization."""

from __future__ import annotations

from agent_fleet.contracts.factory import infra_contract, strategy_contract
from agent_fleet.contracts.models import (
    AgentIOChannel,
    AgentOperatingContract,
    AgentRole,
    ApprovalAuthority,
    HoldingPeriod,
    MarketRegime,
    PositionSizingLimits,
    SetupRule,
)


def _sizing_default(**overrides: float) -> PositionSizingLimits:
    base = dict(
        method="volatility_target_with_risk_cap",
        max_position_pct_nav=0.05,
        max_risk_per_trade_pct_nav=0.005,
        max_gross_exposure_pct_nav=0.30,
        max_net_exposure_pct_nav=0.30,
        max_sector_pct_nav=0.15,
        max_correlated_group_pct_nav=0.20,
    )
    base.update(overrides)
    return PositionSizingLimits(**base)


def build_all_contracts() -> dict[str, AgentOperatingContract]:
    contracts: dict[str, AgentOperatingContract] = {}

    # --- Infrastructure / control plane ---
    contracts["SYS-ORCH-001"] = infra_contract(
        agent_name="Chief Architecture Orchestrator",
        agent_id="SYS-ORCH-001",
        department="Systems Intelligence",
        supervisor="GOV-COMP-001",
        role=AgentRole.ORCHESTRATION,
        rationale="Routes operating-chain messages, resolves conflicts, enforces contract bindings and audit lineage.",
        authorities=[
            ApprovalAuthority.PAUSE,
            ApprovalAuthority.VERSION_APPROVE,
            ApprovalAuthority.REJECT,
        ],
        inputs=[AgentIOChannel(agent_id="*", message_types=["*"], description="Org-wide")],
        outputs=[AgentIOChannel(agent_id="*", message_types=["governance_event", "alert"])],
    )

    contracts["DATA-MKT-001"] = infra_contract(
        agent_name="Market Data Ingestion",
        agent_id="DATA-MKT-001",
        department="Market Information",
        supervisor="SYS-ORCH-001",
        role=AgentRole.DATA,
        rationale="Ingest OHLCV, quotes, calendars; normalize timestamps/symbols; emit raw market_data.",
        authorities=[ApprovalAuthority.NONE],
        outputs=[
            AgentIOChannel(agent_id="DATA-VAL-001", message_types=["market_data"]),
        ],
    )

    contracts["DATA-NEWS-001"] = infra_contract(
        agent_name="News Filings Macro Ingestion",
        agent_id="DATA-NEWS-001",
        department="Market Information",
        supervisor="SYS-ORCH-001",
        role=AgentRole.DATA,
        rationale="Ingest news, filings, earnings, macro releases; tag symbols/topics; source-verify.",
        authorities=[ApprovalAuthority.NONE],
        outputs=[
            AgentIOChannel(agent_id="DATA-VAL-001", message_types=["news_event"]),
        ],
    )

    contracts["DATA-VAL-001"] = infra_contract(
        agent_name="Information Validation",
        agent_id="DATA-VAL-001",
        department="Market Information",
        supervisor="SYS-ORCH-001",
        role=AgentRole.DATA,
        rationale="Validate schema, staleness, outliers, source trust; emit data_validated or reject.",
        authorities=[ApprovalAuthority.REJECT],
        inputs=[
            AgentIOChannel(agent_id="DATA-MKT-001", message_types=["market_data"]),
            AgentIOChannel(agent_id="DATA-NEWS-001", message_types=["news_event"]),
        ],
        outputs=[
            AgentIOChannel(
                agent_id="*",
                message_types=["data_validated"],
                description="Fan-out to research and strategy",
            )
        ],
    )

    contracts["RSH-FUND-001"] = infra_contract(
        agent_name="Fundamental and Event Research",
        agent_id="RSH-FUND-001",
        department="Research and Strategy",
        supervisor="SYS-ORCH-001",
        role=AgentRole.RESEARCH,
        rationale="Convert filings/earnings/macro/thematic research into standardized research_note and signal messages.",
        authorities=[ApprovalAuthority.PROPOSE],
        outputs=[
            AgentIOChannel(agent_id="STRAT-EVT-001", message_types=["research_note", "signal"]),
            AgentIOChannel(agent_id="STRAT-QUAL-001", message_types=["research_note", "signal"]),
            AgentIOChannel(agent_id="STRAT-MACRO-001", message_types=["research_note", "signal"]),
            AgentIOChannel(agent_id="STRAT-SECROT-001", message_types=["signal"]),
        ],
    )

    contracts["RSH-QUANT-001"] = infra_contract(
        agent_name="Quantitative Research",
        agent_id="RSH-QUANT-001",
        department="Quantitative Research",
        supervisor="SYS-ORCH-001",
        role=AgentRole.RESEARCH,
        rationale="Hypothesis/feature generation, statistical validation; publish signals — never trade.",
        authorities=[ApprovalAuthority.PROPOSE],
        outputs=[
            AgentIOChannel(agent_id="STRAT-MOM-001", message_types=["signal"]),
            AgentIOChannel(agent_id="STRAT-MR-001", message_types=["signal"]),
            AgentIOChannel(agent_id="STRAT-PAIRS-001", message_types=["signal"]),
            AgentIOChannel(agent_id="LEARN-CTRL-001", message_types=["improvement_proposal"]),
        ],
    )

    contracts["SIG-VAL-001"] = infra_contract(
        agent_name="Independent Signal Validator",
        agent_id="SIG-VAL-001",
        department="Validation",
        supervisor="SYS-ORCH-001",
        role=AgentRole.VALIDATION,
        rationale="Independently validate trade proposals against contract rules, regime fit, and data quality.",
        authorities=[ApprovalAuthority.VALIDATE, ApprovalAuthority.REJECT],
        inputs=[AgentIOChannel(agent_id="*", message_types=["trade_proposal"])],
        outputs=[
            AgentIOChannel(agent_id="PORT-ALLOC-001", message_types=["validation_result"]),
        ],
    )

    contracts["PORT-ALLOC-001"] = infra_contract(
        agent_name="Portfolio Construction",
        agent_id="PORT-ALLOC-001",
        department="Portfolio and Risk",
        supervisor="RISK-APPR-001",
        role=AgentRole.PORTFOLIO,
        rationale="Size and accept/reduce/reject proposals for portfolio fit, correlation, liquidity, and allocation budgets.",
        authorities=[ApprovalAuthority.REDUCE, ApprovalAuthority.REJECT, ApprovalAuthority.APPROVE],
        outputs=[
            AgentIOChannel(agent_id="RISK-APPR-001", message_types=["portfolio_evaluation"]),
        ],
    )

    contracts["RISK-APPR-001"] = infra_contract(
        agent_name="Risk Approval",
        agent_id="RISK-APPR-001",
        department="Portfolio and Risk",
        supervisor="GOV-COMP-001",
        role=AgentRole.RISK,
        rationale="Independent risk approval with veto; enforces firm limits, stress, drawdown, and emergency halt.",
        authorities=[
            ApprovalAuthority.APPROVE,
            ApprovalAuthority.REJECT,
            ApprovalAuthority.REDUCE,
            ApprovalAuthority.PAUSE,
            ApprovalAuthority.CLOSE,
            ApprovalAuthority.EMERGENCY_HALT,
            ApprovalAuthority.VERSION_APPROVE,
        ],
        outputs=[
            AgentIOChannel(agent_id="CAP-STEW-001", message_types=["risk_decision"]),
            AgentIOChannel(agent_id="EXEC-PAPER-001", message_types=["risk_decision"]),
            AgentIOChannel(agent_id="*", message_types=["emergency_halt"]),
        ],
    )

    contracts["CAP-STEW-001"] = infra_contract(
        agent_name="Capital Stewardship",
        agent_id="CAP-STEW-001",
        department="Capital Stewardship",
        supervisor="GOV-COMP-001",
        role=AgentRole.CAPITAL_STEWARDSHIP,
        rationale="Challenge unnecessary activity and low-quality risk; veto short-termism that violates long-term capital quality.",
        authorities=[
            ApprovalAuthority.REJECT,
            ApprovalAuthority.REDUCE,
            ApprovalAuthority.APPROVE,
            ApprovalAuthority.PAUSE,
        ],
        outputs=[
            AgentIOChannel(agent_id="EXEC-PAPER-001", message_types=["capital_steward_decision"]),
        ],
    )

    contracts["EXEC-PAPER-001"] = infra_contract(
        agent_name="Paper Execution",
        agent_id="EXEC-PAPER-001",
        department="Trading Operations",
        supervisor="SYS-ORCH-001",
        role=AgentRole.EXECUTION,
        rationale="Execute only risk-and-steward authorized orders in paper environment; measure slippage.",
        authorities=[ApprovalAuthority.NONE],
        execution_permissions=["paper_execute_authorized_orders"],
        outputs=[
            AgentIOChannel(agent_id="MON-LIVE-001", message_types=["fill_report", "position_update"]),
            AgentIOChannel(agent_id="REV-ATTR-001", message_types=["fill_report"]),
        ],
    )

    from agent_fleet.contracts.models import DeploymentStatus as _DS

    contracts["EXEC-LIVE-001"] = infra_contract(
        agent_name="Live Execution (DISABLED)",
        agent_id="EXEC-LIVE-001",
        department="Trading Operations",
        supervisor="GOV-COMP-001",
        role=AgentRole.EXECUTION,
        rationale="Live broker gateway — HARD DISABLED until phase gates and explicit human authorization.",
        authorities=[ApprovalAuthority.NONE],
        execution_permissions=[],  # none until authorized
    )
    contracts["EXEC-LIVE-001"].testing_and_deployment_status = _DS.SHUTDOWN

    contracts["MON-LIVE-001"] = infra_contract(
        agent_name="Live Position Monitor",
        agent_id="MON-LIVE-001",
        department="Trading Operations",
        supervisor="RISK-APPR-001",
        role=AgentRole.MONITORING,
        rationale="Monitor open positions vs stops/invalidations; alert and request closes.",
        authorities=[ApprovalAuthority.PAUSE, ApprovalAuthority.CLOSE],
        outputs=[
            AgentIOChannel(agent_id="RISK-APPR-001", message_types=["alert"]),
            AgentIOChannel(agent_id="EXEC-PAPER-001", message_types=["execution_order"]),
        ],
    )

    contracts["MON-REGIME-001"] = infra_contract(
        agent_name="Market Regime Classifier",
        agent_id="MON-REGIME-001",
        department="Trading Operations",
        supervisor="SYS-ORCH-001",
        role=AgentRole.MONITORING,
        rationale="Classify regimes and gate strategy validity.",
        authorities=[ApprovalAuthority.PAUSE],
        outputs=[
            AgentIOChannel(agent_id="*", message_types=["alert"]),
        ],
    )

    contracts["REV-ATTR-001"] = infra_contract(
        agent_name="Post-Trade Attribution",
        agent_id="REV-ATTR-001",
        department="Review",
        supervisor="SYS-ORCH-001",
        role=AgentRole.ATTRIBUTION,
        rationale="Attribute PnL to signal, timing, sizing, execution; feed controlled learning — does not approve trades.",
        authorities=[ApprovalAuthority.PROPOSE],
        outputs=[
            AgentIOChannel(agent_id="LEARN-CTRL-001", message_types=["attribution_report"]),
            AgentIOChannel(agent_id="GOV-COMP-001", message_types=["attribution_report"]),
        ],
    )

    contracts["LEARN-CTRL-001"] = infra_contract(
        agent_name="Controlled Learning Governor",
        agent_id="LEARN-CTRL-001",
        department="Learning",
        supervisor="GOV-COMP-001",
        role=AgentRole.LEARNING,
        rationale="Enforce learning state machine; experimental env isolation; no unilateral production mutation.",
        authorities=[ApprovalAuthority.PROPOSE, ApprovalAuthority.REJECT],
        outputs=[
            AgentIOChannel(agent_id="RISK-APPR-001", message_types=["improvement_proposal"]),
            AgentIOChannel(agent_id="GOV-COMP-001", message_types=["improvement_proposal"]),
        ],
    )

    contracts["GOV-COMP-001"] = infra_contract(
        agent_name="Governance Compliance Operations",
        agent_id="GOV-COMP-001",
        department="Governance and Operations",
        supervisor="GOV-COMP-001",
        role=AgentRole.GOVERNANCE,
        rationale="Permissions, reconciliation, incidents, escalation, documentation, deployment authority.",
        authorities=[
            ApprovalAuthority.APPROVE,
            ApprovalAuthority.REJECT,
            ApprovalAuthority.PAUSE,
            ApprovalAuthority.EMERGENCY_HALT,
            ApprovalAuthority.VERSION_APPROVE,
        ],
    )

    contracts["AI-INFRA-001"] = infra_contract(
        agent_name="AI Infrastructure Router",
        agent_id="AI-INFRA-001",
        department="AI Infrastructure",
        supervisor="SYS-ORCH-001",
        role=AgentRole.INFRASTRUCTURE,
        rationale="Model routing, compute budgets, embeddings store, latency/failover monitoring.",
        authorities=[ApprovalAuthority.PAUSE],
    )

    # --- Strategy fleet (provisional until operator confirms) ---
    contracts["STRAT-MOM-001"] = strategy_contract(
        agent_name="Trend Momentum Strategy",
        agent_id="STRAT-MOM-001",
        rationale="Capture persistent price trends via dual moving-average and breakout confirmation; edge from underreaction to drift.",
        assets=["US_EQUITIES_LIQUID", "ETFS_INDEX"],
        holding=HoldingPeriod.SWING_WEEKS,
        frequency="<= 5 new proposals/week/symbol universe slice",
        regimes=[MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, MarketRegime.LOW_VOL],
        indicators=["sma_50", "sma_200", "atr_14", "volume_sma_20", "donchian_20"],
        setups=[
            SetupRule(
                rule_id="MOM-SETUP-1",
                description="Golden/death cross with volume",
                expression="(sma_50 crosses sma_200) AND volume > 1.2 * volume_sma_20",
            )
        ],
        entries=[
            SetupRule(
                rule_id="MOM-ENTRY-1",
                description="Enter in cross direction on close confirmation",
                expression="close confirms cross AND close beyond donchian_20 in trend direction",
            )
        ],
        exits=[
            SetupRule(
                rule_id="MOM-EXIT-1",
                description="Exit on opposite cross or trailing ATR stop",
                expression="sma_50 cross opposite OR close < trail_stop_3atr",
            )
        ],
        stops=[
            SetupRule(
                rule_id="MOM-STOP-1",
                description="Initial stop 2.5 ATR from entry",
                expression="stop = entry - 2.5 * atr_14 * direction",
            )
        ],
        invalidations=[
            SetupRule(
                rule_id="MOM-INV-1",
                description="Invalid if regime flips to high-vol chop",
                expression="regime in {high_vol, mean_reverting} for 3 sessions",
            )
        ],
        sizing=_sizing_default(max_position_pct_nav=0.04, max_risk_per_trade_pct_nav=0.004),
    )

    contracts["STRAT-MR-001"] = strategy_contract(
        agent_name="Mean Reversion Strategy",
        agent_id="STRAT-MR-001",
        rationale="Fade short-term dislocations in range-bound liquid names when RSI and z-score extremes coincide with support/resistance.",
        assets=["US_EQUITIES_LIQUID"],
        holding=HoldingPeriod.SWING_DAYS,
        frequency="<= 10 proposals/day across universe",
        regimes=[MarketRegime.MEAN_REVERTING, MarketRegime.LOW_VOL],
        indicators=["rsi_14", "zscore_20", "bollinger_20_2", "sma_200"],
        setups=[
            SetupRule(
                rule_id="MR-SETUP-1",
                description="RSI extreme with price above long trend filter for longs",
                expression="rsi_14 < 30 AND zscore_20 < -2 AND close > sma_200",
            )
        ],
        entries=[
            SetupRule(
                rule_id="MR-ENTRY-1",
                description="Enter long on reclaim of lower band",
                expression="close crosses above bollinger_lower",
            )
        ],
        exits=[
            SetupRule(
                rule_id="MR-EXIT-1",
                description="Exit at mean or RSI>55",
                expression="close >= sma_20 OR rsi_14 > 55",
            )
        ],
        stops=[
            SetupRule(
                rule_id="MR-STOP-1",
                description="Stop 1.5 ATR beyond entry extreme",
                expression="stop = setup_low - 1.5 * atr_14",
            )
        ],
        invalidations=[
            SetupRule(
                rule_id="MR-INV-1",
                description="Invalid in strong trend regime",
                expression="regime == trending_down for long setups",
            )
        ],
        sizing=_sizing_default(max_position_pct_nav=0.03, max_risk_per_trade_pct_nav=0.003),
    )

    contracts["STRAT-EVT-001"] = strategy_contract(
        agent_name="Event Earnings Strategy",
        agent_id="STRAT-EVT-001",
        rationale="Trade post-earnings drift and guided revisions when research_note conviction>=0.6 and surprise magnitude exceeds threshold.",
        assets=["US_EQUITIES_LIQUID"],
        holding=HoldingPeriod.SWING_DAYS,
        frequency="around earnings calendar only; <= 3 proposals/event",
        regimes=[MarketRegime.EVENT_DRIVEN, MarketRegime.ANY],
        indicators=["earnings_surprise_pct", "guidance_delta", "implied_move", "realized_gap"],
        setups=[
            SetupRule(
                rule_id="EVT-SETUP-1",
                description="Material surprise with research confirmation",
                expression="abs(earnings_surprise_pct) >= 5 AND research_conviction >= 0.6",
            )
        ],
        entries=[
            SetupRule(
                rule_id="EVT-ENTRY-1",
                description="Enter in surprise direction after open range confirmed",
                expression="gap direction == surprise AND first_30m range hold",
            )
        ],
        exits=[
            SetupRule(
                rule_id="EVT-EXIT-1",
                description="Time stop 5 sessions or target 1R*2",
                expression="sessions_held >= 5 OR pnl >= 2R",
            )
        ],
        stops=[
            SetupRule(
                rule_id="EVT-STOP-1",
                description="Stop beyond gap fill / 1R",
                expression="stop = entry - 1R",
            )
        ],
        invalidations=[
            SetupRule(
                rule_id="EVT-INV-1",
                description="Invalid if guidance contradicts surprise",
                expression="guidance_delta sign opposite surprise",
            )
        ],
        sizing=_sizing_default(max_position_pct_nav=0.025, max_risk_per_trade_pct_nav=0.003),
    )

    contracts["STRAT-MACRO-001"] = strategy_contract(
        agent_name="Macro Regime Strategy",
        agent_id="STRAT-MACRO-001",
        rationale="Allocate across index/sector ETFs conditional on macro regime (rates, inflation, growth) signals from research.",
        assets=["ETFS_INDEX", "ETFS_SECTOR", "ETFS_RATES"],
        holding=HoldingPeriod.POSITION_MONTHS,
        frequency="<= 2 rebalance proposals/week",
        regimes=[MarketRegime.RISK_ON, MarketRegime.RISK_OFF, MarketRegime.ANY],
        indicators=["yield_curve_slope", "real_rate", "credit_spread", "regime_label"],
        setups=[
            SetupRule(
                rule_id="MACRO-SETUP-1",
                description="Regime transition confirmed 2 releases",
                expression="regime_label changed AND confirmed_by >= 2 macro_series",
            )
        ],
        entries=[
            SetupRule(
                rule_id="MACRO-ENTRY-1",
                description="Tilt to regime-favored ETF basket",
                expression="proposal basket weights from regime map",
            )
        ],
        exits=[
            SetupRule(
                rule_id="MACRO-EXIT-1",
                description="Exit tilt on regime reverse",
                expression="regime_label reverses",
            )
        ],
        stops=[
            SetupRule(
                rule_id="MACRO-STOP-1",
                description="Book-level stop 4% on macro book",
                expression="macro_book_drawdown >= 0.04",
            )
        ],
        invalidations=[
            SetupRule(
                rule_id="MACRO-INV-1",
                description="Invalid if data vintage stale > 7d for monthly series",
                expression="macro_series_staleness_days > 7",
            )
        ],
        sizing=_sizing_default(
            max_position_pct_nav=0.10,
            max_risk_per_trade_pct_nav=0.01,
            max_gross_exposure_pct_nav=0.40,
        ),
    )

    contracts["STRAT-QUAL-001"] = strategy_contract(
        agent_name="Quality Value Long-Term Strategy",
        agent_id="STRAT-QUAL-001",
        rationale="Own durable high-ROE/low-leverage businesses at reasonable valuation; low turnover; capital stewardship aligned.",
        assets=["US_EQUITIES_LIQUID"],
        holding=HoldingPeriod.LONG_TERM_YEARS,
        frequency="<= 2 new proposals/month",
        regimes=[MarketRegime.ANY, MarketRegime.RISK_ON, MarketRegime.RISK_OFF],
        indicators=["roe_ttm", "net_debt_ebitda", "owner_earnings_yield", "fcf_margin", "moat_score"],
        setups=[
            SetupRule(
                rule_id="QUAL-SETUP-1",
                description="Quality screen + valuation entry band",
                expression="roe_ttm >= 0.15 AND net_debt_ebitda <= 2 AND owner_earnings_yield >= 0.05",
            )
        ],
        entries=[
            SetupRule(
                rule_id="QUAL-ENTRY-1",
                description="Scale-in on research_note conviction>=0.7",
                expression="research_conviction >= 0.7 AND price within entry band",
            )
        ],
        exits=[
            SetupRule(
                rule_id="QUAL-EXIT-1",
                description="Exit on thesis break or permanent impairment",
                expression="moat_score drop OR accounting_red_flag OR valuation > extreme band",
            )
        ],
        stops=[
            SetupRule(
                rule_id="QUAL-STOP-1",
                description="Soft review trigger -25% from cost; hard risk only on thesis break",
                expression="price <= 0.75 * avg_cost -> mandatory review",
            )
        ],
        invalidations=[
            SetupRule(
                rule_id="QUAL-INV-1",
                description="Invalid if leverage spikes",
                expression="net_debt_ebitda > 3.5",
            )
        ],
        sizing=_sizing_default(
            max_position_pct_nav=0.08,
            max_risk_per_trade_pct_nav=0.01,
            max_gross_exposure_pct_nav=0.50,
        ),
    )

    contracts["STRAT-SECROT-001"] = strategy_contract(
        agent_name="Sector Rotation Strategy",
        agent_id="STRAT-SECROT-001",
        rationale="Rotate sector ETF weights using relative strength and macro sector map; avoid overcrowding single sector.",
        assets=["ETFS_SECTOR"],
        holding=HoldingPeriod.SWING_WEEKS,
        frequency="weekly rank rebalance proposals",
        regimes=[MarketRegime.TRENDING_UP, MarketRegime.RISK_ON, MarketRegime.RISK_OFF],
        indicators=["rs_12_1", "sector_momentum", "breadth"],
        setups=[
            SetupRule(
                rule_id="SEC-SETUP-1",
                description="Top quartile RS with improving breadth",
                expression="rs_rank <= 0.25 AND breadth_expanding",
            )
        ],
        entries=[
            SetupRule(
                rule_id="SEC-ENTRY-1",
                description="Overweight top-2 sectors; underweight bottom-2",
                expression="target_weight from rank map",
            )
        ],
        exits=[
            SetupRule(
                rule_id="SEC-EXIT-1",
                description="Exit when rank leaves top half",
                expression="rs_rank > 0.5",
            )
        ],
        stops=[
            SetupRule(
                rule_id="SEC-STOP-1",
                description="Sector book stop 3%",
                expression="sector_book_dd >= 0.03",
            )
        ],
        invalidations=[
            SetupRule(
                rule_id="SEC-INV-1",
                description="Invalid if sector ETF ADV below liquidity floor",
                expression="adv_20d < liquidity_floor",
            )
        ],
        sizing=_sizing_default(max_position_pct_nav=0.08, max_sector_pct_nav=0.20),
    )

    contracts["STRAT-PAIRS-001"] = strategy_contract(
        agent_name="Statistical Pairs Strategy",
        agent_id="STRAT-PAIRS-001",
        rationale="Mean-revert cointegrated pairs when residual z-score extremes appear; market-neutral intent.",
        assets=["US_EQUITIES_LIQUID_PAIRS"],
        holding=HoldingPeriod.SWING_DAYS,
        frequency="<= 5 pair proposals/day",
        regimes=[MarketRegime.MEAN_REVERTING, MarketRegime.LOW_VOL],
        indicators=["hedge_ratio", "residual_zscore", "half_life", "adf_pvalue"],
        setups=[
            SetupRule(
                rule_id="PAIRS-SETUP-1",
                description="Cointegration valid and z extreme",
                expression="adf_pvalue < 0.05 AND half_life between 2 and 20 AND abs(residual_zscore) >= 2",
            )
        ],
        entries=[
            SetupRule(
                rule_id="PAIRS-ENTRY-1",
                description="Long undervalued / short overvalued leg",
                expression="enter when abs(z) >= 2",
            )
        ],
        exits=[
            SetupRule(
                rule_id="PAIRS-EXIT-1",
                description="Exit at z<=0.5",
                expression="abs(residual_zscore) <= 0.5",
            )
        ],
        stops=[
            SetupRule(
                rule_id="PAIRS-STOP-1",
                description="Stop at abs(z)>=4 or cointegration break",
                expression="abs(z) >= 4 OR adf_pvalue >= 0.1",
            )
        ],
        invalidations=[
            SetupRule(
                rule_id="PAIRS-INV-1",
                description="Invalid if hedge ratio unstable",
                expression="hedge_ratio_rolling_std > limit",
            )
        ],
        sizing=_sizing_default(
            max_position_pct_nav=0.03,
            max_risk_per_trade_pct_nav=0.0025,
            max_gross_exposure_pct_nav=0.20,
            max_net_exposure_pct_nav=0.05,
        ),
    )

    return contracts
