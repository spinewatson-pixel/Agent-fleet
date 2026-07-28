"""In-process message bus with audit trail.

Production would replace this with a durable event log (e.g. Kafka + append-only store).
Paper trading uses an in-memory bus that records every envelope for lineage/audit.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Callable

from agent_fleet.messaging.schemas import Envelope, MessageType


Handler = Callable[[Envelope], None]


class MessageBus:
    def __init__(self, max_audit: int = 50_000) -> None:
        self._subscribers: dict[MessageType, list[Handler]] = defaultdict(list)
        self._agent_inbox: dict[str, list[Handler]] = defaultdict(list)
        self.audit_log: deque[Envelope] = deque(maxlen=max_audit)
        self._halted = False

    def subscribe_type(self, message_type: MessageType, handler: Handler) -> None:
        self._subscribers[message_type].append(handler)

    def subscribe_agent(self, agent_id: str, handler: Handler) -> None:
        self._agent_inbox[agent_id].append(handler)

    def publish(self, envelope: Envelope) -> None:
        if self._halted and envelope.message_type != MessageType.EMERGENCY_HALT:
            # Only governance/risk halt traffic allowed during emergency
            if envelope.message_type not in {MessageType.GOVERNANCE_EVENT, MessageType.ALERT}:
                raise RuntimeError("Bus halted — only emergency/governance traffic allowed")
        self.audit_log.append(envelope)
        for handler in self._subscribers.get(envelope.message_type, []):
            handler(envelope)
        for target in envelope.target_agent_ids:
            for handler in self._agent_inbox.get(target, []):
                handler(envelope)
        # Broadcast wildcard
        for handler in self._agent_inbox.get("*", []):
            handler(envelope)

    def emergency_halt(self) -> None:
        self._halted = True

    def resume(self) -> None:
        self._halted = False

    @property
    def is_halted(self) -> bool:
        return self._halted

    def lineage(self, correlation_id: str) -> list[Envelope]:
        return [e for e in self.audit_log if e.correlation_id == correlation_id]
