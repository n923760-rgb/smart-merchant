from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    name: str
    aggregate_id: UUID
    payload: dict


class EventHandler(Protocol):
    def handle(self, event: DomainEvent) -> None: ...
