from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.events import Event
from jarvis.tools.base import Tool


EventCallback = Callable[[Event], Awaitable[None] | None]


class PluginAPI:
    def __init__(self, context: JarvisContext) -> None:
        self.context = context

    async def subscribe(self, topic_pattern: str, handler: EventCallback) -> None:
        await self.context.bus.subscribe(topic_pattern, handler)

    def register_tool(self, tool: Tool) -> None:
        self.context.tools.register(tool)

    async def remember(self, content: str, category: str = "plugin", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        item = await self.context.memory.remember(content=content, category=category, metadata=metadata or {})
        return {"item_id": item.item_id, "content": item.content, "category": item.category}

    async def log(self, category: str, message: str, details: dict[str, Any] | None = None) -> None:
        await self.context.memory.log_activity(category=category, message=message, details=details or {})
