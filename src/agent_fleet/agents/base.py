"""Base agent with contract enforcement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agent_fleet.schemas.contracts import AgentOperatingContract
from agent_fleet.schemas.enums import Environment
from agent_fleet.schemas.messages import MessageEnvelope


class BaseAgent(ABC):
    def __init__(self, contract: AgentOperatingContract, environment: Environment = Environment.PAPER):
        self.contract = contract
        self.environment = environment
        if environment == Environment.PRODUCTION and contract.execution.live_enabled:
            raise PermissionError(
                f"{contract.agent_id}: live execution cannot be enabled without explicit deploy authorization"
            )

    @property
    def agent_id(self) -> str:
        return self.contract.agent_id

    def assert_may_propose(self) -> None:
        if not self.contract.execution.may_propose_trades:
            raise PermissionError(f"{self.agent_id} may not propose trades")
        if self.contract.approval.can_self_approve:
            raise PermissionError(f"{self.agent_id} illegally has can_self_approve=True")
        if self.contract.approval.can_self_execute:
            raise PermissionError(f"{self.agent_id} illegally has can_self_execute=True")
        if self.contract.approval.can_set_own_capital_limits:
            raise PermissionError(
                f"{self.agent_id} illegally has can_set_own_capital_limits=True"
            )

    def assert_may_execute(self) -> None:
        if not self.contract.execution.may_place_orders:
            raise PermissionError(f"{self.agent_id} may not place orders")
        if self.environment != Environment.PAPER and not self.contract.execution.live_enabled:
            raise PermissionError(f"{self.agent_id}: live orders disabled")

    @abstractmethod
    def handle(self, envelope: MessageEnvelope) -> list[MessageEnvelope]:
        """Process inbound message; return outbound messages."""

    def health(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "version": self.contract.strategy_version,
            "status": self.contract.testing_deployment_status.value,
            "environment": self.environment.value,
        }
