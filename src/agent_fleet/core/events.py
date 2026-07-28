"""Append-only event log for lineage and audit trails."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuditEvent:
    event_id: str
    timestamp: datetime
    actor_id: str
    event_type: str
    correlation_id: str
    payload: dict[str, Any]
    lineage: list[str]


@dataclass
class EventStore:
    """In-memory + optional file-backed audit store."""

    path: Path | None = None
    events: list[AuditEvent] = field(default_factory=list)

    def append(
        self,
        actor_id: str,
        event_type: str,
        correlation_id: str,
        payload: dict[str, Any],
        lineage: list[str] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid4()),
            timestamp=_utcnow(),
            actor_id=actor_id,
            event_type=event_type,
            correlation_id=correlation_id,
            payload=payload,
            lineage=list(lineage or []),
        )
        self.events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "event_id": event.event_id,
                            "timestamp": event.timestamp.isoformat(),
                            "actor_id": event.actor_id,
                            "event_type": event.event_type,
                            "correlation_id": event.correlation_id,
                            "payload": event.payload,
                            "lineage": event.lineage,
                        }
                    )
                    + "\n"
                )
        return event

    def by_correlation(self, correlation_id: str) -> list[AuditEvent]:
        return [e for e in self.events if e.correlation_id == correlation_id]

    def lineage_for(self, correlation_id: str) -> list[str]:
        return [e.event_id for e in self.by_correlation(correlation_id)]
