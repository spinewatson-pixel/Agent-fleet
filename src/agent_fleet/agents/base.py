"""Base agent interface bound to an operating contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agent_fleet.contracts.models import AgentOperatingContract, AgentRole, ApprovalAuthority
from agent_fleet.messaging.bus import MessageBus
from agent_fleet.messaging.schemas import Envelope


class BaseAgent(ABC):
    def __init__(self, contract: AgentOperatingContract, bus: MessageBus) -> None:
        self.contract = contract
        self.bus = bus
        self.agent_id = contract.agent_id
        self._assert_role_permissions()
        bus.subscribe_agent(self.agent_id, self._on_envelope)

    def _assert_role_permissions(self) -> None:
        if self.contract.role == AgentRole.STRATEGY:
            forbidden = {
                ApprovalAuthority.APPROVE,
                ApprovalAuthority.EMERGENCY_HALT,
                ApprovalAuthority.VERSION_APPROVE,
            }
            if forbidden.intersection(set(self.contract.authorities)):
                raise PermissionError(f"{self.agent_id}: strategy cannot hold {forbidden}")
            for perm in self.contract.execution_permissions:
                if "execute" in perm.lower() or "order" in perm.lower():
                    raise PermissionError(f"{self.agent_id}: strategy cannot execute")

    def has_authority(self, authority: ApprovalAuthority) -> bool:
        return authority in self.contract.authorities

    def publish(self, envelope: Envelope) -> None:
        if envelope.source_agent_id != self.agent_id:
            raise PermissionError("Cannot spoof source_agent_id")
        self.bus.publish(envelope)

    def _on_envelope(self, envelope: Envelope) -> None:
        self.handle(envelope)

    @abstractmethod
    def handle(self, envelope: Envelope) -> None:
        ...

    def status(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.contract.role.value,
            "version": self.contract.strategy_version,
            "deployment": self.contract.testing_and_deployment_status.value,
            "environment": self.contract.environment.value,
        }
