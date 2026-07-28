"""Organizational memory with strict production / experimental separation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent_fleet.schemas.enums import Environment


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MemoryRecord:
    key: str
    environment: Environment
    category: str  # research | prediction | trade | rejection | miss | execution | pnl | lesson
    data: dict[str, Any]
    created_at: datetime = field(default_factory=_utcnow)
    agent_id: str = ""
    mutable_in_production: bool = False


@dataclass
class MemoryStore:
    """Separated stores so experimental agents never mutate production rules."""

    production: dict[str, MemoryRecord] = field(default_factory=dict)
    experimental: dict[str, MemoryRecord] = field(default_factory=dict)
    paper: dict[str, MemoryRecord] = field(default_factory=dict)

    def _bucket(self, env: Environment) -> dict[str, MemoryRecord]:
        if env == Environment.PRODUCTION:
            return self.production
        if env == Environment.EXPERIMENTAL:
            return self.experimental
        return self.paper

    def write(self, record: MemoryRecord) -> None:
        if record.environment == Environment.PRODUCTION and record.mutable_in_production:
            raise PermissionError(
                "Experimental/learning writes cannot mark production memory as mutable"
            )
        if (
            record.environment == Environment.EXPERIMENTAL
            and record.category in {"production_rule", "live_limit"}
        ):
            raise PermissionError(
                "Experimental agents must never alter live production rules"
            )
        self._bucket(record.environment)[record.key] = record

    def read(self, key: str, environment: Environment) -> MemoryRecord | None:
        return self._bucket(environment).get(key)

    def list_category(self, category: str, environment: Environment) -> list[MemoryRecord]:
        return [r for r in self._bucket(environment).values() if r.category == category]

    def learn(
        self,
        *,
        key: str,
        category: str,
        data: dict[str, Any],
        agent_id: str,
        environment: Environment = Environment.PAPER,
    ) -> MemoryRecord:
        """Record a learning observation. Never auto-mutates production rules."""
        if environment == Environment.PRODUCTION and category.endswith("_rule_change"):
            raise PermissionError("Rule changes must go through controlled improvement")
        record = MemoryRecord(
            key=key,
            environment=environment,
            category=category,
            data=data,
            agent_id=agent_id,
            mutable_in_production=False,
        )
        self.write(record)
        return record
