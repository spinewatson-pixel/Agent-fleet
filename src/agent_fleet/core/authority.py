"""Authority and approval matrix.

Strategy agents propose. They do not approve, allocate capital, execute,
or grade themselves. Risk and governance hold veto authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_fleet.schemas.enums import ActionType, ApprovalStatus
from agent_fleet.schemas.messages import (
    ApprovalDecision,
    PortfolioVerdict,
    RiskVerdict,
    TradeProposal,
    ValidationResult,
)


# Who may take which action on a trade proposal / open position.
AUTHORITY_MATRIX: dict[str, set[str]] = {
    # agent_id -> permitted ActionType values (plus specials)
    "STRAT-*": set(),  # strategies: propose only (handled separately)
    "VAL-IND-001": {ActionType.REJECT.value},  # can reject invalid proposals
    "PORT-RISK-001": {
        ActionType.APPROVE.value,
        ActionType.REJECT.value,
        ActionType.REDUCE.value,
        ActionType.PAUSE.value,
        ActionType.CLOSE.value,
    },
    "TRADE-OPS-001": {
        ActionType.PAUSE.value,
        ActionType.CLOSE.value,
    },
    "GOV-OPS-001": {
        ActionType.REJECT.value,
        ActionType.PAUSE.value,
        ActionType.SHUTDOWN.value,
    },
    "CAP-STEW-001": {
        ActionType.REJECT.value,
        ActionType.REDUCE.value,
        ActionType.PAUSE.value,
    },
    "EXEC-OMS-001": set(),  # executes only after ApprovalDecision.execution_authorized
    "MON-LIVE-001": {
        ActionType.CLOSE.value,  # recommend; force-close requires TRADE-OPS or RISK
    },
    "ARCH-CHIEF-001": {
        ActionType.PAUSE.value,
        ActionType.SHUTDOWN.value,
    },
}

VETO_AGENTS = {"PORT-RISK-001", "GOV-OPS-001", "CAP-STEW-001"}

APPROVAL_CHAIN = [
    "VAL-IND-001",
    "PORT-RISK-001",
    "CAP-STEW-001",
    "GOV-OPS-001",
]


@dataclass
class AuthorityResolver:
    """Resolves final approval from independent stage verdicts."""

    live_execution_enabled: bool = False
    veto_agents: set[str] = field(default_factory=lambda: set(VETO_AGENTS))
    chain: list[str] = field(default_factory=lambda: list(APPROVAL_CHAIN))

    def resolve(
        self,
        proposal: TradeProposal,
        validation: ValidationResult,
        portfolio: PortfolioVerdict,
        risk: RiskVerdict,
        capital_stewardship: RiskVerdict | None = None,
        governance: RiskVerdict | None = None,
    ) -> ApprovalDecision:
        approving: list[str] = []
        rejecting: list[str] = []
        reasons: list[str] = []

        if not validation.passed:
            rejecting.append(validation.validator_agent_id)
            reasons.extend(validation.defects or ["validation_failed"])
            return ApprovalDecision(
                proposal_id=proposal.proposal_id,
                status=ApprovalStatus.REJECTED,
                final_size_pct_nav=None,
                approving_agents=approving,
                rejecting_agents=rejecting,
                authority_chain=self.chain,
                reasons=reasons,
                execution_authorized=False,
            )

        approving.append(validation.validator_agent_id)

        size = proposal.suggested_size_pct_nav
        size_usd = proposal.suggested_size_usd
        status = ApprovalStatus.APPROVED

        for verdict in (portfolio, risk, capital_stewardship, governance):
            if verdict is None:
                continue
            agent = getattr(verdict, "portfolio_agent_id", None) or getattr(
                verdict, "risk_agent_id", None
            )
            if verdict.action == ActionType.REJECT or getattr(verdict, "veto", False):
                rejecting.append(agent)
                reasons.extend(verdict.reasons)
                return ApprovalDecision(
                    proposal_id=proposal.proposal_id,
                    status=ApprovalStatus.REJECTED,
                    final_size_pct_nav=None,
                    final_size_usd=None,
                    approving_agents=approving,
                    rejecting_agents=rejecting,
                    authority_chain=self.chain,
                    reasons=reasons,
                    execution_authorized=False,
                )
            if verdict.action == ActionType.PAUSE:
                rejecting.append(agent)
                reasons.extend(verdict.reasons)
                return ApprovalDecision(
                    proposal_id=proposal.proposal_id,
                    status=ApprovalStatus.PAUSED,
                    final_size_pct_nav=None,
                    final_size_usd=None,
                    approving_agents=approving,
                    rejecting_agents=rejecting,
                    authority_chain=self.chain,
                    reasons=reasons,
                    execution_authorized=False,
                )
            if verdict.action == ActionType.REDUCE:
                status = ApprovalStatus.REDUCED
                approved = verdict.approved_size_pct_nav
                if approved is not None:
                    size = min(size, approved)
                if getattr(verdict, "approved_size_usd", None) is not None:
                    size_usd = (
                        verdict.approved_size_usd
                        if size_usd is None
                        else min(size_usd, verdict.approved_size_usd)
                    )
                reasons.extend(verdict.reasons)
            approving.append(agent)
            if verdict.approved_size_pct_nav is not None:
                size = min(size, verdict.approved_size_pct_nav)
            if getattr(verdict, "approved_size_usd", None) is not None:
                size_usd = (
                    verdict.approved_size_usd
                    if size_usd is None
                    else min(size_usd, verdict.approved_size_usd)
                )

        # Strategy may never authorize its own execution.
        if proposal.strategy_agent_id in approving:
            approving = [a for a in approving if a != proposal.strategy_agent_id]
            reasons.append("stripped_self_approval")

        # Preserve order while deduplicating (portfolio+risk may share an agent id).
        approving = list(dict.fromkeys(approving))
        rejecting = list(dict.fromkeys(rejecting))

        execution_authorized = status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REDUCED,
        } and not self.live_execution_enabled
        # Paper path: authorize paper fills when approved.
        # Live path: blocked until live_execution_enabled AND explicit deploy auth.
        if self.live_execution_enabled:
            execution_authorized = False
            reasons.append("live_execution_requires_explicit_deploy_authorization")
            status = ApprovalStatus.PAUSED

        return ApprovalDecision(
            proposal_id=proposal.proposal_id,
            status=status,
            final_size_pct_nav=size if status != ApprovalStatus.REJECTED else None,
            final_size_usd=size_usd if status != ApprovalStatus.REJECTED else None,
            approving_agents=approving,
            rejecting_agents=rejecting,
            authority_chain=self.chain,
            reasons=reasons or ["passed_authority_chain"],
            execution_authorized=execution_authorized
            and status in {ApprovalStatus.APPROVED, ApprovalStatus.REDUCED},
        )

    def may_act(self, agent_id: str, action: ActionType) -> bool:
        if agent_id.startswith("STRAT-"):
            return False
        allowed = AUTHORITY_MATRIX.get(agent_id, set())
        return action.value in allowed
