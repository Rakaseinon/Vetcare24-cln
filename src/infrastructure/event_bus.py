"""Bus de eventos en memoria (suficiente para el alcance del PIA; sustituible por un broker)."""
from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Callable

from ..domain.common import DomainEvent

log = logging.getLogger("vetcare.events")


class InMemoryEventBus:
    def __init__(self, max_history: int = 1000) -> None:
        self._handlers: dict[type, list[Callable[[DomainEvent], None]]] = defaultdict(list)
        self.history: deque[DomainEvent] = deque(maxlen=max_history)

    def subscribe(self, event_type: type, handler: Callable[[DomainEvent], None]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        self.history.append(event)
        log.info("evento %s", event.name)
        for h in self._handlers[type(event)]:
            h(event)

    def publish_all(self, events: list[DomainEvent]) -> None:
        for e in events:
            self.publish(e)
