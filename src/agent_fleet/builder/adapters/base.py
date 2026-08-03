"""Adapter Layer Contract — discover / normalize / validate / apply."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agent_fleet.schemas.organization import OrganizationSnapshot


class Adapter(ABC):
    adapter_id: str
    substrate: str
    mutation_supported: bool = False
    capability_coverage: list[str] = []
    mapping_fidelity: str = "partial"

    @abstractmethod
    def discover(self) -> dict[str, Any]:
        """Inventory framework/runtime objects and telemetry."""

    @abstractmethod
    def normalize(self, discovered: dict[str, Any]) -> OrganizationSnapshot:
        """Map into canonical entities with source references."""

    def validate(self, snapshot: OrganizationSnapshot) -> list[str]:
        """Detect information loss, unsupported features, unsafe mappings."""
        issues: list[str] = []
        if not snapshot.organization.mission:
            issues.append("mission_unresolved")
        if not snapshot.workers:
            issues.append("no_workers_discovered")
        if self.mutation_supported is False and snapshot.change_sets:
            for cs in snapshot.change_sets:
                if cs.status.value in {"deployed", "scheduled"}:
                    issues.append(f"read_only_adapter_cannot_deploy:{cs.change_id}")
        return issues

    def apply(self, change: dict[str, Any]) -> dict[str, Any]:
        if not self.mutation_supported:
            return {
                "status": "refused",
                "reason": "read_only_discovery_adapter",
                "change_id": change.get("change_id"),
                "hint": "Export migration plan for human / substrate tooling",
            }
        raise NotImplementedError("Mutation adapters are deferred past MVP")
