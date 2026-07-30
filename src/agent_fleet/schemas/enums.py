"""Enumerations for the institutional operating chain."""

from enum import Enum


class Environment(str, Enum):
    PAPER = "paper"
    EXPERIMENTAL = "experimental"
    PRODUCTION = "production"


class Stage(str, Enum):
    DATA_INGESTION = "data_ingestion"
    INFORMATION_VALIDATION = "information_validation"
    RESEARCH = "research"
    SIGNAL_GENERATION = "signal_generation"
    STRATEGY_PROPOSAL = "strategy_proposal"
    INDEPENDENT_VALIDATION = "independent_validation"
    PORTFOLIO_EVALUATION = "portfolio_evaluation"
    RISK_APPROVAL = "risk_approval"
    EXECUTION = "execution"
    LIVE_MONITORING = "live_monitoring"
    POST_TRADE_ATTRIBUTION = "post_trade_attribution"
    CONTROLLED_IMPROVEMENT = "controlled_improvement"


class MessageType(str, Enum):
    MARKET_EVENT = "market_event"
    RESEARCH_SIGNAL = "research_signal"
    TRADE_PROPOSAL = "trade_proposal"
    VALIDATION_RESULT = "validation_result"
    PORTFOLIO_VERDICT = "portfolio_verdict"
    RISK_VERDICT = "risk_verdict"
    APPROVAL_DECISION = "approval_decision"
    EXECUTION_REPORT = "execution_report"
    MONITORING_ALERT = "monitoring_alert"
    ATTRIBUTION_REPORT = "attribution_report"
    IMPROVEMENT_PROPOSAL = "improvement_proposal"
    SHUTDOWN_ORDER = "shutdown_order"
    AUDIT_EVENT = "audit_event"


class AgentRole(str, Enum):
    CHIEF_ARCHITECTURE = "chief_architecture"
    SYSTEMS_INTELLIGENCE = "systems_intelligence"
    MARKET_INFORMATION = "market_information"
    AI_INFRASTRUCTURE = "ai_infrastructure"
    PORTFOLIO_RISK = "portfolio_risk"
    TRADING_OPERATIONS = "trading_operations"
    QUANTITATIVE_RESEARCH = "quantitative_research"
    FUNDAMENTAL_RESEARCH = "fundamental_research"
    GOVERNANCE = "governance"
    CAPITAL_STEWARDSHIP = "capital_stewardship"
    STRATEGY = "strategy"
    VALIDATION = "validation"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    ATTRIBUTION = "attribution"
    LEARNING_CONTROL = "learning_control"


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"
    COVER = "cover"
    SHORT = "short"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REDUCED = "reduced"
    PAUSED = "paused"
    ESCALATED = "escalated"


class ActionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REDUCE = "reduce"
    PAUSE = "pause"
    CLOSE = "close"
    SHUTDOWN = "shutdown"


class MarketRegime(str, Enum):
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    RISK_OFF = "risk_off"
    RISK_ON = "risk_on"
    EARNINGS_SEASON = "earnings_season"
    MACRO_EVENT = "macro_event"
    UNKNOWN = "unknown"


class DeploymentStatus(str, Enum):
    DESIGN = "design"
    BACKTEST = "backtest"
    PAPER = "paper"
    LIMITED_LIVE = "limited_live"
    PRODUCTION = "production"
    SUSPENDED = "suspended"
    RETIRED = "retired"
