from collections import defaultdict
from typing import Callable
from core.events import Event, EventType


class EventBus:

    def __init__(self) -> None:
        self._listeners: dict[EventType, list[Callable[[Event], None]]] = defaultdict(
            list
        )

    def subscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> None:
        self._listeners[event_type].append(handler)

    def publish(self, event: Event) -> None:
        for handler in self._listeners[event.event_type]:
            handler(event)

    def unsubscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> None:
        self._listeners[event_type] = [
            h for h in self._listeners[event_type] if h != handler
        ]


bus = EventBus()
