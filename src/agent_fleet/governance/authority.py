"""Authority matrix — who may approve, reject, reduce, pause, close, halt."""

from __future__ import annotations

from agent_fleet.contracts.models import ApprovalAuthority
from agent_fleet.contracts.registry import build_all_contracts


def authority_matrix() -> dict[str, list[str]]:
    matrix: dict[str, list[str]] = {a.value: [] for a in ApprovalAuthority}
    for agent_id, contract in build_all_contracts().items():
        for auth in contract.authorities:
            matrix[auth.value].append(agent_id)
    return matrix


STAGE_OWNERS = {
    "data_ingestion": ["DATA-MKT-001", "DATA-NEWS-001"],
    "information_validation": ["DATA-VAL-001"],
    "research": ["RSH-FUND-001", "RSH-QUANT-001"],
    "signal_generation": ["RSH-FUND-001", "RSH-QUANT-001", "STRAT-*"],
    "strategy_proposal": ["STRAT-*"],
    "independent_validation": ["SIG-VAL-001"],
    "portfolio_evaluation": ["PORT-ALLOC-001"],
    "risk_approval": ["RISK-APPR-001"],
    "capital_stewardship": ["CAP-STEW-001"],
    "execution": ["EXEC-PAPER-001"],  # EXEC-LIVE-001 disabled
    "live_monitoring": ["MON-LIVE-001", "MON-REGIME-001"],
    "post_trade_attribution": ["REV-ATTR-001"],
    "controlled_improvement": ["LEARN-CTRL-001"],
}

TRADE_AUTHORITY = {
    "propose": ["STRAT-*"],
    "validate": ["SIG-VAL-001"],
    "reduce": ["PORT-ALLOC-001", "RISK-APPR-001", "CAP-STEW-001"],
    "approve": ["PORT-ALLOC-001", "RISK-APPR-001", "CAP-STEW-001"],
    "reject": ["SIG-VAL-001", "PORT-ALLOC-001", "RISK-APPR-001", "CAP-STEW-001", "GOV-COMP-001"],
    "pause": ["RISK-APPR-001", "CAP-STEW-001", "MON-LIVE-001", "GOV-COMP-001", "SYS-ORCH-001"],
    "close": ["RISK-APPR-001", "MON-LIVE-001"],
    "emergency_halt": ["RISK-APPR-001", "GOV-COMP-001"],
    "execute_paper": ["EXEC-PAPER-001"],
    "execute_live": [],  # empty until authorized
}
