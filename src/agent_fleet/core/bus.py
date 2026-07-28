"""In-process message bus with permission checks and audit."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable

from agent_fleet.core.events import EventStore
from agent_fleet.schemas.messages import MessageEnvelope


Handler = Callable[[MessageEnvelope], None]


@dataclass
class MessageBus:
    event_store: EventStore
    queues: dict[str, deque[MessageEnvelope]] = field(
        default_factory=lambda: defaultdict(deque)
    )
    handlers: dict[str, list[Handler]] = field(
        default_factory=lambda: defaultdict(list)
    )
    # agent_id -> allowed message types they may send
    send_permissions: dict[str, set[str]] = field(default_factory=dict)

    def register_handler(self, agent_id: str, handler: Handler) -> None:
        self.handlers[agent_id].append(handler)

    def set_send_permission(self, agent_id: str, message_types: set[str]) -> None:
        self.send_permissions[agent_id] = message_types

    def publish(self, envelope: MessageEnvelope) -> None:
        allowed = self.send_permissions.get(envelope.sender_id)
        if allowed is not None and envelope.message_type.value not in allowed:
            raise PermissionError(
                f"{envelope.sender_id} may not send {envelope.message_type.value}"
            )
        self.event_store.append(
            actor_id=envelope.sender_id,
            event_type=f"message.{envelope.message_type.value}",
            correlation_id=envelope.correlation_id,
            payload={
                "message_id": envelope.message_id,
                "recipients": envelope.recipient_ids,
                "stage": envelope.stage.value,
            },
            lineage=envelope.lineage,
        )
        for recipient in envelope.recipient_ids:
            self.queues[recipient].append(envelope)
            for handler in self.handlers.get(recipient, []):
                handler(envelope)

    def poll(self, agent_id: str) -> MessageEnvelope | None:
        q = self.queues[agent_id]
        if not q:
            return None
        return q.popleft()
