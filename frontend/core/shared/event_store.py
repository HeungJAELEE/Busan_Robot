import datetime
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass(frozen=True)
class DomainEvent:
    aggregate_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: datetime.datetime.now().timestamp())

class EventStore:
    """
    In-memory EventStore implementation.
    Future upgrade: Append to SQLite or .jsonl for permanent replayability.
    """
    def __init__(self):
        self._events: List[DomainEvent] = []

    def append(self, event: DomainEvent):
        self._events.append(event)
        # TODO: Save to file for permanent storage

    def get_events(self, aggregate_id: str) -> List[DomainEvent]:
        return [e for e in self._events if e.aggregate_id == aggregate_id]

    def get_all_events(self) -> List[DomainEvent]:
        return self._events.copy()

# 전역 EventStore 인스턴스 (메모리 공유용)
global_event_store = EventStore()
