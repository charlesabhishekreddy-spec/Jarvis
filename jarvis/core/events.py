from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from .models import Event

EventHandler = Callable[[Event], Awaitable[None] | None]


class AsyncEventBus:
    def __init__(self, history_size: int = 200) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: deque[Event] = deque(maxlen=history_size)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: dict[str, Any]) -> Event:
        event = Event(topic=topic, payload=payload)
        async with self._lock:
            self._history.append(event)
            handlers = list(self._matching_handlers(topic))
        for handler in handlers:
            result = handler(event)
            if inspect.isawaitable(result):
                asyncio.create_task(result)
        return event

    async def subscribe(self, topic_pattern: str, handler: EventHandler) -> None:
        async with self._lock:
            self._subscribers[topic_pattern].append(handler)

    async def unsubscribe(self, topic_pattern: str, handler: EventHandler) -> None:
        async with self._lock:
            handlers = self._subscribers.get(topic_pattern, [])
            if handler in handlers:
                handlers.remove(handler)

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        events = list(self._history)[-limit:]
        return [
            {
                "event_id": event.event_id,
                "topic": event.topic,
                "timestamp": event.timestamp.isoformat(),
                "payload": event.payload,
            }
            for event in events
        ]

    def _matching_handlers(self, topic: str) -> list[EventHandler]:
        handlers: list[EventHandler] = []
        for pattern, subscribers in self._subscribers.items():
            if pattern == "*" or pattern == topic:
                handlers.extend(subscribers)
            elif pattern.endswith("*") and topic.startswith(pattern[:-1]):
                handlers.extend(subscribers)
        return handlers
